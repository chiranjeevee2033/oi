import requests
import json
import os
import time
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo


# -------------------------------------------------
# 1️⃣ NSE SESSION (ONLY FOR DATA)
# -------------------------------------------------
def get_nse_session():
    session = requests.Session()

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/137.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.nseindia.com/",
        "Connection": "keep-alive"
    })

    session.get("https://www.nseindia.com", timeout=20)

    time.sleep(2)

    return session
# -------------------------------------------------
# 2️⃣ NIFTY → NEXT TUESDAY
# -------------------------------------------------
def get_next_tuesday():
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    weekday = today.weekday()  # Mon=0

    days_ahead = (1 - weekday) % 7
    if days_ahead == 0:
        days_ahead = 7

    expiry = today + timedelta(days=days_ahead)
    return expiry.strftime("%d-%b-%Y")


# -------------------------------------------------
# 3️⃣ LAST TUESDAY OF MONTH
# -------------------------------------------------
def last_tuesday_of_month(year, month):
    if month == 12:
        last_day = date(year, 12, 31)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)

    while last_day.weekday() != 1:  # Tuesday
        last_day -= timedelta(days=1)

    return last_day


# -------------------------------------------------
# 4️⃣ BANKNIFTY / FINNIFTY MONTHLY LOGIC
# -------------------------------------------------
def get_monthly_last_tuesday():
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()

    this_month_last_tue = last_tuesday_of_month(today.year, today.month)

    # If today is AFTER last Tuesday → go to next month
    if today > this_month_last_tue:
        if today.month == 12:
            return last_tuesday_of_month(today.year + 1, 1).strftime("%d-%b-%Y")
        else:
            return last_tuesday_of_month(today.year, today.month + 1).strftime("%d-%b-%Y")

    return this_month_last_tue.strftime("%d-%b-%Y")


# -------------------------------------------------
# 5️⃣ FETCH TOTAL OI & VOLUME
# -------------------------------------------------
def fetch_totals(session, symbol, expiry):

    url = (
        "https://www.nseindia.com/api/option-chain-v3"
        f"?type=Indices&symbol={symbol}&expiry={expiry}"
    )

    for attempt in range(3):

        try:

            response = session.get(url, timeout=30)

            print(symbol, "STATUS:", response.status_code)

            if response.status_code != 200:
                time.sleep(3)
                continue

            data = response.json()

            ce_oi = ce_vol = pe_oi = pe_vol = 0

            for row in data.get("records", {}).get("data", []):

                if "CE" in row:
                    ce_oi += row["CE"].get("openInterest", 0)
                    ce_vol += row["CE"].get("totalTradedVolume", 0)

                if "PE" in row:
                    pe_oi += row["PE"].get("openInterest", 0)
                    pe_vol += row["PE"].get("totalTradedVolume", 0)

            return ce_oi, ce_vol, pe_oi, pe_vol

        except Exception as e:

            print(f"{symbol} Retry {attempt+1} Failed:", e)

            time.sleep(3)

    print(f"{symbol} FAILED AFTER 3 RETRIES")

    return 0, 0, 0, 0
# -------------------------------------------------
# 6️⃣ GOOGLE SHEETS
# -------------------------------------------------
def get_worksheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]

    creds = ServiceAccountCredentials.from_json_keyfile_dict(
        json.loads(os.environ["NEW"]),
        scope
    )

    gc = gspread.authorize(creds)
    return gc.open_by_key(
        "15LE3DlLub6yGC1QkqOTB_AOPGQACQtz22KQY5QJZuAw"
    ).worksheet("NIFTY")


# -------------------------------------------------
# 7️⃣ MAIN
# -------------------------------------------------
def main():
    session = get_nse_session()
    ws = get_worksheet()

    existing_data = ws.get_all_values()
    
    # Add header only if sheet empty
    if not existing_data:
    
        ws.update(
            values=[["TIME", "SYMBOL", "CE_OI", "CE_VOL", "PE_OI", "PE_VOL"]],
            range_name="A1"
        )
    nifty_expiry = get_next_tuesday()
    bank_expiry = get_monthly_last_tuesday()
    finn_expiry = bank_expiry

    rows = []
    
    symbols = [
        ("BANKNIFTY", bank_expiry),
        ("NIFTY", nifty_expiry),
        ("FINNIFTY", finn_expiry)
    ]
    
    for symbol, expiry in symbols:
    
        values = fetch_totals(session, symbol, expiry)
    
        rows.append([
            symbol,
            *values
        ])

    start_row = len(existing_data) + 1
    end_row = start_row + len(rows) - 1
    
    ws.update(
        range_name=f"A{start_row}:E{end_row}",
        values=rows
    )


    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    
    ws.append_row([
        now.strftime("%d-%m-%Y %H:%M:%S IST")
    ])
    print("✅ Calendar-based expiry logic applied successfully")


# -------------------------------------------------
# 8️⃣ ENTRY POINT
# -------------------------------------------------
if __name__ == "__main__":
    main()
