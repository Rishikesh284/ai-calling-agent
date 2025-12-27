import os
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.oauth2.service_account import Credentials
import gspread
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

app = FastAPI(title="AI Appointment Agent")

# ---------- ENV ----------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")

# ---------- OpenAI ----------
client = OpenAI(api_key=OPENAI_API_KEY)

# ---------- Google Sheets ----------
gs_client = None
sheet = None

if GOOGLE_SERVICE_ACCOUNT_JSON and GOOGLE_SHEET_ID:
    creds_dict = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    gs_client = gspread.authorize(creds)
    sheet = gs_client.open_by_key(GOOGLE_SHEET_ID).sheet1

# ---------- Models ----------
class Appointment(BaseModel):
    name: str
    phone: str
    date: str

class AIRequest(BaseModel):
    message: str

# ---------- Health ----------
@app.get("/")
def root():
    return {"status": "ok", "message": "Service running"}

# ---------- Debug ----------
@app.get("/debug/env")
def debug_env():
    return {
        "OPENAI_API_KEY": bool(OPENAI_API_KEY),
        "GOOGLE_SERVICE_ACCOUNT_JSON": bool(GOOGLE_SERVICE_ACCOUNT_JSON),
        "GOOGLE_SHEET_ID": bool(GOOGLE_SHEET_ID),
    }

# ---------- Core Appointment ----------
@app.post("/appointments")
def create_appointment(data: Appointment):
    if not sheet:
        raise HTTPException(status_code=500, detail="Google Sheets not configured")

    sheet.append_row([data.name, data.phone, data.date])
    return {"status": "success", "message": "Appointment booked"}

# ---------- AI AGENT ----------
@app.post("/ai/appointment")
def ai_appointment(req: AIRequest):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI not configured")

    prompt = f"""
You are an AI appointment setter.

Extract:
- name
- phone
- date

If any field is missing, ask the user for it.

User message:
{req.message}

Respond ONLY in JSON format like:
{{
  "name": "...",
  "phone": "...",
  "date": "..."
}}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    content = response.choices[0].message.content

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return {
            "status": "need_info",
            "message": "Please provide your name, phone number, and preferred date."
        }

    missing = [k for k in ["name", "phone", "date"] if not data.get(k)]
    if missing:
        return {
            "status": "need_info",
            "message": f"Please provide: {', '.join(missing)}"
        }

    sheet.append_row([data["name"], data["phone"], data["date"]])

    return {
        "status": "confirmed",
        "message": "✅ Your appointment has been booked successfully!"
    }
