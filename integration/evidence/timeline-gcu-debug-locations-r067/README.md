# GCU debug-location compatibility prototype (R067)

This is an unintegrated CPU prototype, not a released profiling feature.
It adds debug scopes/locations to retained SDK IR without changing non-location
operations or vendor properties, then requires validation by the real SDK.
The v3 printer incompatibility remains as a failed diagnostic. The v4 bridge
and v5 normal SDK compilation succeeded in the existing server Docker.

The generated ELF has real DWARF line tables. Its executable .text is identical
to the original hardware-executed image, but unwind data and some allocated
addresses differ. This does not establish complete equivalence to the original
capture. LLVM11 objdump shows useful line annotations but also a debug-info
warning; the independent readelf line-table dump exits zero with empty stderr.

Finite contexts locate inline clock and SIPINFO operations by retained IR line.
No full reader-to-raw binding, all-path source boundaries, or ordinary pipeline
preservation is certified here. No product code, SDK, device workload, SQL,
Perfetto UI, or paper was changed. SDK linked IR/native dumps stay on the server;
only our prototype, bounded receipts and small decoded contexts are tracked.
