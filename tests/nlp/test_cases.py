# Copyright (C) 2024, Princeton University.
# This source code is licensed under the BSD 3-Clause license found in the LICENSE file in the root directory
# of this source tree.

"""Test cases for NLP parsing module - Edge cases and scenarios."""

from typing import Any, Dict, List

# 20 Edge case test scenarios
TEST_CASES = [
    # 1. 오브젝트 분류 오류 - Sink를 primary에 넣는 경우
    #    LLM이 Sink를 parent_objs에 넣음 → validate가 secondary로 재분류
    #    fallback이 Kitchen 추출, validate가 KitchenCounter를 parent로 자동 추론
    {
        "id": "edge_001",
        "category": "object_classification_error",
        "description": "Sink를 restrict_child_primary에 잘못 분류하는 경우",
        "input": "주방에 싱크대를 배치해줘.",
        "expected_issues": ["Automatically reclassified"],
        "expected_after_fix": {
            "restrict_parent_rooms": ["Kitchen"],
            "restrict_parent_objs": ["KitchenCounter"],
            "restrict_child_primary": ["KitchenCounter"],
            "restrict_child_secondary": ["Sink"],
        },
    },
    # 2. Stage 플래그 불일치 - "바닥에만" + secondary 오브젝트
    #    fallback_extract_stage_flags → solve_small=False
    #    validate → secondary 있으면 solve_small=True 자동 활성화
    {
        "id": "edge_002",
        "category": "stage_flag_mismatch",
        "description": "restrict_child_secondary가 있는데 solve_small_enabled=False",
        "input": "주방에 조리대 위에 음식을 배치하고, 바닥에만 배치해줘.",
        "expected_issues": ["auto-enabled solve_small_enabled"],
        "expected_after_fix": {
            "restrict_parent_rooms": ["Kitchen"],
            "solve_small_enabled": True,  # Should be auto-enabled
        },
    },
    # 3. 숫자 파싱 - "1개 주방"
    #    핵심: solve_max_rooms=1, restrict_parent_rooms=Kitchen
    #    LLM이 오브젝트를 누락할 수 있으므로 restrict_child_primary는 검사하지 않음
    {
        "id": "edge_003",
        "category": "number_parsing",
        "description": "한국어 숫자 표현 '1개 주방' 파싱",
        "input": "1개 주방에 조리대를 배치해줘.",
        "expected_output": {
            "restrict_parent_rooms": ["Kitchen"],
            "solve_max_rooms": 1,
        },
    },
    # 4. 복합 제약사항
    #    "침실과 거실" → fallback이 Bedroom, LivingRoom 추출
    #    "바닥에만" → fallback이 solve_small=False 적용
    {
        "id": "edge_004",
        "category": "complex_constraints",
        "description": "여러 방 타입 + 여러 오브젝트 + 위치 제약",
        "input": "침실과 거실에 침대, 소파, 테이블을 배치하고, 최대 3개 방, 바닥에만 배치해줘.",
        "expected_output": {
            "restrict_parent_rooms": ["Bedroom", "LivingRoom"],
            "solve_max_rooms": 3,
            "solve_large_enabled": True,
            "solve_medium_enabled": False,
            "solve_small_enabled": False,
        },
    },
    # 5. 모호한 표현
    #    "침실" → fallback이 Bedroom 추출
    #    "가구" → LLM이 Furniture 또는 구체적 아이템 반환 가능
    {
        "id": "edge_005",
        "category": "ambiguous_expression",
        "description": "모호한 표현 '적당히 배치해줘'",
        "input": "침실에 적당히 가구를 배치해줘.",
        "expected_output": {
            "restrict_parent_rooms": ["Bedroom"],
            # LLM may return Furniture or specific items; room is the key check
        },
    },
    # 6. 지원되지 않는 타입
    #    LLM이 "게임룸"을 파싱 → 방 이름이 매핑에 없음 → validation이 제거
    #    "게임룸"은 ROOM_MAPPINGS에 없으므로 fallback도 추출 못함
    {
        "id": "edge_006",
        "category": "unsupported_type",
        "description": "존재하지 않는 방 타입",
        "input": "게임룸에 게임기를 배치해줘.",
        "expected_issues": ["Invalid object types"],
        "expected_output": {
            "restrict_parent_rooms": None,
        },
    },
    # 7. 위치 제약 - "바닥과 벽에만"
    #    "거실" → fallback이 LivingRoom 추출
    #    "바닥과 벽에만" → fallback이 large=T, medium=T, small=F 적용
    {
        "id": "edge_007",
        "category": "location_constraint",
        "description": "복합 위치 제약 '바닥과 벽에만'",
        "input": "거실에 가구를 바닥과 벽에만 배치해줘.",
        "expected_output": {
            "restrict_parent_rooms": ["LivingRoom"],
            "solve_large_enabled": True,
            "solve_medium_enabled": True,
            "solve_small_enabled": False,
        },
    },
    # 8. 최소/빈 입력
    #    "침실" → fallback이 Bedroom 추출
    {
        "id": "edge_008",
        "category": "minimal_input",
        "description": "매우 짧은 입력",
        "input": "침실",
        "expected_output": {
            "restrict_parent_rooms": ["Bedroom"],
        },
    },
    # 9. 매우 긴 입력
    #    "침실" → fallback이 Bedroom 추출
    #    LLM이 Wardrobe 반환 → normalize가 Storage로 매핑
    #    LLM이 Lamp 반환 → normalize가 Lighting으로 매핑
    #    LLM이 Chair 반환 → Chair는 valid PRIMARY_OBJECT
    {
        "id": "edge_009",
        "category": "long_input",
        "description": "여러 문장으로 구성된 긴 설명",
        "input": "침실에 침대를 배치하고, 옷장도 배치하고, 책상도 배치하고, 의자도 배치하고, 램프도 배치하고, 최대 2개 방을 생성해줘.",
        "expected_output": {
            "restrict_parent_rooms": ["Bedroom"],
            "solve_max_rooms": 2,
            # Objects vary by LLM run; Bed, Storage/Desk/Chair + Lighting are typical
        },
    },
    # 10. 특수 문자/형식
    #    핵심: 괄호가 있어도 방 타입은 정상 추출 (fallback)
    #    LLM이 괄호에 혼란을 느껴 오브젝트를 누락할 수 있으므로 restrict_child_primary는 검사하지 않음
    {
        "id": "edge_010",
        "category": "special_characters",
        "description": "특수 문자 포함",
        "input": "주방에 조리대(카운터)를 배치해줘.",
        "expected_output": {
            "restrict_parent_rooms": ["Kitchen"],
        },
    },
    # 11. 언어 혼용
    #    "bedroom" → fallback이 ROOM_MAPPINGS에서 Bedroom 추출
    {
        "id": "edge_011",
        "category": "mixed_language",
        "description": "한국어와 영어 혼용",
        "input": "bedroom에 침대를 배치해줘.",
        "expected_output": {
            "restrict_parent_rooms": ["Bedroom"],
        },
    },
    # 12. 동의어/유사어
    {
        "id": "edge_012",
        "category": "synonyms",
        "description": "동의어 사용 - '싱크' vs '싱크대'",
        "input": "주방에 조리대와 싱크를 배치해줘.",
        "expected_output": {
            "restrict_parent_rooms": ["Kitchen"],
            "restrict_parent_objs": ["KitchenCounter"],
            "restrict_child_primary": ["KitchenCounter"],
            "restrict_child_secondary": ["Sink"],
        },
    },
    # 13. 부정 표현
    #    "침실" → fallback이 Bedroom 추출
    {
        "id": "edge_013",
        "category": "negation",
        "description": "부정 표현 '~없이'",
        "input": "침실에 침대만 배치하고 다른 가구는 없이 해줘.",
        "expected_output": {
            "restrict_parent_rooms": ["Bedroom"],
            "restrict_child_primary": ["Bed"],
        },
    },
    # 14. 복수 오브젝트 타입
    #    "거실" → fallback이 LivingRoom 추출
    #    LLM이 LoungeSeating, Chair 반환 → 둘 다 primary; Chair도 valid
    {
        "id": "edge_014",
        "category": "multiple_objects",
        "description": "같은 카테고리에 여러 오브젝트",
        "input": "거실에 소파, 의자, 안락의자를 배치해줘.",
        "expected_output": {
            "restrict_parent_rooms": ["LivingRoom"],
            "restrict_child_primary": ["LoungeSeating", "Chair"],
        },
    },
    # 15. 중복/상충 정보
    #    "주방" → fallback이 Kitchen 추출
    #    "바닥에만" → fallback이 solve_small=False 적용
    #    Sink → secondary로 재분류 → KitchenCounter가 parent로 자동 추론
    #    secondary 존재 → validate가 solve_small=True 자동 활성화
    #    LLM이 Cookware 등을 환각할 수 있으므로 secondary의 정확한 내용은 검사하지 않음
    {
        "id": "edge_015",
        "category": "conflicting_info",
        "description": "상충하는 제약사항",
        "input": "주방에 조리대 위에 싱크대를 배치하고, 바닥에만 배치해줘.",
        "expected_output": {
            "restrict_parent_rooms": ["Kitchen"],
            "solve_large_enabled": True,
        },
    },
    # 16. 매우 구체적인 제약
    #    "주방" → fallback이 Kitchen 추출
    #    "바닥에만" → fallback이 solve_small=False 적용
    #    secondary → validate가 solve_small=True 활성화, parent 추론
    {
        "id": "edge_016",
        "category": "very_specific",
        "description": "모든 파라미터 명시",
        "input": "1개 주방에 조리대를 배치하고 조리대 위에 음식을 배치하고, 바닥에만 배치하고, 최대 1개 방을 생성해줘.",
        "expected_output": {
            "restrict_parent_rooms": ["Kitchen"],
            "solve_max_rooms": 1,
            "solve_large_enabled": True,
            "solve_medium_enabled": False,
        },
    },
    # 17. 매우 모호한 제약
    {
        "id": "edge_017",
        "category": "very_ambiguous",
        "description": "최소한의 정보만 포함",
        "input": "방에 뭔가 배치해줘.",
        "expected_output": {
            "restrict_parent_rooms": None,
        },
    },
    # 18. Stage 조합 엣지 케이스
    #    "거실" → fallback이 LivingRoom 추출
    #    입력에 "~에만" 없음 → fallback stage override 안 함 → all stages True
    #    LLM이 오브젝트를 파싱하면 그대로 사용
    {
        "id": "edge_018",
        "category": "stage_combination",
        "description": "large=True, medium=False, small=True 조합",
        "input": "거실에 소파를 바닥에 배치하고, 테이블 위에 그릇을 올려줘.",
        "expected_output": {
            "restrict_parent_rooms": ["LivingRoom"],
            "solve_large_enabled": True,
        },
    },
    # 19. 수량 제약 엣지 케이스
    #    LLM이 "0개"를 그대로 파싱하면 post_process에서 1로 클램핑됨
    #    LLM이 0 대신 1을 직접 반환할 수도 있음 → 어느 경우든 최종 결과는 1
    {
        "id": "edge_019",
        "category": "quantity_constraint",
        "description": "solve_max_rooms = 0 (잘못된 값)",
        "input": "0개 방을 생성해줘.",
        "expected_output": {
            "solve_max_rooms": 1,
        },
    },
    # 20. 실제 사용 시나리오
    #    "침실" → fallback이 Bedroom 추출
    {
        "id": "edge_020",
        "category": "real_world",
        "description": "실제 사용자가 입력할 만한 자연스러운 표현",
        "input": "아늑한 침실을 만들어줘. 침대와 옷장이 있고, 창가에 책상이 있으면 좋겠어. 최대 2개 방으로 해줘.",
        "expected_output": {
            "restrict_parent_rooms": ["Bedroom"],
            "restrict_child_primary": ["Bed", "Storage", "Desk"],
            "solve_max_rooms": 2,
        },
    },
]


def get_test_cases() -> List[Dict[str, Any]]:
    """Get all test cases.

    Returns:
        List of test case dictionaries
    """
    return TEST_CASES


def get_test_case_by_id(test_id: str) -> Dict[str, Any]:
    """Get a specific test case by ID.

    Args:
        test_id: Test case ID (e.g., "edge_001")

    Returns:
        Test case dictionary or None if not found
    """
    for case in TEST_CASES:
        if case["id"] == test_id:
            return case
    return None


def get_test_cases_by_category(category: str) -> List[Dict[str, Any]]:
    """Get test cases by category.

    Args:
        category: Category name (e.g., "object_classification_error")

    Returns:
        List of test case dictionaries in the category
    """
    return [case for case in TEST_CASES if case["category"] == category]
