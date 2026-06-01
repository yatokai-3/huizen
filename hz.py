
import requests
from bs4 import BeautifulSoup
import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

URL = "https://5huizenvastgoedbeheer.nl/#/student-housing"
DATA_FILE = "data/state.json"

os.makedirs("data", exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0"}


# =====================
# LOAD/SAVE STATE
# =====================
def load_state():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# =====================
# SCRAPE
# =====================
def fetch():
    res = requests.get(URL, headers=HEADERS)
    soup = BeautifulSoup(res.text, "html.parser")

    cards = soup.select("div.q-card__actions.justify-start")

    results = []

    for card in cards:
        name = card.select_one("button .block")
        name = name.get_text(strip=True) if name else None

        total = 0
        available = 0

        chips = card.select("div.q-chip")

        for chip in chips:
            icon = chip.select_one("i.q-icon")
            val  = chip.select_one("span.text-bold")

            if not val:
                continue

            num = int(''.join(filter(str.isdigit, val.text)) or 0)
            classes = " ".join(icon.get("class", [])) if icon else ""

            if "fa-home" in classes:
                total = num
            elif "fa-check-circle" in classes:
                available = num

        if name:
            results.append({
                "id": name.lower().strip(),
                "name": name,
                "available": available,
                "total": total
            })

    return results


# =====================
# EMAIL
# =====================
def send_email(changed):
    gmail_user = os.environ["GMAIL_USER"]
    gmail_pass = os.environ["GMAIL_APP_PASS"]
    notify_email = os.environ["NOTIFY_EMAIL"]

    if not changed:
        print("No new availability")
        return

    rows = ""
    for r in changed:
        rows += f"""
        <div style='border:1px solid #ddd;padding:10px;margin:10px'>
            <b>{r['name']}</b><br>
            Available: <b style='color:green'>{r['available']}</b><br>
            Total: {r['total']}
        </div>
        """

    html = f"""
    <h2>🚨 Rooms Opened (0 → 1+)</h2>
    {rows}
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚨 Rooms Available ({len(changed)} buildings)"
    msg["From"] = gmail_user
    msg["To"] = notify_email

    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_user, gmail_pass)
        smtp.sendmail(gmail_user, notify_email, msg.as_string())

    print("Email sent ✅")


# =====================
# MAIN LOGIC
# =====================
def run_once():
    prev = load_state()
    data = fetch()

    changed = []
    new_state = {}

    for r in data:
        prev_val = prev.get(r["id"], 0)
        curr_val = r["available"]

        new_state[r["id"]] = curr_val

        print(f"{r['name']} | prev={prev_val} → now={curr_val}")

        # ✅ ONLY trigger when 0 → 1+
        if prev_val == 0 and curr_val >= 1:
            changed.append(r)

    save_state(new_state)
    send_email(changed)


if __name__ == "__main__":
    run_once()
