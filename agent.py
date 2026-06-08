"""
맛집 추천 ReAct Agent
Agentic Design Patterns 구현:
  1. ReAct Pattern    - Thought → Action → Observation → Final Answer
  2. Plan-and-Solve   - 사용자 요청을 단계별로 분해하여 실행
  3. Reflection       - 추천 결과가 조건에 맞는지 자체 검토
  4. Memory Pattern   - 사용자 선호도 기억 및 활용
"""

import json
from typing import Optional
import openai

from tools import TOOL_DEFINITIONS, TOOL_MAP

# ─────────────────────────────────────────────
# Memory Pattern
# ─────────────────────────────────────────────

class UserMemory:
    """사용자의 선호도와 이전 대화 내용을 기억하는 메모리"""

    def __init__(self):
        self.preferred_food_types: list[str] = []
        self.price_preference: Optional[str] = None   # "저렴", "보통", "고급"
        self.max_price: Optional[int] = None
        self.companions: Optional[str] = None          # "친구", "가족", "연인", "혼자"
        self.purpose: Optional[str] = None             # "저녁식사", "점심", "술자리", "디저트"
        self.visited: list[str] = []
        self.disliked: list[str] = []
        self.conversation_history: list[dict] = []

    def update_from_query(self, query: str, client: "openai.OpenAI" = None):
        """GPT를 사용해 사용자 쿼리에서 선호도 정보 추출하여 메모리 업데이트"""
        if client is None:
            return

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=200,
            response_format={"type": "json_object"},
            messages=[{
                "role": "user",
                "content": (
                    "아래 사용자 발화에서 식당 관련 선호도 정보를 추출해 JSON으로 반환해.\n"
                    "추출할 수 없는 항목은 null로 해.\n\n"
                    "반환 형식:\n"
                    "{\n"
                    '  "companions": "친구|가족|연인|혼자|null",\n'
                    '  "purpose": "저녁식사|점심식사|술자리|카페/디저트|null",\n'
                    '  "price_preference": "저렴|보통|고급|null",\n'
                    '  "max_price": <1인당 최대 금액 숫자 또는 null>\n'
                    "}\n\n"
                    f"사용자 발화: {query}"
                )
            }]
        )

        try:
            data = json.loads(response.choices[0].message.content)
            if data.get("companions") and data["companions"] != "null":
                self.companions = data["companions"]
            if data.get("purpose") and data["purpose"] != "null":
                self.purpose = data["purpose"]
            if data.get("price_preference") and data["price_preference"] != "null":
                self.price_preference = data["price_preference"]
            if data.get("max_price"):
                self.max_price = int(data["max_price"])
        except (json.JSONDecodeError, ValueError):
            pass

    def add_conversation(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})

    def get_context(self) -> str:
        """메모리 컨텍스트를 문자열로 반환"""
        parts = []
        if self.companions:
            parts.append(f"동행: {self.companions}")
        if self.purpose:
            parts.append(f"목적: {self.purpose}")
        if self.price_preference:
            parts.append(f"가격 선호: {self.price_preference}")
        if self.max_price:
            parts.append(f"최대 예산: 1인당 {self.max_price:,}원")
        if self.preferred_food_types:
            parts.append(f"선호 음식: {', '.join(self.preferred_food_types)}")
        if self.visited:
            parts.append(f"방문한 곳: {', '.join(self.visited)}")
        if self.disliked:
            parts.append(f"비선호: {', '.join(self.disliked)}")

        if not parts:
            return "아직 저장된 사용자 정보가 없습니다."
        return "\n".join(parts)

    def has_history(self) -> bool:
        return bool(self.conversation_history)


# ─────────────────────────────────────────────
# ReAct Agent
# ─────────────────────────────────────────────

