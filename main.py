"""
맛집 추천 AI Agent - 메인 실행 파일
"""

import os
import sys
from dotenv import load_dotenv
from agent import RestaurantAgent

load_dotenv()

BANNER = """
╔══════════════════════════════════════════════════════╗
║        🍽️  맛집 추천 AI Agent  🍽️                   ║
║                                                      ║
║  Agentic Design Patterns:                            ║
║    ✅ ReAct (Thought → Action → Observation)         ║
║    ✅ Plan-and-Solve                                 ║
║    ✅ Reflection                                     ║
║    ✅ Memory                                         ║
╚══════════════════════════════════════════════════════╝
"""

DEMO_QUERY = "전주 객사 근처에서 친구랑 저녁 먹기 좋은 맛집을 찾아줘. 너무 비싸지 않고, 리뷰가 좋은 곳 위주로 3곳 추천해줘."


def check_api_key():
    missing = [k for k in ("OPENAI_API_KEY", "NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET") if not os.environ.get(k)]
    if missing:
        for k in missing:
            print(f"❌ 오류: {k} 환경변수가 설정되지 않았습니다.")
        print("   .env 파일에 키를 추가해주세요. (.env.example 참고)")
        sys.exit(1)


def run_demo():
    """과제 테스트 시나리오 실행"""
    print(BANNER)
    print("🚀 데모 시나리오 실행")
    print(f"📝 쿼리: {DEMO_QUERY}\n")

    agent = RestaurantAgent(verbose=True)
    result = agent.run(DEMO_QUERY)
    print(f"\n{result}\n")


def run_interactive():
    """대화형 인터페이스"""
    print(BANNER)
    print("💬 대화형 모드 시작 (종료: 'exit' 또는 'quit')\n")

    agent = RestaurantAgent(verbose=True)

    while True:
        try:
            user_input = input("\n👤 사용자: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\n👋 Agent를 종료합니다.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "종료", "끝"):
            print("👋 Agent를 종료합니다.")
            break

        result = agent.run(user_input)
        print(f"\n🤖 Agent:\n{result}")


def main():
    check_api_key()

    # 인자 파싱
    mode = "interactive"
    if len(sys.argv) > 1:
        if sys.argv[1] == "demo":
            mode = "demo"
        elif sys.argv[1] == "query" and len(sys.argv) > 2:
            # 단일 쿼리 실행
            query = " ".join(sys.argv[2:])
            print(BANNER)
            agent = RestaurantAgent(verbose=True)
            result = agent.run(query)
            print(f"\n{result}\n")
            return

    if mode == "demo":
        run_demo()
    else:
        run_interactive()


if __name__ == "__main__":
    main()
