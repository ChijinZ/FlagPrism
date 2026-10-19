# Existing GCU300 native inspection tools (R065)

The installed LLVM11 disassembler provides a usable native output for the same
recorded GCU300 ELF for which LLVM18 reported decoding failures in helpers.
The actual tool is `/opt/tops/llvm11/bin/llvm-objdump`, with the same
`-d --triple=dtu --mcpu=gcu300 --demangle --line-numbers` arguments.
Its original-ELF read returned zero and emitted 3,000,060 bytes, including the
previously unavailable timer and physical-counter-identity functions. The
retained output has no reported unknown/decode/error or raw-data fallback terms.
LLVM11 symbol headings omit the angle brackets used by LLVM18; inspection
accounts for that formatting difference. This is not a whole-region proof.

The original ELF SHA-256 is
`ac6748ff87599aa31b21356701527be356ceb9908637df9b67006fa072701cba`.
A separate normal SDK CPU compilation of its retained IR reproduced the entire
original fatbin byte for byte (`bd419b80...`). No application, GCU kernel, SQL or
UI was rerun. No installed product or SDK bytes changed.

The following unsuccessful diagnostics remain failures:

- Enabling the installed debug-info path failed because the installed
  `gcu-compiler-opt` lacks `--ensure-debug-info-scope-on-llvm-func`.
- `CUTE_DUMP_ASM` does not export intermediate files in the device-only branch.
- The documented `gpu-module-to-binary` assembly format did emit native text,
  but LLVM18 and LLVM11 `llvm-mc` both reject its `.dtu_device_func` metadata.
  No assembled substitute was used to certify the original ELF.
- The first retained-string parser rejected a valid escaped backslash before
  any assembler ran; the corrected parser preserves this original failure.

In particular, the final mixed diagnostic controller returned one because its
assembler failed, while its independent original-ELF disassembly step returned
zero. These are separate results, not an end-to-end toolchain success.

This resolves the specific lack-of-disassembly-tool condition for this existing
target/object. It does not close source/loop region G1, bind all timestamp
records to native readers, establish ordinary pipeline preservation, or extend
qualification to other targets. The earlier request for a replacement GCU
disassembler no longer needs user action on this account.

The indexed large outputs remain in the workspace/server. SDK wrapper/private
source, linked generated LLVM and full assembly are not copied into Git.
The included scripts are finite diagnostics of an existing example, not product
per-operator adapters or an alternative profiler frontend.
