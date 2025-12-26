import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict

# ---------- OpenAI ----------
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ---------- Google Sheets ----------
import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

SERVICE_ACCOUNT_FILE = "service_account2.json"  # ✅ correct file

creds = Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=SCOPES
)

gs_client = gspread.authorize(creds)

# ✅ Use Spreadsheet ID (most reliable)
SPREADSHEET_ID = "1kJzWxRoXpy87IhlDuz3g2eRYKNAwng4zrArQPHYZAEc"
sheet = gs_client.open_by_key(SPREADSHEET_ID).sheet1


# ---------- FastAPI ----------
app = FastAPI(title="AI Appointment Agent")


# ---------- Session Memory ----------
sessions: Dict[str, Dict] = {}


# ---------- Request Model ----------
class CallRequest(BaseModel):
    call_id: str
    user_input: str | None = None


# ---------- GPT Logic ----------
def gpt_response(state: str, session: Dict) -> str:
    system_prompt = f"""
You are an AI appointment booking assistant.

Current state: {state}

Your task:
- Greet the caller
- Ask for name
- Ask for date
- Ask for time
- Confirm appointment

Be polite and concise.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": session.get("last_input", "")}
    ]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    return response.choices[0].message.content.strip()


# ---------- Save to Google Sheets ----------
def save_appointment(data: Dict):
    sheet.append_row([
        data.get("name"),
        data.get("date"),
        data.get("time")
    ])


# ---------- API Endpoint ----------
@app.post("/call")
def handle_call(req: CallRequest):
    call_id = req.call_id

    if call_id not in sessions:
        sessions[call_id] = {
            "state": "GREETING",
            "name": None,
            "date": None,
            "time": None,
            "last_input": ""
        }

    session = sessions[call_id]

    if req.user_input:
        session["last_input"] = req.user_input

    # ----- State Machine -----
    if session["state"] == "GREETING":
        reply = "Hi, thank you for calling. May I have your name?"
        session["state"] = "ASK_NAME"

    elif session["state"] == "ASK_NAME":
        session["name"] = req.user_input
        reply = "Thanks. What date would you like to book the appointment?"
        session["state"] = "ASK_DATE"

    elif session["state"] == "ASK_DATE":
        session["date"] = req.user_input
        reply = "Got it. What time works best for you?"
        session["state"] = "ASK_TIME"

    elif session["state"] == "ASK_TIME":
        session["time"] = req.user_input

        save_appointment(session)

        reply = (
            f"Your appointment is confirmed.\n"
            f"Name: {session['name']}\n"
            f"Date: {session['date']}\n"
            f"Time: {session['time']}\n"
            f"Thank you!"
        )

        session["state"] = "CONFIRMED"

    else:
        reply = "Your appointment has already been booked. Thank you."

    return {
        "reply": reply,
        "state": session["state"]
    }

