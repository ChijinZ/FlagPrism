#!/usr/bin/env bash
set -u
cd /workspace/study-goal-enflame-matrix-sanity-r011
export TORCH_0_enflame_AUTOLOAD=0 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
trap 'study_rc=$?; printf "%s\n" "$study_rc" > tcu.exit' EXIT
printf '%s\n' "$$" > tcu.pid
for label in original fixedgrid-w1 tile64-w4 tile64-w1; do
 if [ "$label" = original ]; then tile=32; warps=4; elif [ "$label" = fixedgrid-w1 ]; then tile=32; warps=1; elif [ "$label" = tile64-w4 ]; then tile=64; warps=4; else tile=64; warps=1; fi
 mkdir -p tcu/$label
 tcu --kernel-name matmul --enable-metrics SIP/2D_EFFICIENCY,SIP/1D_EFFICIENCY,SIP/BUSY --replay-mode application --print-gcu-trace --export-csv tcu/$label/invocations.csv --export-rawdata tcu/$label/rawdata --log-file tcu/$label/application.log python3 run_case.py --backend enflame --operator gemm --shape 512x512x512 --tile-m "$tile" --tile-n "$tile" --k-tile "$tile" --num-warps "$warps" --stages 4 --phase baseline --repeats 3 --batch 1 --unique-output --input-dir /workspace/chijin-study-canonical-inputs-r007 --output tcu/$label/runs > tcu/$label/tcu.log 2>&1 || exit "$?"
 done
