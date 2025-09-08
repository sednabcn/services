import pandas as pd
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

def load_contacts(source, svc_account_json=None):
    """Load contacts from CSV, JSON, or Google Sheets URL."""
    if source.endswith(".csv"):
        return pd.read_csv(source).to_dict(orient="records")
    elif source.endswith(".json"):
        return pd.read_json(source).to_dict(orient="records")
    elif source.endswith(".url") and svc_account_json:
        url = open(source).read().strip()
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(svc_account_json, scope)
        client = gspread.authorize(creds)
        sheet_id = url.split("/d/")[1].split("/")[0]
        sheet = client.open_by_key(sheet_id).sheet1
        data = sheet.get_all_records()
        return data
    else:
        raise ValueError(f"Unsupported source: {source}")
