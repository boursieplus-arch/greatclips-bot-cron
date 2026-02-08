import os
import requests
from bs4 import BeautifulSoup
import re
import sqlite3
from datetime import datetime

BASE_URL = "https://coupons-2save.com/greatclips"

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])

def send_telegram(text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        r = requests.post(url, data=data, timeout=10)
        print("Telegram status:", r.status_code)
    except Exception as e:
        print("Telegram error:", e)

def fetch_page():
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(BASE_URL, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.text

def parse_coupons(html):
    soup = BeautifulSoup(html, "lxml")
    coupons = []
    for elem in soup.find_all(string=re.compile("Great Clips", re.I)):
        if elem.parent.name in ["script", "style"]:
            continue
        full_text = elem.parent.get_text(" ", strip=True)
        prices = re.findall(r"\$\d+\.\d{2}", full_text)
        if prices:
            coupons.append({
                "description": full_text,
                "prices": list(set(prices))
            })
    return coupons

def init_db():
    conn = sqlite3.connect("coupons2save.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT UNIQUE,
            found_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_and_get_new(coupons):
    conn = sqlite3.connect("coupons2save.db")
    c = conn.cursor()
    new_items = []
    for cpn in coupons:
        try:
            c.execute(
                "INSERT INTO coupons (description, found_at) VALUES (?, ?)",
                (cpn["description"], datetime.now().isoformat())
            )
            conn.commit()
            new_items.append(cpn)
        except sqlite3.IntegrityError:
            pass
    conn.close()
    return new_items

def main():
    init_db()
    html = fetch_page()
    coupons = parse_coupons(html)
    new_coupons = save_and_get_new(coupons)

    print(f"Found: {len(coupons)}, New: {len(new_coupons)}")
    
    if not new_coupons:
        print("No new coupons.")
        return

    for cpn in new_coupons:
        text = "🎉 کوپن جدید Great Clips:\n"
        text += "قیمت‌ها: " + ", ".join(cpn["prices"]) + "\n\n"
        text += cpn["description"][:500]  # محدود به 500 کاراکتر
        send_telegram(text)

if __name__ == "__main__":
    main()
