#!/bin/bash
# =============================================================================
# NL Batch Scene Generation Script
# 20개의 다양한 실내 씬을 LLM 모듈로 config 생성 후 Blender로 씬을 생성합니다.
#
# 사용법:
#   bash scripts/nl_batch_generate.sh [--config-only] [--start N] [--end N]
#
# 옵션:
#   --config-only  : config 파일만 생성 (씬 생성 건너뜀)
#   --start N      : N번째 씬부터 시작 (기본: 1)
#   --end N        : N번째 씬까지 생성 (기본: 20)
# =============================================================================

set -euo pipefail

# ─── 설정 ────────────────────────────────────────────────────────────────────
OUTPUT_BASE="/media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs"
BATCH_DIR="${OUTPUT_BASE}/nl_batch"
LOG_DIR="${BATCH_DIR}/logs"
INFINIGEN_ROOT="/home/ailab/infinigen"

# bpy 호환성을 위한 libstdc++ 설정
if [[ -n "${CONDA_PREFIX:-}" ]]; then
    export LD_PRELOAD="${CONDA_PREFIX}/lib/libstdc++.so.6"
fi

CONFIG_ONLY=false
START_IDX=1
END_IDX=20

# ─── 인자 파싱 ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --config-only)
            CONFIG_ONLY=true
            shift
            ;;
        --start)
            START_IDX="$2"
            shift 2
            ;;
        --end)
            END_IDX="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ─── 20개 씬 설명 정의 ──────────────────────────────────────────────────────
# 형식: "seed|scene_name|자연어 설명"
SCENES=(
    # 침실 (4개)
    "1|scene_01_bedroom_basic|침실에 침대와 옷장을 배치한 씬을 1개 생성해줘."
    "2|scene_02_bedroom_study|침실에 침대와 책상, 의자를 배치한 씬을 1개 생성해줘."
    "3|scene_03_bedroom_cozy|침실에 침대와 사이드테이블, 램프를 배치한 씬을 1개 생성해줘."
    "4|scene_04_bedroom_full|침실에 침대, 옷장, 천장등을 배치한 씬을 1개 생성해줘."

    # 주방 (4개)
    "5|scene_05_kitchen_full|주방에 조리대, 싱크대, 가전제품을 배치한 씬을 1개 생성해줘."
    "6|scene_06_kitchen_dishes|주방에 조리대와 식기를 배치한 씬을 1개 생성해줘."
    "7|scene_07_kitchen_cooking|주방에 조리대, 싱크대, 그릇을 배치한 씬을 1개 생성해줘."
    "8|scene_08_kitchen_appliance|주방에 가전제품과 조리대를 배치한 씬을 1개 생성해줘."

    # 거실 (4개)
    "9|scene_09_living_tv|거실에 소파와 테이블, 티비를 배치한 씬을 1개 생성해줘."
    "10|scene_10_living_light|거실에 소파와 조명을 배치한 씬을 1개 생성해줘."
    "11|scene_11_living_ceiling|거실에 소파, 테이블, 천장등을 배치한 씬을 1개 생성해줘."
    "12|scene_12_living_decor|거실에 소파, 테이블, 벽장식을 배치한 씬을 1개 생성해줘."

    # 사무실 (3개)
    "13|scene_13_office_monitor|사무실에 책상, 의자, 모니터를 배치한 씬을 1개 생성해줘."
    "14|scene_14_office_shelf|사무실에 책상, 선반, 모니터를 배치한 씬을 1개 생성해줘."
    "15|scene_15_office_basic|사무실에 책상, 의자, 선반을 배치한 씬을 1개 생성해줘."

    # 식당 (3개)
    "16|scene_16_dining_basic|식당에 테이블과 의자를 배치한 씬을 1개 생성해줘."
    "17|scene_17_dining_light|식당에 테이블, 의자, 조명을 배치한 씬을 1개 생성해줘."
    "18|scene_18_dining_ceiling|식당에 테이블, 의자, 천장등을 배치한 씬을 1개 생성해줘."

    # 화장실 (2개)
    "19|scene_19_bathroom_basic|화장실에 싱크대를 배치한 씬을 1개 생성해줘."
    "20|scene_20_bathroom_shelf|화장실에 싱크대와 선반을 배치한 씬을 1개 생성해줘."
)

# ─── 디렉토리 생성 ────────────────────────────────────────────────────────────
mkdir -p "${BATCH_DIR}"
mkdir -p "${LOG_DIR}"

