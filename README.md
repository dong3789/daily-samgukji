# daily-samgukji

매일 삼국지연의 한 회를 번역해서 웹 리더에 발행하고, 텔레그램으로 구독자에게 보내주는 프로젝트.

## 하는 일

- `chapters/` 에 있는 삼국지연의 원문 텍스트를 읽음
- Gemini를 사용해 현대 한국어 소설체 HTML로 번역함
- 등장인물, 관계, 장면, 지역 메타데이터를 생성함
- `web/chapters/*.json` 형태로 웹 리더용 데이터를 발행함
- 텔레그램 구독자에게 매일 새 회차 링크를 전송함
- 별도 봇으로 `/start`, `/stop`, `/status` 구독 관리를 처리함

## 프로젝트 구조

- `send.py` — 하루 한 회 처리: 번역, 메타데이터 생성, 웹 발행, 텔레그램 전송
- `bot.py` — 텔레그램 구독/해지/상태 확인 봇
- `regen_meta.py` — 기존 회차 메타데이터 재생성 스크립트
- `chapters/` — 원문 텍스트
- `web/` — 웹 리더 정적 파일 및 발행된 JSON
- `subscribers.json` — 구독자 목록
- `state.json` — 다음 발행 회차 상태
- `Dockerfile` — 봇 실행용 컨테이너 설정

## 요구 사항

- Python 3.12+
- Telegram Bot Token
- Gemini API Key

설치:

```bash
pip install -r requirements.txt
```

## 환경 변수

`.env` 파일 또는 환경 변수로 아래 값을 설정해야 함.

- `GEMINI_API_KEY` — Gemini API 키
- `TELEGRAM_BOT_TOKEN` — 텔레그램 봇 토큰
- `TELEGRAM_CHAT_ID` — 기본 알림을 받을 텔레그램 chat id
- `BASE_URL` — 웹 리더 주소 (예: `https://example.com/daily-samgukji/`)

예시:

```env
GEMINI_API_KEY=your_gemini_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=123456789
BASE_URL=https://your-site.example/daily-samgukji/
```

## 실행 방법

### 1) 텔레그램 봇 실행

```bash
python3 bot.py
```

기능:
- `/start` 구독 시작
- `/stop` 구독 해지
- `/status` 현재 발행 상태 확인

### 2) 하루 한 회 발행

```bash
python3 send.py
```

동작 순서:
1. `state.json` 에서 다음 회차 번호 확인
2. 원문 로드
3. Gemini 번역
4. 메타데이터 생성
5. `web/chapters/{번호}.json` 저장
6. `web/index.json` 갱신
7. 텔레그램 구독자 전체에게 링크 발송
8. 다음 회차 번호 저장

## 데이터 형식

웹 리더용 챕터 파일 예시:

```json
{
  "num": 1,
  "title": "제1회",
  "original_title": "第一回 宴桃园豪杰三结义 斩黄巾英雄首立功",
  "content": "<p>...</p>",
  "meta": {
    "characters": [],
    "relationships": [],
    "scenes": [],
    "locations": [],
    "location_coords": {}
  }
}
```

## 배포/운영 메모

- 현재 `Dockerfile` 은 `bot.py` 실행 기준으로 구성되어 있음
- `send.py` 는 cron, GitHub Actions, 외부 스케줄러 등으로 하루 1회 실행하는 구조가 적합함
- `subscribers.json`, `state.json` 은 런타임 중 갱신되므로 영속 저장소 관리가 필요함

## 주의 사항

- `subscribers.json` 에는 실제 구독자 chat id가 들어가므로 공개 저장소 관리 시 주의 필요
- `.env`, API 키, 토큰은 절대 커밋하면 안 됨
- 번역과 메타데이터 생성 모두 외부 API 비용/레이트리밋 영향을 받음

## 다음에 개선해볼 만한 것

- `state.json` 초기화/복구 로직 보강
- 구독자 저장을 JSON 파일 대신 DB로 변경
- 텔레그램 전송 실패 재시도
- 웹 리더 배포 방식 문서화
- 스케줄러 설정 예시 추가
- 테스트 코드 추가
