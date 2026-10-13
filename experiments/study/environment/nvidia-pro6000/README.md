# Recorded PRO6000 Docker setup

These are the actual setup/build/download/smoke/tuning commands recorded for this run. Dependencies and compiled code live in the Docker bind directory `/storage/Ext_01/chijin-study-pro6000/workspace` mounted as `/workspace`, rather than the small Docker root disk. Existing user containers are reused on GCU and Ascend.

The build uses FlagTree PR1262, current FlagPrism, sm120 support, Python3.10, Torch2.8.0+cu128, FlagPrism enabled and FlagCX disabled for the single-device run. The PR's external FlagPrism include path was repaired with a source symlink. Original failure and successful environment receipts remain under workspace artifacts/study-goal-run/environment. These scripts record this run's paths and container identity; reuse the configured container when reproducing.
