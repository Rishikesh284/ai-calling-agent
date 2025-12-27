import os
import json
from fastapi import FastAPI
from google.oauth2.service_account import Credentials
import gspread

app = FastAPI()

# ==============================
# ENV VARIABLES
# ==============================
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID")
SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")

if not GOOGLE_SHEET_ID or not SERVICE_ACCOUNT_JSON:
    raise RuntimeError("Missing required environment variables")

# ==============================
# GOOGLE AUTH
# ==============================
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

service_account_info = json.loads(SERVICE_ACCOUNT_JSON)

credentials = Credentials.from_service_account_info(
    service_account_info,
    scopes=SCOPES
)

gs_client = gspread.authorize(credentials)
sheet = gs_client.open_by_key(GOOGLE_SHEET_ID).sheet1

# ==============================
# ROUTES
# ==============================
@app.get("/")
def health():
    return {"status": "AI Appointment Agent is running"}

@app.post("/appointment")
def create_appointment(data: dict):
    sheet.append_row([
        data.get("name"),
        data.get("phone"),
        data.get("date"),
        data.get("time"),
        data.get("notes", "")
    ])
    return {"success": True}
