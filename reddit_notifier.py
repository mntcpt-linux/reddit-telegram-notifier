import os
import time
import json
import logging
from pathlib import Path

import praw
import requests
from dotenv import load_dotenv

load_dotenv()

# =========================
# Cấu hình
# =========================
SUBREDDIT = "PathOfExile2"
TARGET_FLAIR = "Giveaway"

POLL_INTERVAL = 60
STATE_FILE = Path("seen_posts.json")

REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER_AGENT = os.getenv(
    "REDDIT_USER_AGENT",
    "personal-giveaway-notifier/1.0"
)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# =========================
# Khởi tạo Reddit API
# =========================
def create_reddit_client():
    if not REDDIT_CLIENT_ID or not REDDIT_CLIENT_SECRET:
        raise ValueError("Thiếu thông tin xác thực Reddit API.")

    return praw.Reddit(
        client_id=REDDIT_CLIENT_ID,
        client_secret=REDDIT_CLIENT_SECRET,
        user_agent=REDDIT_USER_AGENT,
        check_for_async=False,
    )


# =========================
# Đọc và lưu trạng thái
# =========================
def load_seen_posts():
    if not STATE_FILE.exists():
        return set()

    try:
        with STATE_FILE.open("r", encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError):
        logging.warning("Không đọc được file trạng thái.")
        return set()


def save_seen_posts(seen_ids):
    with STATE_FILE.open("w", encoding="utf-8") as f:
        json.dump(list(seen_ids), f, ensure_ascii=False, indent=2)


# =========================
# Gửi thông báo Telegram
# =========================
def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise ValueError("Thiếu Telegram Bot Token hoặc Chat ID.")

    url = (
        f"https://api.telegram.org/bot"
        f"{TELEGRAM_BOT_TOKEN}/sendMessage"
    )

    response = requests.post(
        url,
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=20,
    )

    response.raise_for_status()
    result = response.json()

    if not result.get("ok"):
        raise RuntimeError(f"Telegram API lỗi: {result}")


# =========================
# Tạo nội dung thông báo
# =========================
def format_post(submission):
    title = submission.title
    url = f"https://www.reddit.com{submission.permalink}"
    author = submission.author.name if submission.author else "[deleted]"

    return (
        "🎁 Giveaway mới trong r/PathOfExile2!\n\n"
        f"📌 {title}\n\n"
        f"🏷 Flair: {submission.link_flair_text or 'N/A'}\n"
        f"👤 Tác giả: u/{author}\n"
        f"🔗 {url}"
    )


# =========================
# Theo dõi bài đăng mới
# =========================
def main():
    reddit = create_reddit_client()
    subreddit = reddit.subreddit(SUBREDDIT)

    seen_ids = load_seen_posts()

    # Nếu chạy lần đầu, ghi nhận bài mới nhất làm mốc.
    # Không gửi thông báo cho các bài đã tồn tại trước đó.
    if not seen_ids:
        latest_posts = list(subreddit.new(limit=1))

        if latest_posts:
            seen_ids.add(latest_posts[0].id)
            save_seen_posts(seen_ids)

        logging.info("Đã thiết lập mốc theo dõi ban đầu.")

    logging.info(
        "Bắt đầu theo dõi r/%s với flair '%s'.",
        SUBREDDIT,
        TARGET_FLAIR,
    )

    while True:
        try:
            posts = list(subreddit.new(limit=100))

            # Xử lý từ bài cũ đến bài mới để thông báo đúng thứ tự.
            new_posts = [
                post for post in reversed(posts)
                if post.id not in seen_ids
            ]

            for post in new_posts:
                seen_ids.add(post.id)

                flair = (post.link_flair_text or "").strip()

                if flair.casefold() == TARGET_FLAIR.casefold():
                    message = format_post(post)

                    try:
                        send_telegram_message(message)
                        logging.info("Đã gửi thông báo: %s", post.id)
                    except Exception:
                        logging.exception(
                            "Không gửi được thông báo cho bài %s",
                            post.id,
                        )

            # Giới hạn kích thước file trạng thái.
            seen_ids = set(list(seen_ids)[-5000:])
            save_seen_posts(seen_ids)

        except Exception:
            logging.exception("Lỗi khi kiểm tra Reddit.")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
