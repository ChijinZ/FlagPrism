# C1 source navigation and execution report validation

Executed in server Docker `chijin-study-pro6000`, CPU only. Report tests used
`/workspace/venv/bin/python` (Python 3.10.12); browser used the separately
installed P1 Playwright environment and Chromium 141.0.7390.37. This is root
engineering validation, not independent acceptance or the extra code reviews.

The four inputs are preserved C0 development captures: NVIDIA CLI, Enflame CLI,
Ascend reduction and runtime loop. Report regeneration used a separate directory
and verified every raw file unchanged. Source bytes/digests, valid anchors,
invalid-primary/valid-inline handling, exact binary-and-line record backlinks,
and actual HTML execution mapping navigation passed. Complete derived bundles
were below 64 MiB and report materialization below 60 seconds. This does not
measure new C1 device collection, final CLI cost or GPU performance.

CPU tests: 54 passed, one optional preexisting report test skipped. Actual browser
interaction was executed separately and passed on all four bundles. YAPF 0.43.0
preserved each tested Python AST; Ruff 0.9.1 passed. See the source digests in
`format-receipt.json`.

Full evidence, including unmodified parent bytes, derived bundles, scripts,
screenshots and retained failed browser attempts, is in the engineering workspace:
`artifacts/usability/run-001/c1-root-ui-r4-evidence.tgz`, SHA-256
`0b5f4fc09f7ebe53dcd1245a4c90ab79d802bc63aedeadaecea602253504b6f6`.
Server directory: `/workspace/usability-c1-root-ui/r4/`.

Browser attempts 1/2 failed because the isolated runtime needed its explicit
fontconfig file. The passing command set `FONTCONFIG_FILE` to the existing
P1 `browser-fonts.conf` and the extracted runtime library path. No product change
was needed for this test environment issue. Earlier unit-test collection failure
(test syntax) and missing-pytest attempt remain in r1; neither was counted as a
product pass. Final independent installed-wheel and product re-review remain
required.