class RestaurantAgent:
    """
    맛집 추천 ReAct Agent

    적용 패턴:
    - ReAct: Thought→Action→Observation→Final Answer 루프
    - Plan-and-Solve: 실행 전 단계별 계획 수립
    - Reflection: 추천 결과 자체 검토
    - Memory: 사용자 선호도 기억
    """

    def __init__(self, verbose: bool = True):
        self.client = openai.OpenAI()
        self.memory = UserMemory()
        self.verbose = verbose
        self.max_steps = 10

    # ── Plan-and-Solve Pattern ──────────────────

    def create_plan(self, user_query: str) -> str:
        """
        Plan-and-Solve: 사용자 요청을 단계별 실행 계획으로 분해
        빠른 계획 수립을 위해 gpt-4o-mini 사용
        """
        if self.verbose:
            print("\n" + "="*60)
            print("📋 [Plan-and-Solve] 실행 계획 수립 중...")
            print("="*60)

        memory_ctx = self.memory.get_context()

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=600,
            messages=[{
                "role": "user",
                "content": (
                    f"아래 맛집 추천 요청을 분석하여 Agent 실행 계획을 세워주세요.\n\n"
                    f"사용자 요청: {user_query}\n"
                    f"사용자 메모리: {memory_ctx}\n\n"
                    "다음 형식으로 간략하게 작성:\n"
                    "1. 지역 분석: ...\n"
                    "2. 조건 파악: ...\n"
                    "3. 검색 전략: ...\n"
                    "4. 필터링 기준: ...\n"
                    "5. 최종 추천 방식: ..."
                )
            }]
        )

        plan = response.choices[0].message.content
        if self.verbose:
            print(plan)
        return plan

    # ── ReAct Loop ──────────────────────────────

    def run_react_loop(self, user_query: str, plan: str) -> str:
        """
        ReAct Pattern: Thought → Action → Observation → Final Answer 루프
        OpenAI의 Function Calling을 활용한 에이전틱 루프
        """
        if self.verbose:
            print("\n" + "="*60)
            print("🤖 [ReAct] Agent 실행 시작")
            print("="*60)

        system_content = (
            "당신은 맛집 추천 전문 AI Agent입니다.\n"
            "ReAct 패턴으로 동작하며, 네이버 검색 API 도구를 호출하여 실제 맛집을 추천합니다.\n\n"
            f"[실행 계획]\n{plan}\n\n"
            f"[사용자 메모리]\n{self.memory.get_context()}\n\n"
            "[도구 사용 지침]\n"
            "- search_restaurants: 지역 + 음식 종류 키워드로 광범위 검색\n"
            "- search_nearby_restaurants: 특정 랜드마크 근처 맛집 검색 (랜드마크 기준 추천 시 사용)\n"
            "- 두 도구를 조합해 더 정확한 결과를 얻을 수 있습니다.\n\n"
            "[주의사항]\n"
            "- 검색 결과는 리뷰 수 기준으로 정렬됩니다. 상위 결과가 리뷰가 많은 곳입니다.\n"
            "- 거리 정보는 제공되지 않으므로 주소를 기반으로 위치를 안내하세요.\n"
            "- 결과가 없으면 검색어를 바꾸거나 다른 도구로 재시도하세요.\n"
            "- 최종 추천 시 가게명, 카테고리, 주소, 전화번호, 네이버 URL을 포함하세요.\n"
            "- 한국어로 친근하게 답변하세요."
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_query},
        ]

        step = 0
        final_answer = ""

        while step < self.max_steps:
            step += 1

            response = self.client.chat.completions.create(
                model="gpt-4o",
                max_tokens=2048,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                messages=messages
            )

            choice = response.choices[0]
            message = choice.message

            # Thought 출력 (텍스트)
            if message.content and self.verbose:
                print(f"\n[STEP {step}]")
                print(f"💭 Thought:\n{message.content}")

            # 종료 조건: 도구 호출 없이 텍스트만 반환
            if choice.finish_reason == "stop" or not message.tool_calls:
                final_answer = message.content or ""
                break

            # assistant 메시지를 히스토리에 추가
            assistant_msg = {"role": "assistant", "content": message.content}
            if message.tool_calls:
                assistant_msg["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            messages.append(assistant_msg)

            # Action + Observation
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_input = json.loads(tool_call.function.arguments)

                if self.verbose:
                    print(f"\n🔧 Action: {tool_name}")
                    print(f"📥 Input: {json.dumps(tool_input, ensure_ascii=False, indent=2)}")

                result = self._execute_tool(tool_name, tool_input)

                if self.verbose:
                    print(f"👁️  Observation: {json.dumps(result, ensure_ascii=False, indent=2)}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

        if step >= self.max_steps and not final_answer:
            final_answer = "최대 반복 횟수에 도달했습니다. 현재까지 수집된 정보로 답변을 드립니다."

        return final_answer

    def _execute_tool(self, tool_name: str, tool_input: dict) -> dict:
        """도구 실행 및 예외 처리"""
        if tool_name not in TOOL_MAP:
            return {
                "status": "error",
                "error_type": "unknown_tool",
                "message": f"'{tool_name}'은 존재하지 않는 도구입니다.",
                "available_tools": list(TOOL_MAP.keys())
            }
        try:
            return TOOL_MAP[tool_name](**tool_input)
        except TypeError as e:
            return {
                "status": "error",
                "error_type": "invalid_input",
                "message": f"도구 입력값이 잘못되었습니다: {str(e)}"
            }
        except Exception as e:
            return {
                "status": "error",
                "error_type": "execution_error",
                "message": f"도구 실행 중 오류 발생: {str(e)}"
            }

    # ── Reflection Pattern ───────────────────────

    def reflect(self, user_query: str, answer: str) -> str:
        """
        Reflection Pattern: 생성된 추천 결과가 사용자 조건에 맞는지 자체 검토
        부족한 부분이 있으면 보완 의견을 추가
        """
        if self.verbose:
            print("\n" + "="*60)
            print("🔍 [Reflection] 추천 결과 자체 검토 중...")
            print("="*60)

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=400,
            messages=[{
                "role": "user",
                "content": (
                    f"아래 맛집 추천 결과가 사용자 요청을 충분히 만족하는지 검토해주세요.\n\n"
                    f"[사용자 요청]\n{user_query}\n\n"
                    f"[추천 결과]\n{answer}\n\n"
                    "다음 기준으로 평가하고 보완할 점이 있으면 1-2문장으로만 간략히 언급:\n"
                    "- 요청한 지역인가?\n"
                    "- 가격 조건에 맞는가?\n"
                    "- 리뷰/평점 기준을 충족하는가?\n"
                    "- 동행자/목적에 적합한가?\n"
                    "- 충분한 수의 추천이 제공되었는가?\n\n"
                    "만약 모든 기준을 충족하면 '✅ 추천 결과가 모든 조건을 충족합니다.'라고만 말하세요.\n"
                    "부족한 점이 있으면 '⚠️ 보완 의견:' 다음에 간략히 작성하세요."
                )
            }]
        )

        reflection = response.choices[0].message.content.strip()
        if self.verbose:
            print(reflection)
        return reflection

    # ── 메인 실행 ────────────────────────────────

    def run(self, user_query: str) -> str:
        """
        Agent 메인 실행 흐름:
        1. Memory 업데이트 (Memory Pattern)
        2. Plan 수립 (Plan-and-Solve Pattern)
        3. ReAct 루프 실행 (ReAct Pattern)
        4. Reflection 수행 (Reflection Pattern)
        5. 최종 답변 반환
        """
        # 1. Memory 업데이트
        self.memory.update_from_query(user_query, client=self.client)
        self.memory.add_conversation("user", user_query)

        if self.verbose:
            print("\n" + "="*60)
            print("🧠 [Memory] 사용자 정보 업데이트")
            print("="*60)
            print(self.memory.get_context())

        # 2. Plan 수립
        plan = self.create_plan(user_query)

        # 3. ReAct 루프
        answer = self.run_react_loop(user_query, plan)

        # 4. Reflection
        reflection = self.reflect(user_query, answer)

        # 5. 최종 결과 조합
        self.memory.add_conversation("assistant", answer)

        if self.verbose:
            print("\n" + "="*60)
            print("✨ [Final Answer] 최종 추천 결과")
            print("="*60)

        final_output = answer
        if "⚠️" in reflection:
            final_output += f"\n\n---\n{reflection}"

        return final_output
