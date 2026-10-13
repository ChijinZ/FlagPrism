#!/usr/bin/env bash
set -u
cd /workspace/study-goal-enflame-matrix-sanity-r011
export TORCH_0_enflame_AUTOLOAD=0 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
trap 'study_rc=$?; printf "%s\n" "$study_rc" > w2.exit' EXIT
printf '%s\n' "$$" > w2.pid
python3 run_case.py --backend enflame --operator gemm --shape 512x512x512 --tile-m 32 --tile-n 32 --k-tile 32 --num-warps 2 --stages 4 --phase native --profile-launches 30 --input-dir /workspace/chijin-study-canonical-inputs-r007 --output fixedgrid-w2 > fixedgrid-w2.log 2>&1 || exit "$?"
mkdir -p tcu/fixedgrid-w2
tcu --kernel-name matmul --enable-metrics SIP/2D_EFFICIENCY,SIP/1D_EFFICIENCY,SIP/BUSY --replay-mode application --print-gcu-trace --export-csv tcu/fixedgrid-w2/invocations.csv --export-rawdata tcu/fixedgrid-w2/rawdata --log-file tcu/fixedgrid-w2/application.log python3 run_case.py --backend enflame --operator gemm --shape 512x512x512 --tile-m 32 --tile-n 32 --k-tile 32 --num-warps 2 --stages 4 --phase baseline --repeats 3 --batch 1 --unique-output --input-dir /workspace/chijin-study-canonical-inputs-r007 --output tcu/fixedgrid-w2/runs > tcu/fixedgrid-w2/tcu.log 2>&1 || exit "$?"
