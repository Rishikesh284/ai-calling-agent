import os
import json
from fastapi import FastAPI, HTTPException
from google.oauth2.service_account import Credentials
import gspread

app = FastAPI(title="AI Calling Agent")

# Lazy globals
_sheet = None


def get_sheet():
    global _sheet

    if _sheet is not None:
        return _sheet

    service_account_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    sheet_id = os.getenv("GOOGLE_SHEET_ID")

    if not service_account_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is missing")

    if not sheet_id:
        raise RuntimeError("GOOGLE_SHEET_ID is missing")

    creds_dict = json.loads(service_account_json)

    creds = Credentials.from_service_account_info(
        creds_dict,
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )

    client = gspread.authorize(creds)
    _sheet = client.open_by_key(sheet_id).sheet1
    return _sheet


@app.get("/")
def health():
    return {"status": "ok", "message": "Service running"}


@app.get("/debug/env")
def debug_env():
    return {
        "GOOGLE_SERVICE_ACCOUNT_JSON": bool(os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")),
        "GOOGLE_SHEET_ID": bool(os.getenv("GOOGLE_SHEET_ID")),
        "OPENAI_API_KEY": bool(os.getenv("OPENAI_API_KEY")),
    }


@app.post("/appointments")
def create_appointment(name: str, phone: str, date: str):
    try:
        sheet = get_sheet()
        sheet.append_row([name, phone, date])
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
