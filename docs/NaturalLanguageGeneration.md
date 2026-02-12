# 자연어 기반 실내 씬 생성 가이드

이 문서는 자연어 설명을 통해 Infinigen의 실내 씬을 생성하는 방법을 설명합니다.

## 목차

1. [개요](#개요)
2. [설치 및 설정](#설치-및-설정)
3. [기본 사용법](#기본-사용법)
4. [지원되는 파라미터](#지원되는-파라미터)
5. [사용 예제](#사용-예제)
6. [제한사항](#제한사항)
7. [고급 사용법](#고급-사용법)
8. [문제 해결](#문제-해결)

## 개요

자연어 기반 씬 생성 기능은 LLM(Large Language Model)을 사용하여 자연어 설명을 파싱하고, 이를 gin config 파일로 변환하여 실내 씬을 생성합니다.

### 작동 방식

```
자연어 입력 → LLM 파싱 → 이름 정규화 → 제약사항 검증 및 재분류 → Gin Config 생성 → 씬 생성
```

1. **자연어 파싱**: LLM이 자연어 입력에서 gin config로 제어 가능한 정보만 추출
2. **이름 정규화**: 자연어 오브젝트/방 이름을 Semantics 태그 이름으로 변환 (예: "싱크대" → "Sink", "모니터" → "Watchable")
3. **제약사항 검증 및 재분류**: 
   - 파싱된 제약사항이 유효한지 검증
   - 오브젝트가 잘못된 카테고리에 분류되면 자동으로 올바른 카테고리로 재분류 (예: Sink가 primary에 있으면 secondary로 이동)
4. **Config 생성**: 검증 및 재분류된 제약사항을 gin config 형식으로 변환
5. **씬 생성**: 생성된 config 파일을 사용하여 씬 생성 (선택사항)

## 설치 및 설정

### 필수 요구사항

- Python 3.11 이상
- Infinigen 프로젝트 설치 완료
- 로컬 LLM (Ollama) 또는 OpenAI API 키

### 로컬 LLM 설정 (기본값, 권장)

이 기능은 기본적으로 로컬 LLM(Ollama)을 사용합니다. 로컬 LLM을 사용하면 API 비용 없이 오프라인에서도 작동합니다.

#### 1. Ollama 설치

**Linux/macOS**:
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**설치 문제 해결**:
- libffi 충돌 오류가 발생하는 경우 (conda 환경):
  ```bash
  conda install -c anaconda git curl
  # 또는
  conda install libffi==3.3
  ```
- 또는 수동 설치:
  ```bash
  wget https://github.com/ollama/ollama/releases/latest/download/ollama-linux-amd64
  chmod +x ollama-linux-amd64
  sudo mv ollama-linux-amd64 /usr/local/bin/ollama
  ```

#### 2. Ollama 서버 시작

```bash
ollama serve
```

서버는 백그라운드에서 실행되며, 기본 주소는 `http://localhost:11434`입니다.

#### 3. 모델 다운로드

Gemma 3 4B 모델을 다운로드합니다:

```bash
ollama pull gemma3
```

다른 모델을 사용하려면:
```bash
ollama pull <model-name>
```

#### 4. Python 패키지 설치

```bash
pip install ollama
# 또는
pip install -e ".[nlp]"
```

#### 5. 사용법

로컬 LLM은 기본값이므로 별도 설정 없이 사용할 수 있습니다:

```bash
python -m infinigen_examples.generate_from_nl \
    --nl "침실에 침대와 옷장을 배치한 씬을 1개 생성해줘." \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/bedroom_scene
```

다른 모델을 사용하려면:
```bash
python -m infinigen_examples.generate_from_nl \
    --nl "침실에 침대를 배치해줘." \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/bedroom_llama3 \
    --ollama-model "llama3" \
    --ollama-base-url "http://localhost:11434"
```

### OpenAI API 설정 (선택사항)

OpenAI API를 사용하려면 `--use-openai` 플래그를 사용하고 환경 변수에 API 키를 설정하세요:

```bash
export OPENAI_API_KEY="your-api-key-here"
```

또는 명령줄에서 직접 지정:

```bash
python -m infinigen_examples.generate_from_nl \
    --nl "your description" \
    --use-openai \
    --api-key "your-api-key-here" \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/openai_scene
```

## 기본 사용법

### Config 파일만 생성

가장 기본적인 사용법은 자연어 설명으로부터 gin config 파일만 생성하는 것입니다:

```bash
python -m infinigen_examples.generate_from_nl \
    --nl "침실에 침대와 옷장을 배치한 씬을 1개 생성해줘." \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/bedroom_config_only
```

### Config 생성 후 바로 씬 생성

`--generate-scene` 플래그를 사용하면 config 파일 생성 후 바로 씬을 생성합니다:

```bash
python -m infinigen_examples.generate_from_nl \
    --nl "침실에 침대와 옷장을 배치한 씬을 1개 생성해줘." \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/bedroom_with_scene \
    --generate-scene
```

### Python API 사용

Python 코드에서 직접 사용할 수도 있습니다:

**로컬 LLM 사용 (기본값)**:
```python
from pathlib import Path
from infinigen_examples.nlp.generate_from_nl import generate_scene_from_nl

config_path = generate_scene_from_nl(
    natural_language="침실에 침대와 옷장을 배치한 씬을 1개 생성해줘.",
    output_folder=Path("/media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/bedroom_python"),
    scene_seed=42,
    use_local_llm=True,  # 기본값
    ollama_model="gemma3",  # 기본값
    ollama_base_url="http://localhost:11434",  # 기본값
)

print(f"Generated config: {config_path}")
```

**OpenAI API 사용**:
```python
from pathlib import Path
from infinigen_examples.nlp.generate_from_nl import generate_scene_from_nl

config_path = generate_scene_from_nl(
    natural_language="침실에 침대와 옷장을 배치한 씬을 1개 생성해줘.",
    output_folder=Path("/media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/bedroom_openai"),
    scene_seed=42,
    use_openai=True,
    api_key="your-api-key",  # 또는 None (환경 변수 사용)
)

print(f"Generated config: {config_path}")
```

## 지원되는 파라미터

이 기능은 **gin config로 제어 가능한 파라미터만** 추출합니다. 다음은 지원되는 주요 파라미터들입니다.

### 방 타입 제한 (`restrict_parent_rooms`)

지원되는 방 타입:
- **한국어**: 주방, 침실, 거실, 응접실, 옷장, 복도, 화장실, 욕실, 차고, 발코니, 식당, 다이닝룸, 유틸리티, 계단실, 사무실, 회의실, 휴게실
- **영어**: Kitchen, Bedroom, LivingRoom, Closet, Hallway, Bathroom, Garage, Balcony, DiningRoom, Utility, StaircaseRoom, Office, MeetingRoom, BreakRoom

### 오브젝트 타입 제한

오브젝트는 배치 방식에 따라 세 가지 카테고리로 분류됩니다:

#### 부모 오브젝트 (`restrict_parent_objs`)
다른 오브젝트 위에 배치될 수 있는 오브젝트 (다른 오브젝트의 부모가 될 수 있음)
- **예시**: KitchenCounter, Storage, Table, Desk, SideTable, Bed
- **설명**: 이 오브젝트들은 다른 오브젝트를 위에 올려놓을 수 있는 표면을 제공합니다

#### 주요 오브젝트 (`restrict_child_primary`)
방에 직접 배치되는 주요 오브젝트 (바닥에, 벽에 배치)
- **한국어**: 침대, 의자, 소파, 테이블, 책상, 옷장, 선반, 조리대, 가전제품, 가구, 벽장식, 천장등
- **영어**: Bed, Seating, LoungeSeating, Table, Desk, Storage, KitchenCounter, KitchenAppliance, Furniture, WallDecoration, CeilingLight, Chair, SideTable
- **설명**: 이 오브젝트들은 방의 바닥이나 벽에 직접 배치됩니다

#### 보조 오브젝트 (`restrict_child_secondary`)
다른 오브젝트 위에 배치되는 보조 오브젝트
- **한국어**: 싱크대, 그릇, 식기, 조리기구, 수저, 램프, 조명, 모니터, 티비
- **영어**: Sink, Dishware, Cookware, Utensils, OfficeShelfItem, KitchenCounterItem, TableDisplayItem, BathroomItem, FoodPantryItem, Lighting, Watchable
- **설명**: 이 오브젝트들은 다른 오브젝트(예: KitchenCounter, Table, Storage) 위에 배치됩니다
- **중요**: Sink는 KitchenCounter 위에 배치되므로 `restrict_child_secondary`에 있어야 합니다

**자동 재분류 기능**: LLM이 오브젝트를 잘못된 카테고리에 분류하더라도, 시스템이 자동으로 올바른 카테고리로 재분류합니다. 예를 들어, Sink가 `restrict_child_primary`에 있으면 자동으로 `restrict_child_secondary`로 이동됩니다.

### 수량 제약

- `solve_max_rooms`: 최대 방 개수
- `solve_max_parent_obj`: 최대 부모 오브젝트 개수

### 위치 관계 제어 (간접 제어)

**중요**: 위치 관계는 직접 제어할 수 없지만, stage 활성화/비활성화를 통해 간접적으로 제어할 수 있습니다.

- **바닥에만 배치**: `solve_large_enabled=True`, `solve_medium_enabled=False`, `solve_small_enabled=False` (large stage만 활성화)
- **벽/천장에만 배치**: `solve_large_enabled=False`, `solve_medium_enabled=True`, `solve_small_enabled=False` (medium stage만 활성화)
- **오브젝트 위에만 배치**: `solve_large_enabled=False`, `solve_medium_enabled=False`, `solve_small_enabled=True` (small stage만 활성화)

### 기타 설정

- `solve_steps`: 해결 단계 수 (large, medium, small)
- `terrain_enabled`: 지형 생성 여부
- `topview`: 탑뷰 모드
- `animate_cameras_enabled`: 카메라 애니메이션 활성화
- `floating_objs_enabled`: 플로팅 오브젝트 활성화
- `restrict_single_supported_roomtype`: 단일 방 타입으로 제한

## 사용 예제

**참고**: `--output_folder`는 절대 경로 또는 현재 작업 디렉토리 기준 상대 경로를 사용할 수 있습니다. 외부 SSD에 저장하려면 절대 경로를 사용하세요.

### 예제 1: 기본 사용 (한국어)

```bash
# 외부 SSD에 저장 (권장)
python -m infinigen_examples.generate_from_nl \
    --nl "침실에 침대와 옷장을 배치한 씬을 1개 생성해줘." \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/bedroom_scene \
    --generate-scene

# 또는 현재 디렉토리에 저장
python -m infinigen_examples.generate_from_nl \
    --nl "침실에 침대와 옷장을 배치한 씬을 1개 생성해줘." \
    --output_folder ./output \
    --generate-scene
```

**생성되는 config**:
```gin
include 'infinigen_examples/configs_indoor/base_indoors.gin'

# restrict_solving parameters
restrict_solving.restrict_parent_rooms = ['Bedroom']
restrict_solving.restrict_child_primary = ['Bed', 'Storage']
restrict_solving.solve_max_rooms = 1
```

### 예제 2: 위치 제약 (바닥에만 배치)

```bash
python -m infinigen_examples.generate_from_nl \
    --nl "주방에 조리대와 싱크대만 배치하고, 바닥에만 배치해줘." \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/kitchen_floor_only \
    --generate-scene
```

**생성되는 config**:
```gin
include 'infinigen_examples/configs_indoor/base_indoors.gin'

# restrict_solving parameters
restrict_solving.restrict_parent_rooms = ['Kitchen']
restrict_solving.restrict_parent_objs = ['KitchenCounter']
restrict_solving.restrict_child_primary = ['KitchenCounter']
restrict_solving.restrict_child_secondary = ['Sink']

# compose_indoors parameters
compose_indoors.solve_large_enabled = True
compose_indoors.solve_medium_enabled = False
compose_indoors.solve_small_enabled = False
```

**설명**: 
- KitchenCounter는 방에 직접 배치되므로 `restrict_child_primary`에 포함됩니다
- Sink는 KitchenCounter 위에 배치되므로 `restrict_child_secondary`에 포함됩니다
- KitchenCounter는 다른 오브젝트(Sink)의 부모가 될 수 있으므로 `restrict_parent_objs`에도 포함됩니다
- "바닥에만 배치"는 large stage만 활성화하여 바닥에 직접 배치되는 오브젝트만 생성합니다

### 예제 3: 영어 입력

```bash
python -m infinigen_examples.generate_from_nl \
    --nl "Create a scene with a dining table and chairs in the dining room. Maximum 2 rooms." \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/dining_room \
    --generate-scene
```

**생성되는 config**:
```gin
include 'infinigen_examples/configs_indoor/base_indoors.gin'

# restrict_solving parameters
restrict_solving.restrict_parent_rooms = ['DiningRoom']
restrict_solving.restrict_child_primary = ['Table', 'Seating']
restrict_solving.solve_max_rooms = 2
```

### 예제 4: 복합 제약사항

```bash
python -m infinigen_examples.generate_from_nl \
    --nl "거실에 소파와 테이블을 배치하고, 최대 3개의 방을 생성해줘. 오브젝트는 바닥에만 배치해줘." \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/living_room \
    --generate-scene
```

### 예제 5: Seed 지정

```bash
python -m infinigen_examples.generate_from_nl \
    --nl "침실에 침대를 배치해줘." \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/bedroom_seed42 \
    --seed 42 \
    --generate-scene
```

### 예제 6: Base Config 변경

```bash
python -m infinigen_examples.generate_from_nl \
    --nl "주방 씬을 생성해줘." \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/kitchen_custom \
    --base-config "infinigen_examples/configs_indoor/custom_base.gin" \
    --generate-scene
```

### 예제 7: Task 지정

```bash
python -m infinigen_examples.generate_from_nl \
    --nl "침실 씬을 생성해줘." \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/bedroom_full \
    --task coarse populate render \
    --generate-scene
```

## 제한사항

### 1. Gin Config로 제어 가능한 항목만 추출

이 기능은 **gin config로 제어 가능한 파라미터만** 추출합니다. 다음은 제어할 수 없는 항목들입니다:

- **위치 관계 직접 제어 불가능**: `on_floor`, `on_wall`, `on_ceiling` 관계는 `default_greedy_stages()`에서 하드코딩되어 있습니다.
  - **대안**: `solve_*_enabled` 플래그로 stage를 비활성화하여 간접 제어 가능
- **세부적인 오브젝트 배치**: 특정 오브젝트의 정확한 위치나 방향은 제어 불가능
- **재질이나 색상**: 오브젝트의 재질이나 색상은 제어 불가능

### 2. LLM 파싱 오류 및 자동 재분류

LLM이 자연어를 잘못 파싱할 수 있습니다. 이 경우:

- 파싱 실패 시 기본 config가 사용됩니다
- 경고 메시지가 출력되며, 수정된 값으로 계속 진행됩니다
- **자동 재분류**: 오브젝트가 잘못된 카테고리에 분류되면 자동으로 올바른 카테고리로 재분류됩니다
  - 예: Sink가 `restrict_child_primary`에 있으면 자동으로 `restrict_child_secondary`로 이동
  - 예: Monitor, TV가 잘못 분류되면 `Watchable`로 자동 변환
- 생성된 config 파일을 확인하여 올바르게 파싱되었는지 검증하세요

### 3. 지원되지 않는 방/오브젝트 타입

지원되지 않는 방 타입이나 오브젝트 타입을 지정하면:

- 경고 메시지가 출력됩니다
- 해당 항목은 무시되거나 가장 유사한 타입으로 매핑될 수 있습니다
- **참고**: 일부 오브젝트는 Semantics 태그로 직접 존재하지 않지만 매핑됩니다
  - `TVStand`: `Storage` 태그로 처리됨 (TVStandFactory가 Storage 태그 사용)
  - `Monitor`, `TV`: `Watchable` 태그로 매핑됨

## 고급 사용법

### Config 파일 수동 수정

생성된 config 파일을 직접 수정하여 추가 제약사항을 적용할 수 있습니다:

```bash
# 1. Config 파일 생성
python -m infinigen_examples.generate_from_nl \
    --nl "침실에 침대를 배치해줘." \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/bedroom_manual

# 2. 생성된 config 파일 확인
# 파일 위치: infinigen_examples/configs_indoor/nl_generated_*.gin

# 3. Config 파일 수동 수정

# 4. 수정된 config로 씬 생성
python -m infinigen_examples.generate_indoors \
    --configs base_indoors nl_generated_xxxxx \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/bedroom_manual
```

### Gin Override 사용

생성된 config에 추가 override를 적용할 수 있습니다:

```bash
python -m infinigen_examples.generate_from_nl \
    --nl "침실에 침대를 배치해줘." \
    --output_folder /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/bedroom_override \
    --overrides "compose_indoors.terrain_enabled=True" \
    --generate-scene
```

### Python API에서 세부 제어

```python
from pathlib import Path
from infinigen_examples.nlp.generate_from_nl import generate_scene_from_nl

# 자연어 파싱 및 config 생성
config_path = generate_scene_from_nl(
    natural_language="침실에 침대를 배치해줘.",
    output_folder=Path("/media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/bedroom_api"),
    scene_seed=42,
    use_openai=True,
    base_config="infinigen_examples/configs_indoor/base_indoors.gin",
)

# 생성된 config 파일 읽기 및 수정
with open(config_path, 'r') as f:
    config_content = f.read()

# 추가 수정 후 저장
# ...

# 수동으로 씬 생성
# python -m infinigen_examples.generate_indoors --configs base_indoors nl_generated_xxxxx
```

## 문제 해결

### 1. Ollama 연결 오류

**문제**: `Ollama server is not reachable at http://localhost:11434`

**해결책**:
- Ollama 서버가 실행 중인지 확인: `ollama serve`
- 서버 주소가 올바른지 확인: `--ollama-base-url` 옵션 사용
- 방화벽 설정 확인

**문제**: `Model 'gemma3' not found`

**해결책**:
- 모델 다운로드: `ollama pull gemma3`
- 사용 가능한 모델 확인: `ollama list`
- 다른 모델 사용: `--ollama-model <model-name>`

**문제**: `ollama package is required`

**해결책**:
```bash
pip install ollama
# 또는
pip install -e ".[nlp]"
```

### 2. OpenAI API 오류

**문제**: `OpenAI API error: ...`

**해결책**:
- API 키가 올바르게 설정되었는지 확인
- API 키에 충분한 크레딧이 있는지 확인
- 네트워크 연결 확인
- `--use-openai` 플래그가 설정되었는지 확인

### 3. 파싱 결과가 예상과 다름

**문제**: LLM이 자연어를 잘못 파싱함

**해결책**:
- 더 명확하고 구체적인 자연어 설명 사용
- 생성된 config 파일을 확인하고 수동으로 수정
- 여러 번 시도하여 다른 결과 얻기 (seed 변경)

### 3. 지원되지 않는 방/오브젝트 타입

**문제**: 경고 메시지가 출력됨

**해결책**:
- 지원되는 방/오브젝트 타입 목록 확인 (위의 [지원되는 파라미터](#지원되는-파라미터) 섹션 참조)
- 유사한 타입으로 변경

### 5. Config 파일을 찾을 수 없음

**문제**: `Config file not found: ...`

**해결책**:
- Config 파일은 `infinigen_examples/configs_indoor/` 디렉토리에 생성됩니다
- 파일명은 `nl_generated_{hash}.gin` 형식입니다
- 생성 로그에서 정확한 파일 경로 확인

### 6. 씬 생성 실패

**문제**: Config는 생성되었지만 씬 생성이 실패함

**해결책**:
- 생성된 config 파일의 문법 확인
- Base config가 올바른지 확인
- `generate_indoors.py`를 직접 실행하여 더 자세한 오류 메시지 확인

## 추가 리소스

- [기본 실내 씬 생성 가이드](./generate_indoors.md) (있는 경우)
- [Gin Config 문서](./gin_config.md) (있는 경우)
- [태그 시스템 문서](./tags.md) (있는 경우)

## 참고사항

### 로컬 LLM vs OpenAI API

- **로컬 LLM (기본값)**: 
  - 오프라인 작동 가능
  - API 비용 없음
  - 데이터 프라이버시 보장
  - 첫 실행 시 모델 로딩으로 인한 지연 가능
  - GPU 가속 권장 (CUDA 지원 시)
  
- **OpenAI API**:
  - 빠른 응답 속도
  - 더 일관된 JSON 출력
  - 인터넷 연결 필요
  - API 비용 발생

### 기타

- 생성된 config 파일은 `infinigen_examples/configs_indoor/` 디렉토리에 저장됩니다
- 파일명은 입력 자연어의 해시값을 기반으로 생성되므로, 동일한 입력은 동일한 파일명을 생성합니다
- Config 파일은 수동으로 수정하거나 삭제할 수 있습니다
- LLM 파싱은 비결정적일 수 있으므로, 동일한 입력이라도 약간 다른 결과가 나올 수 있습니다
- 로컬 LLM의 경우, Gemma 모델은 JSON 출력이 OpenAI만큼 일관되지 않을 수 있으므로 `post_process.py`의 오류 수정 로직이 자동으로 적용됩니다
