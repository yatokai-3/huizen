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
# STATE
# =====================
def load_state():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
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
        name_el = card.select_one("button .block")
        name = name_el.get_text(strip=True) if name_el else None

        total = 0
        available = 0

        for chip in card.select("div.q-chip"):
            icon = chip.select_one("i.q-icon")
            val = chip.select_one("span.text-bold")

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
    if not changed:
        print("No alert")
        return

    gmail_user = os.environ["GMAIL_USER"]
    gmail_pass = os.environ["GMAIL_APP_PASS"]
    notify_email = os.environ["NOTIFY_EMAIL"]

    rows = ""
    for r in changed:
        rows += f"""
        <div style='border:1px solid #ddd;padding:10px;margin:10px'>
          <b>{r['name']}</b><br>
          Available: <b style='color:green'>{r['available']}</b><br>
          Total: {r['total']}
        </div>
        """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚨 Rooms Opened ({len(changed)} building)"
    msg["From"] = gmail_user
    msg["To"] = notify_email

    msg.attach(MIMEText(f"<h2>Rooms Available</h2>{rows}", "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail_user, gmail_pass)
        smtp.sendmail(gmail_user, notify_email, msg.as_string())

    print("Email sent ✅")


# =====================
# MAIN
# =====================
def run_once():
    prev_state = load_state()
    current_data = fetch()

    changed = []
    new_state = {}

    for r in current_data:
        b_id = r["id"]

        prev_val = prev_state.get(b_id, 0)
        curr_val = r["available"]

        # ✅ ALWAYS save current state (even 0)
        new_state[b_id] = curr_val

        print(f"{r['name']} | prev={prev_val} → now={curr_val}")

        # ✅ trigger only on 0 → 1+
        if prev_val == 0 and curr_val >= 1:
            changed.append(r)

    save_state(new_state)
    send_email(changed)


if __name__ == "__main__":
    run_once()
