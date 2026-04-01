#!/usr/bin/env python3
"""매일 삼국지 한 회를 번역해서 웹 리더에 발행하고 텔레그램으로 링크를 보내는 스크립트"""

import os
import json
import time
import requests
from pathlib import Path
from google import genai

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
CHAPTERS_DIR = Path(__file__).parent / "chapters"
WEB_CHAPTERS_DIR = Path(__file__).parent / "web" / "chapters"
WEB_DIR = Path(__file__).parent / "web"
STATE_FILE = Path(__file__).parent / "state.json"
BASE_URL = os.environ.get("BASE_URL", "")


def get_current_chapter() -> int:
    if STATE_FILE.exists():
        state = json.loads(STATE_FILE.read_text())
        return state.get("next_chapter", 1)
    return 1


def save_state(chapter: int):
    STATE_FILE.write_text(json.dumps({"next_chapter": chapter}))


def load_chapter(num: int) -> str:
    path = CHAPTERS_DIR / f"chapter_{num:03d}.txt"
    if not path.exists():
        raise FileNotFoundError(f"Chapter {num} not found")
    return path.read_text(encoding="utf-8")


def get_client():
    return genai.Client(api_key=GEMINI_API_KEY)


# 삼국지 주요 지역 좌표 (SVG 맵 기준 % 좌표)
LOCATION_COORDS = {
    "낙양": [52, 35], "장안": [40, 35], "허창": [55, 40], "업군": [55, 30],
    "성도": [28, 52], "형주": [48, 52], "강릉": [48, 50], "양양": [50, 45],
    "강동": [65, 50], "건업": [65, 48], "오군": [68, 52], "회계": [72, 55],
    "서주": [62, 35], "유주": [58, 18], "기주": [55, 22], "연주": [58, 35],
    "청주": [63, 28], "예주": [55, 38], "양주": [65, 45], "익주": [30, 55],
    "옹주": [38, 32], "병주": [48, 22], "교주": [52, 72], "량주": [28, 30],
    "탁군": [58, 18], "탁현": [58, 18], "거록": [57, 25], "광종": [58, 26],
    "영천": [55, 40], "완성": [52, 45], "남양": [50, 43], "여남": [57, 43],
    "진류": [57, 37], "동탁": [40, 35], "북해": [64, 30], "동래": [68, 28],
    "상산": [56, 24], "산양": [60, 36], "발해": [60, 22], "하내": [52, 32],
    "하동": [46, 32], "남피": [60, 24], "북평": [62, 18], "요동": [68, 12],
    "서량": [25, 30], "동군": [57, 33], "진류군": [57, 37], "소패": [60, 38],
    "하비": [62, 38], "수춘": [62, 42], "여강": [62, 45], "장사": [48, 58],
    "계양": [50, 62], "영릉": [46, 60], "무릉": [42, 55], "한중": [35, 42],
    "천수": [32, 35], "미축": [28, 48], "백제성": [32, 48], "이릉": [40, 50],
    "적벽": [50, 50], "번성": [50, 44], "맥성": [46, 48], "오장원": [38, 38],
    "기산": [33, 36], "정군산": [36, 42], "동관": [42, 36], "호로관": [50, 34],
    "사수관": [52, 36], "함곡관": [46, 35],
}