# ─── 결과 추적 ────────────────────────────────────────────────────────────────
SUCCEEDED=()
FAILED=()
SKIPPED=()

# ─── 메인 루프 ────────────────────────────────────────────────────────────────
TOTAL=${#SCENES[@]}
echo "============================================================"
echo " NL Batch Scene Generation"
echo " Total scenes: ${TOTAL}, Range: ${START_IDX} ~ ${END_IDX}"
echo " Output: ${BATCH_DIR}"
echo " Config only: ${CONFIG_ONLY}"
echo "============================================================"
echo ""

cd "${INFINIGEN_ROOT}"

for entry in "${SCENES[@]}"; do
    IFS='|' read -r SEED SCENE_NAME NL_DESC <<< "${entry}"

    # 범위 필터링
    if [[ ${SEED} -lt ${START_IDX} || ${SEED} -gt ${END_IDX} ]]; then
        continue
    fi

    SCENE_DIR="${BATCH_DIR}/${SCENE_NAME}"
    LOG_FILE="${LOG_DIR}/${SCENE_NAME}.log"

    echo "────────────────────────────────────────────────────────────"
    echo "[${SEED}/${TOTAL}] ${SCENE_NAME}"
    echo "  NL: ${NL_DESC}"
    echo "  Output: ${SCENE_DIR}"
    echo "  Log: ${LOG_FILE}"

    # 이미 생성된 씬은 건너뛰기 (coarse 폴더가 있으면)
    if [[ -d "${SCENE_DIR}" && -d "${SCENE_DIR}/coarse" ]]; then
        echo "  >> SKIP: 이미 생성된 씬입니다."
        SKIPPED+=("${SCENE_NAME}")
        continue
    fi

    # 생성 명령어 구성
    CMD_ARGS=(
        python -m infinigen_examples.generate_from_nl
        --nl "${NL_DESC}"
        --output_folder "${SCENE_DIR}"
        --seed "${SEED}"
        --task coarse
    )

    if [[ "${CONFIG_ONLY}" == "false" ]]; then
        CMD_ARGS+=(--generate-scene)
    fi

    echo "  >> 실행 중..."
    START_TIME=$(date +%s)

    if "${CMD_ARGS[@]}" > "${LOG_FILE}" 2>&1; then
        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        echo "  >> SUCCESS (${ELAPSED}s)"
        SUCCEEDED+=("${SCENE_NAME}")
    else
        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        echo "  >> FAILED (${ELAPSED}s) - 로그를 확인하세요: ${LOG_FILE}"
        FAILED+=("${SCENE_NAME}")
    fi

    echo ""
done

# ─── 결과 요약 ────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo " 배치 생성 결과 요약"
echo "============================================================"
echo " 성공: ${#SUCCEEDED[@]}개"
for s in "${SUCCEEDED[@]+"${SUCCEEDED[@]}"}"; do
    echo "   - ${s}"
done
echo " 실패: ${#FAILED[@]}개"
for f in "${FAILED[@]+"${FAILED[@]}"}"; do
    echo "   - ${f}"
done
echo " 건너뜀: ${#SKIPPED[@]}개"
for k in "${SKIPPED[@]+"${SKIPPED[@]}"}"; do
    echo "   - ${k}"
done
echo "============================================================"

# 결과를 JSON 파일로 저장
RESULT_FILE="${LOG_DIR}/batch_result_$(date +%Y%m%d_%H%M%S).json"
cat > "${RESULT_FILE}" << ENDJSON
{
    "timestamp": "$(date -Iseconds)",
    "config_only": ${CONFIG_ONLY},
    "range": [${START_IDX}, ${END_IDX}],
    "succeeded": [$(printf '"%s",' "${SUCCEEDED[@]+"${SUCCEEDED[@]}"}" | sed 's/,$//')]  ,
    "failed": [$(printf '"%s",' "${FAILED[@]+"${FAILED[@]}"}" | sed 's/,$//')]  ,
    "skipped": [$(printf '"%s",' "${SKIPPED[@]+"${SKIPPED[@]}"}" | sed 's/,$//')]
}
ENDJSON
echo "결과 저장: ${RESULT_FILE}"

# 실패가 있으면 exit code 1
if [[ ${#FAILED[@]} -gt 0 ]]; then
    exit 1
fi
