"""
맛집 검색 도구 - Naver Search API 기반
Tool Use Pattern: Agent가 직접 호출하는 도구들
"""

import os
import re
import requests
from typing import Optional

NAVER_LOCAL_URL = "https://openapi.naver.com/v1/search/local.json"

FOOD_TYPE_QUERY_MAP = {
    "한식": "한식",
    "일식": "일식",
    "중식": "중식",
    "양식": "양식",
    "카페": "카페",
    "카페/디저트": "카페 디저트",
    "디저트": "디저트",
    "포차": "포차",
    "포차/안주": "포차",
    "분식": "분식",
    "고기": "고기구이",
    "해산물": "해산물",
    "피자": "피자",
    "치킨": "치킨",
}


# ─────────────────────────────────────────────
# 내부 헬퍼
# ─────────────────────────────────────────────

def _headers() -> dict:
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise EnvironmentError("NAVER_CLIENT_ID 또는 NAVER_CLIENT_SECRET이 .env에 설정되지 않았습니다.")
    return {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def _local_search(query: str, display: int = 5, sort: str = "comment") -> list:
    params = {"query": query, "display": display, "sort": sort}
    resp = requests.get(NAVER_LOCAL_URL, headers=_headers(), params=params, timeout=10)
    resp.raise_for_status()
    return resp.json().get("items", [])


def _format(place: dict) -> dict:
    category = place.get("category", "")
    parts = [p.strip() for p in category.split(">")]
    food_type = parts[1] if len(parts) >= 2 else parts[0] if parts else "기타"

    return {
        "name": _strip_html(place.get("title", "")),
        "food_type": food_type,
        "category": category,
        "address": place.get("roadAddress") or place.get("address", ""),
        "phone": place.get("telephone", "전화번호 없음") or "전화번호 없음",
        "distance_label": "거리 정보 없음",
        "naver_url": place.get("link", ""),
    }


def _wrap_error(error_type: str, message: str, suggestion: str = "") -> dict:
    result = {"status": "error", "error_type": error_type, "message": message, "results": []}
    if suggestion:
        result["suggestion"] = suggestion
    return result


# ─────────────────────────────────────────────
# 도구 구현
# ─────────────────────────────────────────────

def search_restaurants(location: str, food_type: Optional[str] = None) -> dict:
    """
    지역과 음식 종류로 맛집 키워드 검색 (Naver Search API)
    리뷰 수 기준으로 정렬하여 반환
    """
    try:
        food_kw = FOOD_TYPE_QUERY_MAP.get(food_type, food_type) if food_type else "맛집"
        query = f"{location} {food_kw}"

        docs = _local_search(query, display=5, sort="comment")

        if not docs:
            return _wrap_error(
                "no_results",
                f"'{location}'에서 '{food_type or '맛집'}' 검색 결과가 없습니다.",
                "검색어를 구체적으로 바꾸거나 지역 이름을 다르게 입력해보세요."
            )

        return {
            "status": "success",
            "total": len(docs),
            "location": location,
            "food_type": food_type,
            "results": [_format(d) for d in docs]
        }

    except requests.exceptions.ConnectionError:
        return _wrap_error("network_error", "네트워크 연결에 실패했습니다. 인터넷 연결을 확인해주세요.")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return _wrap_error("auth_error", "Naver API 키가 유효하지 않습니다. .env의 NAVER_CLIENT_ID/SECRET을 확인해주세요.")
        if e.response.status_code == 403:
            return _wrap_error("auth_error", "Naver API 접근이 거부되었습니다. 검색 API가 활성화되어 있는지 확인해주세요.")
        return _wrap_error("api_error", f"Naver API 오류 ({e.response.status_code}): {e.response.text}")
    except Exception as e:
        if "NAVER_CLIENT" in str(e):
            return _wrap_error("config_error", str(e))
        return _wrap_error("unknown_error", f"알 수 없는 오류: {str(e)}")


def search_nearby_restaurants(landmark: str, food_type: Optional[str] = None,
                               radius_m: int = 1000) -> dict:
    """
    랜드마크 근처 맛집 검색 (Naver Search API)
    랜드마크명 + 음식 종류 키워드로 검색, 리뷰 수 기준 정렬
    """
    try:
        food_kw = FOOD_TYPE_QUERY_MAP.get(food_type, food_type) if food_type else "맛집"
        query = f"{landmark} {food_kw}"

        docs = _local_search(query, display=5, sort="comment")

        if not docs:
            return _wrap_error(
                "no_results",
                f"'{landmark}' 근처에서 맛집을 찾을 수 없습니다.",
                "검색어를 바꾸거나 지역명을 더 구체적으로 입력해보세요."
            )

        return {
            "status": "success",
            "total": len(docs),
            "landmark": landmark,
            "radius_m": radius_m,
            "results": [_format(d) for d in docs]
        }

    except requests.exceptions.ConnectionError:
        return _wrap_error("network_error", "네트워크 연결에 실패했습니다.")
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            return _wrap_error("auth_error", "Naver API 키가 유효하지 않습니다.")
        if e.response.status_code == 403:
            return _wrap_error("auth_error", "Naver API 접근이 거부되었습니다.")
        return _wrap_error("api_error", f"Naver API 오류 ({e.response.status_code})")
    except Exception as e:
        if "NAVER_CLIENT" in str(e):
            return _wrap_error("config_error", str(e))
        return _wrap_error("unknown_error", f"알 수 없는 오류: {str(e)}")


# ─────────────────────────────────────────────
# OpenAI Tool Definitions (Tool Use Pattern)
# ─────────────────────────────────────────────

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_restaurants",
            "description": (
                "네이버 검색 API를 사용해 지역과 음식 종류로 실제 맛집을 검색합니다. "
                "리뷰 수 기준으로 정렬하여 반환합니다. "
                "가게명, 카테고리, 주소, 전화번호, 네이버 URL을 반환합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "검색할 지역 (예: '전주 객사', '서울 홍대', '부산 서면')"
                    },
                    "food_type": {
                        "type": "string",
                        "description": "음식 종류 (예: '한식', '일식', '양식', '카페', '포차'). 생략 시 전체 맛집 검색."
                    }
                },
                "required": ["location"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_nearby_restaurants",
            "description": (
                "특정 랜드마크(장소) 근처의 맛집을 검색합니다. "
                "랜드마크명과 음식 종류 키워드를 조합하여 검색하며, 리뷰 수 기준으로 정렬합니다. "
                "네이버 검색 API를 사용합니다."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "landmark": {
                        "type": "string",
                        "description": "기준 랜드마크 (예: '전주 객사', '홍대역', '해운대 해수욕장')"
                    },
                    "food_type": {
                        "type": "string",
                        "description": "음식 종류 (예: '한식', '카페'). 생략 시 전체 음식점 검색."
                    },
                    "radius_m": {
                        "type": "integer",
                        "description": "검색 반경 참고값 (미터 단위, 기본값 1000)"
                    }
                },
                "required": ["landmark"]
            }
        }
    }
]

TOOL_MAP = {
    "search_restaurants": search_restaurants,
    "search_nearby_restaurants": search_nearby_restaurants,
}
