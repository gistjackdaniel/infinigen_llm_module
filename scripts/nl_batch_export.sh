#!/bin/bash
# =============================================================================
# NL Batch Scene Export Script
# 생성된 씬들을 Isaac Sim용 USDC 형식으로 일괄 export합니다.
#
# 사전 조건:
#   - nl_batch_generate.sh로 씬이 생성되어 있어야 합니다.
#
# 사용법:
#   bash scripts/nl_batch_export.sh [--resolution N] [--start N] [--end N]
#
# 옵션:
#   --resolution N : 텍스처 해상도 (기본: 1024)
#   --start N      : N번째 씬부터 시작 (기본: 1)
#   --end N        : N번째 씬까지 export (기본: 20)
# =============================================================================

set -euo pipefail

# ─── 설정 ────────────────────────────────────────────────────────────────────
OUTPUT_BASE="/media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs"
BATCH_DIR="${OUTPUT_BASE}/nl_batch"
EXPORT_DIR="${OUTPUT_BASE}/nl_batch_export"
LOG_DIR="${EXPORT_DIR}/logs"
INFINIGEN_ROOT="/home/ailab/infinigen"

# bpy 호환성을 위한 libstdc++ 설정
if [[ -n "${CONDA_PREFIX:-}" ]]; then
    export LD_PRELOAD="${CONDA_PREFIX}/lib/libstdc++.so.6"
fi

RESOLUTION=1024
START_IDX=1
END_IDX=20

# ─── 인자 파싱 ───────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
    case $1 in
        --resolution)
            RESOLUTION="$2"
            shift 2
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

# ─── 디렉토리 생성 ────────────────────────────────────────────────────────────
mkdir -p "${EXPORT_DIR}"
mkdir -p "${LOG_DIR}"

# ─── 결과 추적 ────────────────────────────────────────────────────────────────
SUCCEEDED=()
FAILED=()
SKIPPED=()

# ─── 씬 디렉토리 탐색 ────────────────────────────────────────────────────────
cd "${INFINIGEN_ROOT}"

# nl_batch 디렉토리에서 scene_* 폴더들을 찾음
SCENE_DIRS=()
for d in "${BATCH_DIR}"/scene_*; do
    if [[ -d "$d" ]]; then
        SCENE_DIRS+=("$d")
    fi
done

# 정렬
IFS=$'\n' SCENE_DIRS=($(sort <<<"${SCENE_DIRS[*]}")); unset IFS

TOTAL=${#SCENE_DIRS[@]}

echo "============================================================"
echo " NL Batch Scene Export (USDC for Isaac Sim)"
echo " Total scenes found: ${TOTAL}"
echo " Texture resolution: ${RESOLUTION}"
echo " Input: ${BATCH_DIR}"
echo " Export output: ${EXPORT_DIR}"
echo "============================================================"
echo ""

if [[ ${TOTAL} -eq 0 ]]; then
    echo "ERROR: 생성된 씬이 없습니다. 먼저 nl_batch_generate.sh를 실행하세요."
    exit 1
fi

IDX=0
for SCENE_PATH in "${SCENE_DIRS[@]}"; do
    IDX=$((IDX + 1))

    # 범위 필터링
    if [[ ${IDX} -lt ${START_IDX} || ${IDX} -gt ${END_IDX} ]]; then
        continue
    fi

    SCENE_NAME=$(basename "${SCENE_PATH}")
    EXPORT_SCENE_DIR="${EXPORT_DIR}/${SCENE_NAME}"
    LOG_FILE="${LOG_DIR}/${SCENE_NAME}_export.log"

    echo "────────────────────────────────────────────────────────────"
    echo "[${IDX}/${TOTAL}] Exporting: ${SCENE_NAME}"
    echo "  Input: ${SCENE_PATH}"
    echo "  Export to: ${EXPORT_SCENE_DIR}"

    # coarse 폴더가 없으면 건너뛰기
    if [[ ! -d "${SCENE_PATH}/coarse" ]]; then
        echo "  >> SKIP: coarse 폴더가 없습니다 (씬이 생성되지 않음)."
        SKIPPED+=("${SCENE_NAME}")
        continue
    fi

    # 이미 export된 씬은 건너뛰기
    if [[ -d "${EXPORT_SCENE_DIR}" ]] && find "${EXPORT_SCENE_DIR}" -name "*.usdc" -print -quit 2>/dev/null | grep -q .; then
        echo "  >> SKIP: 이미 export된 씬입니다."
        SKIPPED+=("${SCENE_NAME}")
        continue
    fi

    echo "  >> Export 실행 중..."
    START_TIME=$(date +%s)

    if python -m infinigen.tools.export \
        --input_folder "${SCENE_PATH}" \
        --output_folder "${EXPORT_SCENE_DIR}" \
        -f usdc \
        -r "${RESOLUTION}" \
        --omniverse \
        > "${LOG_FILE}" 2>&1; then

        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        echo "  >> SUCCESS (${ELAPSED}s)"
        SUCCEEDED+=("${SCENE_NAME}")
    else
        END_TIME=$(date +%s)
        ELAPSED=$((END_TIME - START_TIME))
        echo "  >> FAILED (${ELAPSED}s) - 로그 확인: ${LOG_FILE}"
        FAILED+=("${SCENE_NAME}")
    fi

    echo ""
done

# ─── 결과 요약 ────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
echo " Export 결과 요약"
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

# USDC 파일 목록 출력
echo ""
echo "생성된 USDC 파일 목록:"
find "${EXPORT_DIR}" -name "*.usdc" -type f 2>/dev/null | sort || echo "  (없음)"

echo ""
echo "Isaac Sim에서 사용하려면:"
echo "  conda activate isaac-sim"
echo "  source setup_conda_env.sh"
echo "  python infinigen/tools/isaac_sim.py \\"
echo "      --scene-path <USDC_PATH> \\"
echo "      --json-path <JSON_PATH>"

# 결과를 JSON 파일로 저장
RESULT_FILE="${LOG_DIR}/export_result_$(date +%Y%m%d_%H%M%S).json"
cat > "${RESULT_FILE}" << ENDJSON
{
    "timestamp": "$(date -Iseconds)",
    "resolution": ${RESOLUTION},
    "range": [${START_IDX}, ${END_IDX}],
    "succeeded": [$(printf '"%s",' "${SUCCEEDED[@]+"${SUCCEEDED[@]}"}" | sed 's/,$//')]  ,
    "failed": [$(printf '"%s",' "${FAILED[@]+"${FAILED[@]}"}" | sed 's/,$//')]  ,
    "skipped": [$(printf '"%s",' "${SKIPPED[@]+"${SKIPPED[@]}"}" | sed 's/,$//')]
}
ENDJSON
echo ""
echo "결과 저장: ${RESULT_FILE}"

# 실패가 있으면 exit code 1
if [[ ${#FAILED[@]} -gt 0 ]]; then
    exit 1
fi
