# Compiler-referenced source files and actor plan declarations

CPU-only validation in server Docker `chijin-study-pro6000`, Python3.10.12,
`/workspace/venv/bin/python`, source tree `/workspace/usability-c1-root-ui/r6/source`.
This is an engineering source-overlay check, not an independent wheel acceptance.

- Report/source tests: 56 passed, one preexisting optional test skipped.
- Launch wrapper/registration tests: 13 passed, including preservation of CRLF
  bytes, imported helper snapshots, one snapshot per actual binary registration,
  and separate real launch identities. No device kernel was executed by these tests.
- Snapshot tests delete the original helper before export/viewing, verify exact
  bytes and declared Latin-1 decoding, reject corrupted payload digests, and retain
  missing-file reasons. Bundle tests verify exported helper references and manifest.
- Plans retain real compiler actor declarations separately from runtime slots.
  Four C0 development bundles were regenerated in separate directories; all raw
  files stayed byte-identical and source anchors remained valid. Their timing is
  derived-report materialization, not fresh C1 device capture or full finalize cost.
- YAPF0.43.0 preserved all tested ASTs; Ruff0.9.1 passed. Exact tested file digests
  are in `format-receipt.json`.

Full small evidence archive is retained in the engineering workspace at
`artifacts/usability/run-001/c1-root-ui-r6-evidence.tgz`, SHA-256
`82e14a643b64a6316fcda954aa352630b1029a3d5e8afaee4bd394547a16af9a`.
Actual browser navigation was separately validated in the preceding source
navigation evidence. A preliminary launch-overlay harness failed one old test
because its parent module attribute still referenced C0; synchronizing that
attribute with the loaded source module fixed the harness. The product was not
patched to bypass that test. Original attempt logs remain under r5 on the server.
