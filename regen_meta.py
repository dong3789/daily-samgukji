#!/usr/bin/env python3
"""기존 챕터 1-4에 메타데이터를 생성하여 추가하는 스크립트"""

import json
import os
import sys
from pathlib import Path
from google import genai
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

LOCATION_COORDS = {
    "낙양": [52, 35], "장안": [40, 35], "허창": [55, 40], "업군": [55, 30],
    "성도": [28, 52], "형주": [48, 52], "강릉": [48, 50], "양양": [50, 45],
    "강동": [65, 50], "건업": [65, 48], "오군": [68, 52], "회계": [72, 55],
    "서주": [62, 35], "유주": [58, 18], "기주": [55, 22], "연주": [58, 35],
    "청주": [63, 28], "예주": [55, 38], "양주": [65, 45], "익주": [30, 55],
    "옹주": [38, 32], "병주": [48, 22], "교주": [52, 72], "량주": [28, 30],
    "탁군": [58, 18], "탁현": [58, 18], "거록": [57, 25], "광종": [58, 26],
    "영천": [55, 40], "완성": [52, 45], "남양": [50, 43], "여남": [57, 43],
    "진류": [57, 37], "북해": [64, 30], "동래": [68, 28],
    "상산": [56, 24], "산양": [60, 36], "발해": [60, 22], "하내": [52, 32],
    "하동": [46, 32], "남피": [60, 24], "북평": [62, 18], "요동": [68, 12],
    "서량": [25, 30], "동군": [57, 33], "진류군": [57, 37], "소패": [60, 38],
    "하비": [62, 38], "수춘": [62, 42], "여강": [62, 45], "장사": [48, 58],
    "계양": [50, 62], "영릉": [46, 60], "무릉": [42, 55], "한중": [35, 42],
    "천수": [32, 35], "적벽": [50, 50], "번성": [50, 44], "맥성": [46, 48],
    "오장원": [38, 38], "기산": [33, 36], "정군산": [36, 42], "동관": [42, 36],
    "호로관": [50, 34], "사수관": [52, 36], "함곡관": [46, 35],
}

known_locations = ", ".join(LOCATION_COORDS.keys())

start = int(sys.argv[1]) if len(sys.argv) > 1 else 1
end = int(sys.argv[2]) if len(sys.argv) > 2 else 4

for num in range(start, end + 1):
    print(f"Generating metadata for chapter {num}...")

    chapter_path = Path(__file__).parent / f"chapters/chapter_{num:03d}.txt"
    chinese_text = chapter_path.read_text(encoding="utf-8")

    prompt = f"""삼국지연의 제{num}회의 원문을 분석하여 아래 JSON 형식으로 메타데이터를 추출하세요.
반드시 유효한 JSON만 출력하세요. 다른 텍스트는 절대 포함하지 마세요.

{{
  "characters": [
    {{"name": "유비", "title": "한실 종친", "side": "촉"}}
  ],
  "relationships": [
    {{"from": "유비", "to": "관우", "label": "의형제"}}
  ],
  "scenes": [
    {{"title": "도원결의", "description": "유비, 관우, 장비가 의형제를 맺다", "mood": "감동"}}
  ],
  "locations": ["낙양", "탁군"]
}}

규칙:
- characters: 주요 인물 최대 10명. side는 촉/위/오/한/황건적/동탁/여포/원소/기타 중 택1
- relationships: 핵심 관계 최대 8개. label은 2-4글자
- scenes: 핵심 장면 3-5개. mood는 전투/긴장/감동/모략/비극/희극/장엄 중 택1
- locations: 다음 목록에서만 선택: {known_locations}

원문:
{chinese_text}"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )

    text = response.text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        meta = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        meta = {"characters": [], "relationships": [], "scenes": [], "locations": []}

    meta["location_coords"] = {
        loc: LOCATION_COORDS[loc]
        for loc in meta.get("locations", [])
        if loc in LOCATION_COORDS
    }

    # 기존 JSON에 메타데이터 추가
    json_path = Path(__file__).parent / f"web/chapters/{num:03d}.json"
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data["meta"] = meta
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    chars = len(meta.get("characters", []))
    scenes = len(meta.get("scenes", []))
    locs = len(meta.get("locations", []))
    print(f"  -> {chars} characters, {scenes} scenes, {locs} locations")

print("All done!")
