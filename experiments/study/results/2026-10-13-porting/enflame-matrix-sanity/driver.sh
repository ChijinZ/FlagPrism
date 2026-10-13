#!/usr/bin/env bash
set -u
cd /workspace/study-goal-enflame-matrix-sanity-r011
export TORCH_0_enflame_AUTOLOAD=0 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
trap 'study_rc=$?; printf "%s\n" "$study_rc" > driver.exit' EXIT
printf '%s\n' "$$" > driver.pid
python3 run_case.py --backend enflame --operator gemm --shape 512x512x512 --tile-m 32 --tile-n 32 --k-tile 32 --num-warps 4 --stages 4 --phase baseline --repeats 7 --batch 5 --input-dir /workspace/chijin-study-canonical-inputs-r007 --output independent-baseline > independent-baseline.log 2>&1 || exit "$?"
for label in fixedgrid-w1 tile64-w1 tile64-w4; do
 if [ "$label" = fixedgrid-w1 ]; then tile=32; warps=1; else tile=64; if [ "$label" = tile64-w1 ]; then warps=1; else warps=4; fi; fi
 python3 run_case.py --backend enflame --operator gemm --shape 512x512x512 --tile-m "$tile" --tile-n "$tile" --k-tile "$tile" --num-warps "$warps" --stages 4 --phase native --profile-launches 30 --input-dir /workspace/chijin-study-canonical-inputs-r007 --output "$label" > "$label.log" 2>&1 || exit "$?"
 done
