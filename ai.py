import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# =========================
# CONFIG
# =========================
SHEET_ID = "15LE3DlLub6yGC1QkqOTB_AOPGQACQtz22KQY5QJZuAw"
INPUT_WS = "NSPRUT"
OUTPUT_WS = "RESULT"

# =========================
# GOOGLE AUTH
# =========================
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.environ["NEW"])
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)

gc = gspread.authorize(creds)

sh = gc.open_by_key(SHEET_ID)
input_ws = sh.worksheet(INPUT_WS)

try:
    output_ws = sh.worksheet(OUTPUT_WS)
except:
    output_ws = sh.add_worksheet(title=OUTPUT_WS, rows="2000", cols="20")

# =========================
# HELPERS
# =========================
def clean(x):
    try:
        return float(str(x).replace(",", "").replace("%", ""))
    except:
        return 0

def find_col(headers, name):
    for i, h in enumerate(headers):
        if name.lower().replace(" ", "") in h.lower().replace(" ", ""):
            return i
    return -1

# =========================
# LOAD DATA
# =========================
data = input_ws.get_all_values()
headers = data[0]
rows = data[1:]

symbol_i = find_col(headers, "symbol")
oi_i = find_col(headers, "OI-Chang")
spot_i = find_col(headers, "oi spot")

up_list = []
down_list = []

# =========================
# CORE LOGIC
# =========================
for r in rows:
    try:
        symbol = r[symbol_i]
        oi = clean(r[oi_i])
        spot = clean(r[spot_i])

        # Skip weak moves
        if abs(spot) < 0.3:
            continue

        # UP
        if oi > 5 and spot > 0:
            score = oi + (spot * 10)
            up_list.append((symbol, oi, spot, score))

        # DOWN
        elif oi > 5 and spot < 0:
            score = oi + (abs(spot) * 10)
            down_list.append((symbol, oi, spot, score))

    except:
        continue

# =========================
# SORT & PICK TOP 3
# =========================
up_list = sorted(up_list, key=lambda x: x[3], reverse=True)[:3]
down_list = sorted(down_list, key=lambda x: x[3], reverse=True)[:3]

# =========================
# PREPARE ROWS (SIDE BY SIDE)
# =========================
max_len = max(len(up_list), len(down_list))

rows_to_add = []

timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Header row (only once if sheet empty)
if len(output_ws.get_all_values()) == 0:
    output_ws.append_row([
        "Time",
        "UP Stock", "UP OI", "UP Spot",
        "DOWN Stock", "DOWN OI", "DOWN Spot"
    ])

# Data rows
for i in range(max_len):
    up = up_list[i] if i < len(up_list) else ("", "", "")
    down = down_list[i] if i < len(down_list) else ("", "", "")

    rows_to_add.append([
        timestamp if i == 0 else "",
        up[0], up[1], up[2],
        down[0], down[1], down[2]
    ])

# =========================
# APPEND TO SHEET
# =========================
for row in rows_to_add:
    output_ws.append_row(row)

print("✅ Data appended successfully (UP & DOWN separate)")
