# NLP Parsing Module Tests

이 디렉토리는 자연어 파싱 모듈의 엣지 케이스를 테스트하기 위한 테스트 스위트를 포함합니다.

## 파일 구조

- `test_cases.py`: 20개의 엣지 케이스 테스트 시나리오 정의
- `test_nlp_evaluation.py`: 평가 함수 구현 (정확도, 재분류, 일관성 검사)
- `run_nlp_tests.py`: 테스트 실행 스크립트 및 리포트 생성
- `test_results/`: 테스트 결과 저장 디렉토리 (자동 생성)

## 사용법

### 모든 테스트 실행

```bash
cd /home/ailab/infinigen
python -m tests.nlp.run_nlp_tests
```

### 특정 테스트만 실행

```bash
python -m tests.nlp.run_nlp_tests --test-ids edge_001 edge_002
```

### 특정 카테고리만 실행

```bash
python -m tests.nlp.run_nlp_tests --categories object_classification_error stage_flag_mismatch
```

### OpenAI API 사용

```bash
export OPENAI_API_KEY="your-api-key"
python -m tests.nlp.run_nlp_tests --use-openai
```

### 로컬 LLM 사용 (기본값)

```bash
python -m tests.nlp.run_nlp_tests --use-local-llm --ollama-model gemma3
```

## 테스트 케이스 카테고리

1. **object_classification_error**: 오브젝트 분류 오류
2. **stage_flag_mismatch**: Stage 플래그 불일치
3. **number_parsing**: 숫자 파싱 엣지 케이스
4. **complex_constraints**: 복합 제약사항
5. **ambiguous_expression**: 모호한 표현
6. **unsupported_type**: 지원되지 않는 타입
7. **location_constraint**: 위치 제약 엣지 케이스
8. **minimal_input**: 최소/빈 입력
9. **long_input**: 매우 긴 입력
10. **special_characters**: 특수 문자/형식
11. **mixed_language**: 언어 혼용
12. **synonyms**: 동의어/유사어
13. **negation**: 부정 표현
14. **multiple_objects**: 복수 오브젝트 타입
15. **conflicting_info**: 중복/상충 정보
16. **very_specific**: 매우 구체적인 제약
17. **very_ambiguous**: 매우 모호한 제약
18. **stage_combination**: Stage 조합 엣지 케이스
19. **quantity_constraint**: 수량 제약 엣지 케이스
20. **real_world**: 실제 사용 시나리오

## 리포트

테스트 실행 후 다음 파일들이 생성됩니다:

- `test_results/results_YYYYMMDD_HHMMSS.json`: 상세한 JSON 결과
- `test_results/report_YYYYMMDD_HHMMSS.md`: 마크다운 리포트

리포트에는 다음 정보가 포함됩니다:
- 전체 통계 (성공률, 재분류율, Stage 일관성)
- 카테고리별 성공률
- 필드별 정확도
- 실패한 테스트 상세 정보
