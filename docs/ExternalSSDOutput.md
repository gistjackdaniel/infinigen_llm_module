# 외부 SSD에 출력 저장하기

Infinigen의 데이터셋 생성 작업은 많은 디스크 공간을 필요로 합니다. 외부 SSD나 다른 저장소에 출력을 저장하려면 `INFINIGEN_OUTPUT_BASE` 환경 변수를 사용하세요.

## 빠른 시작

```bash
# 1. 환경 변수 설정
export INFINIGEN_OUTPUT_BASE=/media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs

# 2. 일반적인 방법으로 실행 (상대 경로도 자동으로 외부 SSD에 저장됨)
python -m infinigen.datagen.manage_jobs \
    --output_folder outputs/my_dataset \
    --num_scenes 1000 \
    --pipeline_configs local_256GB.gin monocular.gin blender_gt.gin indoor_background_configs.gin \
    --configs singleroom.gin \
    --pipeline_overrides get_cmd.driver_script='infinigen_examples.generate_indoors' manage_datagen_jobs.num_concurrent=16 \
    --overrides compose_indoors.restrict_single_supported_roomtype=True
```

**중요**: `--output_folder`에 상대 경로(예: `outputs/my_dataset`)를 지정하면 환경 변수 기준으로 해석됩니다. 절대 경로를 지정하면 그대로 사용됩니다.

## 환경 변수 설정

### 임시 설정 (현재 세션만)
```bash
export INFINIGEN_OUTPUT_BASE=/media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs
```

### 영구 설정 (모든 세션)
`~/.bashrc`에 추가:
```bash
export INFINIGEN_OUTPUT_BASE=/media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs
```
그 후 `source ~/.bashrc` 실행

## 동작 방식

- `INFINIGEN_OUTPUT_BASE` 환경 변수가 설정되어 있으면, `--output_folder`의 상대 경로를 이 기준으로 해석합니다.
- 환경 변수가 없고 현재 작업 디렉토리가 `/media/` 경로에 있으면, 자동으로 해당 경로의 `outputs` 폴더를 사용합니다.
- 그 외의 경우 기본값인 `outputs` 폴더를 사용합니다.

## 기존 데이터 이동

```bash
# 1. 데이터 이동
mv /home/ailab/infinigen/outputs/my_dataset /media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs/my_dataset

# 2. 환경 변수 설정 후 --use_existing으로 재개
export INFINIGEN_OUTPUT_BASE=/media/ailab/b310e108-a41f-4ba5-810b-28ac3c870413/juhyeong/infinigen/outputs
python -m infinigen.datagen.manage_jobs --output_folder outputs/my_dataset --use_existing ...
```

## 문제 해결

**경로가 존재하지 않음**: `mkdir -p`로 미리 생성

**권한 오류**: `chmod -R u+w`로 쓰기 권한 부여

**환경 변수 확인**: `echo $INFINIGEN_OUTPUT_BASE`
