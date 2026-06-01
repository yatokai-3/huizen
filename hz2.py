import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright

URL = "https://5huizenvastgoedbeheer.nl/#/student-housing"
DATA_FILE = "data/state.json"

os.makedirs("data", exist_ok=True)


def load_state():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {}

def save_state(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def safe_int(text):
    return int("".join(filter(str.isdigit, text)) or 0)


# ✅ SCRAPER (Playwright)
def fetch():
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, wait_until="domcontentloaded")
        page.wait_for_timeout(5000)

        cards = page.locator("div.q-card")
        count = cards.count()

        print(f"Found {count} cards")

        for i in range(count):
            card = cards.nth(i)

            name_el = card.locator("span.block").first
            if name_el.count() == 0:
                continue

            name = name_el.inner_text().strip()
            if not name:
                continue

            total = 0
            available = 0

            chips = card.locator("div.q-chip")
            for j in range(chips.count()):
                chip = chips.nth(j)

                icon = chip.locator("i.q-icon").first
                val = chip.locator("span.text-bold").first

                if val.count() == 0:
                    continue

                num = safe_int(val.inner_text())
                icon_class = icon.get_attribute("class") or ""

                if "fa-home" in icon_class:
                    total = num
                elif "fa-check-circle" in icon_class:
                    available = num

            results.append({
                "id": name.lower(),
                "name": name,
                "total": total,
                "available": available
            })

        browser.close()

    return results


# ✅ EMAIL
def send_email(changed):
    if not changed:
        print("No alerts")
        return

    gmail = os.environ["GMAIL_USER"]
    password = os.environ["GMAIL_APP_PASS"]
    to_email = os.environ["NOTIFY_EMAIL"]

    rows = ""
    for r in changed:
        rows += f"""
        <div>
        <b>{r['name']}</b><br>
        Available: {r['available']}<br>
        Total: {r['total']}
        </div><br>
        """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🚨 Rooms Available ({len(changed)})"
    msg["From"] = gmail
    msg["To"] = to_email

    html = f"<h2>Rooms Opened</h2>{rows}"
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(gmail, password)
        smtp.sendmail(gmail, to_email, msg.as_string())

    print("Email sent ✅")


# ✅ MAIN
def run_once():
    prev = load_state()
    data = fetch()

    changed = []
    new_state = {}

    for r in data:
        prev_val = prev.get(r["id"], {}).get("available", 0)
        curr_val = r["available"]

        new_state[r["id"]] = r

        print(f"{r['name']} | {prev_val} -> {curr_val}")

        if curr_val > prev_val:
            changed.append(r)

    save_state(new_state)
    send_email(changed)


if __name__ == "__main__":
    run_once()
