
import os
import time
import json
import logging
from pathlib import Path
from urllib.parse import quote

import feedparser
import requests
from dotenv import load_dotenv

load_dotenv()

# ===== CONFIGURATION =====
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

SUBREDDIT = "PathOfExile2"
POLL_INTERVAL = 60  # Kiểm tra mỗi 60 giây

SEEN_FILE = Path("seen_posts.json")

RSS_URL = (
    f"https://www.reddit.com/r/{SUBREDDIT}/search.rss"
    "?q=flair%3AGiveaway&restrict_sr=1&sort=new"
)

HEADERS = {
    "User-Agent": "PersonalGiveawayNotifier/1.0"
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


def load_seen():
    """Đọc danh sách bài đã xử lý."""
    if SEEN_FILE.exists():
        try:
            return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            logging.warning("Không đọc được seen_posts.json")
    return set()


def save_seen(seen):
    """Lưu danh sách bài đã xử lý."""
    SEEN_FILE.write_text(
        json.dumps(list(seen), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def fetch_posts():
    """Lấy bài đăng từ RSS."""
    response = requests.get(
        RSS_URL,
        headers=HEADERS,
        timeout=20,
    )
    response.raise_for_status()

    feed = feedparser.parse(response.content)

    if feed.bozo:
        logging.warning("RSS có thể không hợp lệ: %s", feed.bozo_exception)

    return feed.entries


def send_telegram(message):
    """Gửi thông báo đến Telegram."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    response.raise_for_status()

    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(f"Telegram API error: {result}")


def get_post_id(entry):
    """Tạo ID ổn định cho mỗi bài đăng."""
    return entry.get("id") or entry.get("link", "")


def format_message(entry):
    title = entry.get("title", "(Không có tiêu đề)")
    link = entry.get("link", "")
    published = entry.get("published", "Không rõ")

    return (
        "🎁 GIVEAWAY MỚI — Path of Exile 2\n\n"
        f"📌 {title}\n\n"
        f"🕒 {published}\n"
        f"🔗 {link}"
    )


def main():
    if not BOT_TOKEN or not CHAT_ID:
        raise SystemExit(
            "Thiếu TELEGRAM_BOT_TOKEN hoặc TELEGRAM_CHAT_ID trong .env"
        )

    seen = load_seen()

    logging.info("Đang khởi động theo dõi r/%s", SUBREDDIT)

    # Lần đầu chạy: ghi nhận bài hiện có, không gửi thông báo hàng loạt.
    if not seen:
        try:
            entries = fetch_posts()
            for entry in entries:
                post_id = get_post_id(entry)
                if post_id:
                    seen.add(post_id)

            save_seen(seen)
            logging.info("Đã ghi nhận %d bài hiện có.", len(seen))
        except Exception as exc:
            logging.warning("Không thể khởi tạo RSS: %s", exc)

    while True:
        try:
            entries = fetch_posts()

            # RSS thường trả bài mới trước, nên xử lý bài cũ trước.
            new_entries = []

            for entry in entries:
                post_id = get_post_id(entry)
                if post_id and post_id not in seen:
                    new_entries.append((post_id, entry))

            for post_id, entry in reversed(new_entries):
                try:
                    send_telegram(format_message(entry))
                    logging.info("Đã gửi: %s", entry.get("title", post_id))
                except Exception:
                    logging.exception("Gửi Telegram thất bại")
                    continue

                seen.add(post_id)
                save_seen(seen)

        except Exception:
            logging.exception("Lỗi khi kiểm tra RSS")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
