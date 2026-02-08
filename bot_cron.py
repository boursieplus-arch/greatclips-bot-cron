import os
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime

BASE_URL = "https://coupons-2save.com/greatclips"

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
CHAT_ID = int(os.environ["CHAT_ID"])

def send_telegram(text: str):
    """ارسال پیام به تلگرام"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text}
    try:
        r = requests.post(url, data=data, timeout=10)
        print(f"Telegram status: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False

def fetch_page(url):
    """دریافت محتوای یک صفحه"""
    headers = {"User-Agent": "Mozilla/5.0"}
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.text

def get_coupon_page_links():
    """از صفحه اصلی، لینک همه صفحات کوپن را می‌گیرد (مثل /greatclips/$8-99)"""
    html = fetch_page(BASE_URL)
    soup = BeautifulSoup(html, "lxml")
    
    coupon_links = []
    # لینک‌هایی که به صفحات کوپن اشاره می‌کنند (معمولاً شامل /greatclips/$ هستند)
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # لینک‌های نسبی یا مطلق که به زیرصفحات کوپن اشاره می‌کنند
        if "/greatclips/" in href and href != "/greatclips" and href != "/greatclips/":
            # ساخت URL کامل
            if href.startswith("http"):
                full_url = href
            elif href.startswith("/"):
                full_url = "https://coupons-2save.com" + href
            else:
                full_url = "https://coupons-2save.com/greatclips/" + href
            
            if full_url not in coupon_links and full_url != BASE_URL:
                coupon_links.append(full_url)
    
    return coupon_links

def extract_offer_links(page_url):
    """از یک صفحه کوپن، همه لینک‌های offers.greatclips.com را استخراج می‌کند"""
    try:
        html = fetch_page(page_url)
        soup = BeautifulSoup(html, "lxml")
        
        offer_links = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if "offers.greatclips.com" in href:
                offer_links.add(href)
        
        # استخراج قیمت از متن صفحه (برای تیتر)
        title_tag = soup.find("h1") or soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""
        
        # پیدا کردن قیمت در تیتر یا متن
        price_match = re.search(r"\$(\d+\.\d{2})", title)
        price = price_match.group(0) if price_match else "قیمت نامشخص"
        
        return {
            "page_url": page_url,
            "title": title[:80],  # محدود به 80 کاراکتر
            "price": price,
            "offer_links": sorted(offer_links)
        }
    except Exception as e:
        print(f"Error extracting from {page_url}: {e}")
        return None

def main():
    print(f"🚀 شروع اسکرپ کوپن‌های Great Clips - {datetime.now()}")
    
    # ۱. گرفتن لینک صفحات کوپن از صفحه اصلی
    print("📄 در حال دریافت لیست صفحات کوپن...")
    coupon_pages = get_coupon_page_links()
    print(f"✅ {len(coupon_pages)} صفحه کوپن پیدا شد")
    
    # ۲. از هر صفحه، لینک‌های offers را بگیر
    all_data = []
    for idx, page_url in enumerate(coupon_pages[:10], 1):  # محدود به ۱۰ صفحه اول برای سرعت
        print(f"🔍 [{idx}/{min(10, len(coupon_pages))}] در حال پردازش: {page_url}")
        data = extract_offer_links(page_url)
        if data and data["offer_links"]:
            all_data.append(data)
    
    print(f"✅ جمعاً {len(all_data)} کوپن با لینک offer پیدا شد")
    
    # ۳. ساخت پیام‌ها در چند بخش
    if not all_data:
        message = "❌ هیچ کوپن جدیدی پیدا نشد."
        send_telegram(message)
        return

    header = f"🎉 کوپن‌های Great Clips ({datetime.now().strftime('%Y-%m-%d %H:%M')})\n"
    header += f"{'='*40}\n\n"

    message = header
    CHUNK_LIMIT = 3500  # کمی کمتر از 4096 برای حاشیه امن

    def send_if_meaningful(text: str):
        text = text.rstrip()
        # اگر خالی یا فقط «ادامه...» است، نفرست
        if not text:
            return
        if text.strip() == "(ادامه...)":
            return
        send_telegram(text)

    for idx, item in enumerate(all_data, 1):
        block = ""
        block += f"🔸 کوپن {idx}: {item['price']}\n"
        block += f"📄 {item['title']}\n"
        block += f"🔗 صفحه: {item['page_url']}\n"
        block += f"💳 لینک‌های Offer:\n"
        for link in item['offer_links'][:5]:  # حداکثر ۵ لینک برای هر کوپن
            block += f"   • {link}\n"
        block += "\n"

        # اگر اضافه کردن این بلاک باعث شود پیام از حد بگذرد، پیام فعلی را بفرست
        if len(message) + len(block) > CHUNK_LIMIT:
            send_if_meaningful(message)
            message = "(ادامه...)\n\n" + block
        else:
            message += block
    
    # ارسال بخش آخر
    send_if_meaningful(message)
    
    print("✅ اتمام کار")

if __name__ == "__main__":
    main()
