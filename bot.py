#!/usr/bin/env python3
"""출근길삼국지 텔레그램 봇 - 구독/해지 관리 + 상시 실행"""

import os
import json
import time
import requests
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
SUBSCRIBERS_FILE = Path(__file__).parent / "subscribers.json"
BASE_URL = os.environ.get("BASE_URL", "")
STATE_FILE = Path(__file__).parent / "state.json"


def load_subscribers() -> dict:
    """구독자 목록 로드. {chat_id: {name, subscribed_at}}"""
    if SUBSCRIBERS_FILE.exists():
        return json.loads(SUBSCRIBERS_FILE.read_text())
    return {}


def save_subscribers(subs: dict):
    SUBSCRIBERS_FILE.write_text(json.dumps(subs, ensure_ascii=False, indent=2))


def get_current_chapter() -> int:
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        return state.get("next_chapter", 1)
    return 1


def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    })
    return resp.ok


def handle_message(message):
    chat_id = str(message["chat"]["id"])
    text = message.get("text", "").strip()
    user = message.get("from", {})
    name = user.get("first_name", "") + " " + user.get("last_name", "")
    name = name.strip()

    subs = load_subscribers()

    if text == "/start":
        if chat_id not in subs:
            subs[chat_id] = {"name": name, "subscribed_at": int(time.time())}
            save_subscribers(subs)

        current = get_current_chapter() - 1 or 1
        reader_url = f"{BASE_URL}#1" if BASE_URL else ""
        send_message(chat_id,
            f"📖 <b>출근길 삼국지</b>에 오신 걸 환영합니다!\n\n"
            f"매일 아침 7시, 삼국지연의 한 회를 번역해서 보내드립니다.\n"
            f"현재 {current}회까지 발행되었어요.\n\n"
            f"📚 웹 리더: {reader_url}\n\n"
            f"/stop - 구독 해지\n"
            f"/status - 진행 상황"
        )

    elif text == "/stop":
        if chat_id in subs:
            del subs[chat_id]
            save_subscribers(subs)
        send_message(chat_id, "구독이 해지되었습니다. 다시 읽고 싶으시면 /start 를 보내주세요.")

    elif text == "/status":
        current = get_current_chapter() - 1 or 0
        send_message(chat_id,
            f"📚 <b>출근길 삼국지 현황</b>\n\n"
            f"발행: {current}/120회\n"
            f"다음 발행: 내일 아침 7시"
        )

    else:
        send_message(chat_id,
            "📖 <b>출근길 삼국지</b>\n\n"
            "/start - 구독하기\n"
            "/stop - 구독 해지\n"
            "/status - 진행 상황"
        )


def poll():
    """Long polling으로 메시지 수신"""
    offset = 0
    print("Bot started. Polling for messages...")

    while True:
        try:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
            resp = requests.get(url, params={
                "offset": offset,
                "timeout": 30,
            }, timeout=35)

            if not resp.ok:
                print(f"Error: {resp.status_code}")
                time.sleep(5)
                continue

            data = resp.json()
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                if "message" in update:
                    handle_message(update["message"])

        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    poll()