def generate_metadata(chinese_text: str, chapter_num: int) -> dict:
    """Gemini로 챕터 메타데이터 (인물, 장면, 지역) 추출"""
    client = get_client()

    known_locations = ", ".join(LOCATION_COORDS.keys())

    prompt = f"""삼국지연의 제{chapter_num}회의 원문을 분석하여 아래 JSON 형식으로 메타데이터를 추출하세요.
반드시 유효한 JSON만 출력하세요. 다른 텍스트는 절대 포함하지 마세요.

{{
  "characters": [
    {{
      "name": "유비",
      "title": "한실 종친, 중산정왕의 후예",
      "side": "촉"
    }}
  ],
  "relationships": [
    {{
      "from": "유비",
      "to": "관우",
      "label": "의형제"
    }}
  ],
  "scenes": [
    {{
      "title": "도원결의",
      "description": "유비, 관우, 장비가 장비의 도원에서 의형제를 맺다",
      "mood": "감동"
    }}
  ],
  "locations": ["낙양", "탁군"]
}}

규칙:
- characters: 이 회에 등장하는 주요 인물 (최대 10명). side는 촉/위/오/한/황건적/동탁/여포/원소/기타 중 택1
- relationships: 인물 간 핵심 관계 (최대 8개). label은 2-4글자로 간결하게 (예: 의형제, 군신, 적대, 부자, 사제)
- scenes: 핵심 장면 3-5개. mood는 전투/긴장/감동/모략/비극/희극/장엄 중 택1
- locations: 이 회에서 언급되는 지역명. 반드시 다음 목록에서만 선택: {known_locations}

원문:
{chinese_text}"""

    from google.genai import types
    config = types.GenerateContentConfig(max_output_tokens=8192)
    text = _call_gemini(client, prompt, config)
    # JSON 블록 추출
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        meta = json.loads(text)
    except json.JSONDecodeError:
        meta = {"characters": [], "relationships": [], "scenes": [], "locations": []}

    # 좌표 매핑
    meta["location_coords"] = {
        loc: LOCATION_COORDS[loc]
        for loc in meta.get("locations", [])
        if loc in LOCATION_COORDS
    }

    return meta


TRANSLATE_SYSTEM = """당신은 한국의 베스트셀러 역사소설 작가이자 삼국지연의 전문 번역가입니다.
중국어 원문을 한국 독자가 소설처럼 몰입해서 읽을 수 있는 현대 한국어로 번역해주세요.

## 문체 원칙
- 마치 한국 작가가 직접 쓴 소설처럼 자연스러운 한국어를 사용하세요.
- 직역 투(~하였다, ~한 바, ~하는 것이다)를 피하고, 실제 한국 소설에서 쓰는 문장 구조를 사용하세요.
- 문장은 짧고 리듬감 있게. 한 문장이 너무 길면 둘로 나누세요.
- 대화문은 캐릭터의 성격과 상황에 맞는 살아있는 말투로 번역하세요.
  - 장수나 호걸: 호탕하고 거친 말투 ("이놈!", "어디 한번 덤벼보거라!")
  - 황제나 고관: 위엄 있는 말투
  - 일반 서술: 현대 한국어 소설체
- 고어체나 번역 투("~하였노라", "~인즉", "납시었다")는 사용하지 마세요.
- 감정과 분위기를 살려주세요. 전투 장면은 긴박하게, 모략 장면은 긴장감 있게.

## 고유명사
- 인명, 지명은 한국식 한자 독음 사용 (예: 刘备→유비, 曹操→조조, 关羽→관우)
- 처음 등장하는 인물은 "유비(劉備)" 형태로 한 번만 한자를 병기하세요.

## 서술 방식
- 원문의 의미를 충실히 전달하되, 한국어로 자연스럽게 의역하세요.
- 중국 고전 특유의 압축적 표현은 풀어서 설명하세요.

## 포맷 규칙
- 시(詩)나 노래: <div class="poem"><p>줄1</p><p>줄2</p></div> 형태
- 일반 문단: <p>내용</p> 태그
- 대화문: 큰따옴표로 감싸기
- 반드시 HTML 태그(<p>, <div>)만 사용. 마크다운 사용 금지.
- 제목은 포함하지 마세요. 본문만 번역하세요.
- 원문을 절대 빠뜨리지 말고 끝까지 완역하세요."""


def _split_text(text: str, max_chars: int = 2500) -> list[str]:
    """문단 단위로 텍스트를 분할"""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks = []
    current = []
    current_len = 0
    for p in paragraphs:
        if current_len + len(p) > max_chars and current:
            chunks.append("\n\n".join(current))
            current = [p]
            current_len = len(p)
        else:
            current.append(p)
            current_len += len(p)
    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _call_gemini(client, prompt, config, max_retries=5):
    """Rate limit 대응 재시도 로직"""
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt, config=config,
            )
            return response.text
        except Exception as e:
            if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                wait = 15 * (attempt + 1)
                print(f"  Rate limit hit, waiting {wait}s (attempt {attempt+1}/{max_retries})...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Max retries exceeded for Gemini API")


