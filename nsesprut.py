import requests
import pandas as pd
import time
from datetime import datetime
import pytz
import os
import json

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==========================
# CONFIG
# ==========================
SHEET_ID = "15LE3DlLub6yGC1QkqOTB_AOPGQACQtz22KQY5QJZuAw"
WORKSHEET_NAME = "NSPRUT"

BASE_URL = "https://www.nseindia.com"
API_URL = "https://www.nseindia.com/api/live-analysis-oi-spurts-underlyings"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/market-data/oi-spurts",
    "Connection": "keep-alive"
}

# ==========================
# GOOGLE SHEETS CONNECT (ENV SAFE)
# ==========================
def get_worksheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    raw_json = os.environ.get("NEW")
    if not raw_json:
        raise Exception("Environment variable NEW is not set")

    creds_dict = json.loads(raw_json)
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    return sh.worksheet(WORKSHEET_NAME)

# ==========================
# FETCH NSE DATA
# ==========================
def fetch_oi_spurts():
    session = requests.Session()
    session.headers.update(HEADERS)

    session.get(BASE_URL)
    time.sleep(1)

    r = session.get(API_URL)
    r.raise_for_status()

    df = pd.DataFrame(r.json().get("data", []))
    return df.head(35)

# ==========================
# MAIN
# ==========================
def main():
    print("📡 Fetching NSE OI Spurts data...")
    df = fetch_oi_spurts()

    if df.empty:
        raise Exception("No data received from NSE")

    print("✅ Data fetched")

    ws = get_worksheet()
    
    existing_data = ws.get_all_values()
    
    # Add header only if sheet empty
    if not existing_data:
    
        header_row = df.columns.tolist()
    
        ws.append_row(header_row)

    # ---- Timestamp ONLY in Column A, last row ----
    ist = pytz.timezone("Asia/Kolkata")
    timestamp = datetime.now(ist).strftime("%d-%m-%Y %H:%M:%S IST")

    rows_to_append = df.values.tolist()
    
    # append all data rows
    ws.append_rows(rows_to_append)
    
    # append ONE timestamp row at end
    ws.append_row([timestamp])
    print("🎉 SUCCESS: Sheet updated safely")

# ==========================
if __name__ == "__main__":
    main()




