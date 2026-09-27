# Reddit Telegram Giveaway Notifier

A personal, non-commercial Python application that monitors
public posts in r/PathOfExile2 and sends Telegram notifications
for posts with the Giveaway flair.

## Features
- Read-only Reddit monitoring
- Filters posts by Giveaway flair
- Sends notifications to a private Telegram chat
- Stores processed post IDs to avoid duplicate notifications

## Requirements
- Python 3.10+
- Reddit API credentials and appropriate access
- Telegram Bot Token and Chat ID

## Setup
1. Install dependencies:
   pip install -r requirements.txt

2. Configure credentials in .env.

3. Run:
   python reddit_notifier.py

## Privacy
Credentials are stored locally in .env.
The application does not automatically enter giveaways,
comment, vote, or message Reddit users.