def translate_chapter(chinese_text: str, chapter_num: int) -> str:
    from google.genai import types
    client = get_client()
    config = types.GenerateContentConfig(max_output_tokens=65536)

    chunks = _split_text(chinese_text)

    if len(chunks) <= 1:
        prompt = f"{TRANSLATE_SYSTEM}\n\n원문:\n{chinese_text}"
        return _call_gemini(client, prompt, config)

    # 분할 번역
    parts = []
    for i, chunk in enumerate(chunks):
        context = f"(제{chapter_num}회 중 {i+1}/{len(chunks)} 파트)"
        if i > 0:
            context += "\n앞부분은 이미 번역되었습니다. 이어서 번역하세요."
        prompt = f"{TRANSLATE_SYSTEM}\n\n{context}\n\n원문:\n{chunk}"
        parts.append(_call_gemini(client, prompt, config))
        if i < len(chunks) - 1:
            time.sleep(5)  # 청크 간 딜레이

    return "\n".join(parts)


def save_web_chapter(chapter_num: int, translated_html: str, original_title: str, metadata: dict = None):
    """번역된 챕터를 웹 리더용 JSON으로 저장"""
    WEB_CHAPTERS_DIR.mkdir(parents=True, exist_ok=True)

    data = {
        "num": chapter_num,
        "title": f"제{chapter_num}회",
        "original_title": original_title,
        "content": translated_html,
    }
    if metadata:
        data["meta"] = metadata

    path = WEB_CHAPTERS_DIR / f"{chapter_num:03d}.json"
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    # index.json 업데이트
    update_index()
    return path


def update_index():
    """발행된 챕터 목록 index.json 업데이트"""
    chapters = []
    for f in sorted(WEB_CHAPTERS_DIR.glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        chapters.append({
            "num": data["num"],
            "title": data.get("original_title", f"제{data['num']}회"),
        })
    index_path = WEB_DIR / "index.json"
    index_path.write_text(json.dumps(chapters, ensure_ascii=False, indent=2), encoding="utf-8")


SUBSCRIBERS_FILE = Path(__file__).parent / "subscribers.json"


def get_all_chat_ids() -> list[str]:
    """구독자 목록 + 기본 CHAT_ID 반환"""
    chat_ids = {CHAT_ID}
    if SUBSCRIBERS_FILE.exists():
        subs = json.loads(SUBSCRIBERS_FILE.read_text())
        chat_ids.update(subs.keys())
    return list(chat_ids)


def send_telegram(text: str):
    """모든 구독자에게 텔레그램 메시지 전송"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for chat_id in get_all_chat_ids():
        resp = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False,
        })
        if not resp.ok:
            print(f"Failed to send to {chat_id}: {resp.text}")


def main():
    chapter_num = get_current_chapter()
    if chapter_num > 120:
        send_telegram("📚 삼국지연의 120회를 모두 읽었습니다! 축하합니다! 🎉")
        return

    print(f"Processing chapter {chapter_num}...")
    chinese_text = load_chapter(chapter_num)

    # 회 제목 추출 (첫 줄)
    first_line = chinese_text.split("\n")[0].strip()

    print(f"Translating chapter {chapter_num} ({len(chinese_text)} chars)...")
    translated = translate_chapter(chinese_text, chapter_num)

    print("Generating metadata...")
    metadata = generate_metadata(chinese_text, chapter_num)

    print("Saving web chapter...")
    save_web_chapter(chapter_num, translated, first_line, metadata)

    print("Sending Telegram notification...")
    chapter_url = f"{BASE_URL}#{chapter_num}" if BASE_URL else f"(웹 리더 #{chapter_num})"
    message = f"📖 <b>출근길 삼국지 제{chapter_num}회</b>\n{first_line}\n\n{chapter_url}\n\n📚 {chapter_num}/120회"
    send_telegram(message)

    save_state(chapter_num + 1)
    print(f"Done! Chapter {chapter_num} saved.")


if __name__ == "__main__":
    main()
