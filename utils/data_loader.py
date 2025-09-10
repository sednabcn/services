import pandas as pd
import requests
from io import StringIO
import gspread
from oauth2client.service_account import ServiceAccountCredentials


def load_contacts(source, svc_account_json=None):
    """
    Load contacts from CSV, JSON, or Google Sheets URL (.url file).

    Args:
        source (str): Path to file (.csv, .json, .url)
        svc_account_json (dict, optional): Google service account JSON dict.
                                           If not provided, falls back to public CSV export.

    Returns:
        list of dicts: contacts
    """
    # ----------------- CSV -----------------
    if source.endswith(".csv"):
        return pd.read_csv(source).to_dict(orient="records")

    # ----------------- JSON -----------------
    elif source.endswith(".json"):
        return pd.read_json(source).to_dict(orient="records")

    # ----------------- Google Sheets via .url -----------------
    elif source.endswith(".url"):
        # Read the .url file
        with open(source, "r") as f:
            content = f.read().strip()

        # Case 1: Plain URL
        if content.startswith("http"):
            sheet_url = content

        # Case 2: [InternetShortcut] style
        elif "URL=" in content:
            sheet_url = None
            for line in content.splitlines():
                if line.startswith("URL="):
                    sheet_url = line.split("=", 1)[1].strip()
                    break
            if not sheet_url:
                raise ValueError(f"No valid URL found in {source}")
        else:
            raise ValueError(f"Unsupported .url file format in {source}")

        # Extract Sheet ID
        try:
            sheet_id = sheet_url.split("/d/")[1].split("/")[0]
        except IndexError:
            raise ValueError(f"Invalid Google Sheets URL: {sheet_url}")

        # Extract gid if present
        gid = None
        if "gid=" in sheet_url:
            gid = sheet_url.split("gid=")[1].split("&")[0].split("#")[0]

        # ----------------- Use Google API if credentials provided -----------------
        if svc_account_json:
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(svc_account_json, scope)
            client = gspread.authorize(creds)

            # Pick correct worksheet
            if gid:
                worksheet = None
                for ws in client.open_by_key(sheet_id).worksheets():
                    if str(ws.id) == str(gid):
                        worksheet = ws
                        break
                if worksheet is None:
                    worksheet = client.open_by_key(sheet_id).sheet1
            else:
                worksheet = client.open_by_key(sheet_id).sheet1

            data = worksheet.get_all_records()

        # ----------------- Fallback: public CSV export -----------------
        else:
            export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
            if gid:
                export_url += f"&gid={gid}"
            resp = requests.get(export_url)
            resp.raise_for_status()
            data = pd.read_csv(StringIO(resp.text)).to_dict(orient="records")

        return data

    else:
        raise ValueError(f"Unsupported source: {source}")
