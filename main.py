import os
import json
from datetime import datetime

from fastapi import FastAPI
from pydantic import BaseModel

from google.oauth2.service_account import Credentials
import gspread

from openai import OpenAI
from dotenv import load_dotenv

# -------------------------------------------------
# Load environment variables
# -------------------------------------------------
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
BUSINESS_NAME = os.getenv("BUSINESS_NAME", "our business")
TIMEZONE = os.getenv("TIMEZONE", "Asia/Kolkata")

if not GOOGLE_SERVICE_ACCOUNT_JSON:
    raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is missing")

# -------------------------------------------------
# Initialize OpenAI
# -------------------------------------------------
client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------------------------------
# Initialize Google Sheets (ENV based)
# -------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

service_account_info = json.loads(GOOGLE_SERVICE_ACCOUNT_JSON)

creds = Credentials.from_service_account_info(
    service_account_info,
    scopes=SCOPES
)

gs_client = gspread.authorize(creds)
sheet = gs_client.open_by_key(GOOGLE_SHEET_ID).sheet1

# -------------------------------------------------
# FastAPI App
# -------------------------------------------------
app = FastAPI(title="AI Appointment Setter")

sessions = {}

# -------------------------------------------------
# Request Model
# -------------------------------------------------
class CallRequest(BaseModel):
    call_id: str
    user_input: str | None = None

# -------------------------------------------------
# GPT Logic
# -------------------------------------------------
def gpt_response(state, context):
    system_prompt = f"""
You are a polite, natural-sounding AI receptionist for {BUSINESS_NAME}.
Start with:
"Hi, thank you for calling {BUSINESS_NAME}. How can I help you?"

Only book appointments if the caller explicitly asks for one.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": context}
        ]
    )

    return response.choices[0].message.content.strip()

# -------------------------------------------------
# API Endpoint
# -------------------------------------------------
@app.post("/call")
def handle_call(req: CallRequest):
    call_id = req.call_id

    if call_id not in sessions:
        sessions[call_id] = ""

    if req.user_input:
        sessions[call_id] += f"\nUser: {req.user_input}"

    reply = gpt_response("ACTIVE", sessions[call_id])

    sessions[call_id] += f"\nAI: {reply}"

    return {
        "reply": reply
    }

# -------------------------------------------------
# Health Check
# -------------------------------------------------
@app.get("/")
def root():
    return {"status": "AI Appointment Setter Running"}

