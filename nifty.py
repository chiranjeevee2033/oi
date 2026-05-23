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
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.nseindia.com/"
    })
    session.get("https://www.nseindia.com", timeout=10)
    time.sleep(1)
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

    data = session.get(url, timeout=10).json()

    ce_oi = ce_vol = pe_oi = pe_vol = 0

    for row in data.get("records", {}).get("data", []):
        if "CE" in row:
            ce_oi += row["CE"].get("openInterest", 0)
            ce_vol += row["CE"].get("totalTradedVolume", 0)
        if "PE" in row:
            pe_oi += row["PE"].get("openInterest", 0)
            pe_vol += row["PE"].get("totalTradedVolume", 0)

    return ce_oi, ce_vol, pe_oi, pe_vol


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

    ws.batch_clear(["A:E"])
    ws.update("A1", [["SYMBOL", "CE_OI", "CE_VOL", "PE_OI", "PE_VOL"]])

    nifty_expiry = get_next_tuesday()
    bank_expiry = get_monthly_last_tuesday()
    finn_expiry = bank_expiry

    rows = [
        ["BANKNIFTY", *fetch_totals(session, "BANKNIFTY", bank_expiry)],
        ["NIFTY", *fetch_totals(session, "NIFTY", nifty_expiry)],
        ["FINNIFTY", *fetch_totals(session, "FINNIFTY", finn_expiry)],
    ]

    ws.update("A2", rows)

    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    ws.update(
        f"A{len(rows) + 2}",
        [[now.strftime("%d-%m-%Y %H:%M:%S IST")]]
    )

    print("✅ Calendar-based expiry logic applied successfully")


# -------------------------------------------------
# 8️⃣ ENTRY POINT
# -------------------------------------------------
if __name__ == "__main__":
    main()
