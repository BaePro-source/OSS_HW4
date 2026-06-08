# 🍽️ 맛집 추천 AI Agent

13주차 실습 과제 - Agentic Design Pattern을 활용한 맛집 찾기 AI Agent

---

## 프로젝트 개요

사용자의 자연어 요청을 분석하여 ReAct 패턴을 포함한 4가지 Agentic Design Pattern으로
맛집을 탐색하고 추천하는 AI Agent입니다.

Naver Search API를 활용해 실제 맛집 데이터를 조회하며, OpenAI GPT-4o 기반으로 동작합니다.

---

## 적용한 Agentic Design Pattern (4가지)

### 1. ReAct Pattern (필수)
**Thought → Action → Observation → Final Answer** 구조

- Agent가 현재 상황을 분석(Thought)하고, 적절한 도구를 선택(Action)하여 호출하고,
  도구 실행 결과(Observation)를 바탕으로 다음 행동을 결정하는 루프를 반복
- OpenAI Function Calling API를 활용하여 구현
- 구현 위치: `agent.py` → `run_react_loop()`

```
[STEP 1]
💭 Thought: 전주 객사 근처 맛집을 검색해야겠다.
🔧 Action: search_nearby_restaurants
📥 Input: {"landmark": "전주 객사", "radius_m": 1000}
👁️  Observation: {"status": "success", "total": 15, "results": [...]}

[STEP 2]
💭 Thought: 결과를 바탕으로 가격이 저렴하고 좋은 곳 3곳을 추천한다.
(Final Answer 생성)
```

### 2. Plan-and-Solve Pattern
사용자의 요청을 단계별로 분해하여 실행 계획을 수립 후 진행

- 지역 분석 → 조건 파악 → 검색 전략 → 필터링 기준 → 최종 추천 방식
- ReAct 루프 시작 전에 실행하여 Agent에게 컨텍스트 제공
- 구현 위치: `agent.py` → `create_plan()`

### 3. Reflection Pattern
추천 결과가 사용자 조건에 맞는지 자체 검토

- 지역·가격·리뷰·동행자·목적 등 5가지 기준으로 평가
- 부족한 부분이 있으면 보완 의견을 최종 답변에 추가
- 구현 위치: `agent.py` → `reflect()`

### 4. Memory Pattern
대화 간 사용자 선호도를 기억하여 추천에 반영

- 동행자, 목적, 가격 선호도, 선호 음식 종류 등 자동 추출·저장
- 후속 질문에서 이전 대화 맥락 반영
- 구현 위치: `agent.py` → `UserMemory` 클래스

---

## 맛집 검색 도구 (Tool Use Pattern)

| 도구 | 설명 |
|------|------|
| `search_restaurants` | 지역·음식종류 키워드로 맛집 검색 (지역 좌표 자동 조회 후 거리순 정렬) |
| `search_nearby_restaurants` | 특정 랜드마크 근처 반경 내 맛집을 거리순으로 검색 |

두 도구 모두 **Naver Search API**를 사용하며, 가게명·카테고리·주소·전화번호·네이버 URL을 반환합니다. 검색 결과는 리뷰 수(`comment`) 기준으로 정렬됩니다.

---

## 예외 처리

| 상황 | 처리 방식 |
|------|-----------|
| 존재하지 않는 지역 | `location_not_found` 에러 반환, 구체적 입력 방법 안내 |
| 검색 결과 없음 | `no_results` 에러 반환, 반경 확장 또는 검색어 변경 제안 |
| 음식 종류 모호 | LLM이 내부 카테고리 맵으로 자동 매핑 후 재시도 |
| API 호출 실패 | `network_error` / `auth_error` / `api_error` 구분 처리 |
| 조건 부족 | Memory에 저장된 선호도로 기본값 추정 후 검색 |

---

## 실행 환경

- Python 3.9 이상
- OpenAI API Key 필요
- Naver Search API Client ID / Client Secret 필요

### 설치

```bash
pip install -r requirements.txt
cp .env.example .env
# .env 파일에 OPENAI_API_KEY, NAVER_CLIENT_ID, NAVER_CLIENT_SECRET 입력
```

### 실행

```bash
# 과제 테스트 시나리오 (데모 모드)
python main.py demo

# 대화형 모드
python main.py

# 단일 쿼리
python main.py query "홍대에서 파스타 맛집 추천해줘"
```

---

## 외부 API 사용 방법

### Naver Search API

1. [developers.naver.com](https://developers.naver.com)에서 애플리케이션 등록
2. 사용 API → **검색** 선택
3. Client ID / Client Secret 복사
4. `.env` 파일에 입력:
   ```
   NAVER_CLIENT_ID=발급받은_Client_ID
   NAVER_CLIENT_SECRET=발급받은_Client_Secret
   ```

사용 엔드포인트:
- 지역 검색: `https://openapi.naver.com/v1/search/local.json`
- 요청 헤더: `X-Naver-Client-Id`, `X-Naver-Client-Secret`
- 검색 결과는 리뷰 수(`sort=comment`) 기준으로 정렬하여 조회

---

## 파일 구조

```
OSS_HW4/
├── main.py          # 실행 진입점 (데모/대화형/단일쿼리 모드)
├── agent.py         # ReAct Agent + 4가지 패턴 구현
├── tools.py         # 맛집 검색 도구 2종 + OpenAI Tool Definitions
├── requirements.txt
├── .env.example     # API Key 설정 예시
└── README.md
```

---

## 테스트 시나리오

**과제 지정 쿼리:**
> "전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘.
> 너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘."

실행:
```bash
python main.py demo
```

Agent 실행 흐름:
1. **Memory**: 친구, 저녁식사, 저렴 키워드 추출·저장
2. **Plan**: 전주 객사 검색 → 가격/거리 기준 필터 계획 수립
3. **ReAct Step 1**: `search_nearby_restaurants("전주 객사", radius_m=1000)` 호출
4. **ReAct Step 2**: 필요 시 `search_restaurants("전주 객사", food_type=...)` 추가 호출
5. **Reflection**: 조건 충족 여부 자체 검토
6. **Final Answer**: 최종 추천 3곳 출력
# OSS_HW4
