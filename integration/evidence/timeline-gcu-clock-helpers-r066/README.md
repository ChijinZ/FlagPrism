# Finite GCU300 original-ELF clock-helper audit (R066)

The existing hardware-executed ELF and the LLVM11 native output are bound by
SHA-256. The server Docker audit resolves the two actual ELF symbols, checks
each displayed instruction's bytes against that original image, and checks the
finite SDK getter/identity shapes. Ordinary Python and `-O` both pass, and
altered upper-mask and missing-rollover-comparison fixtures are rejected.

The getter has low-word reads, a high-word read, a low-word rollover comparison
and reread path, and an upper-word `0x3fff` mask. This corroborates the existing
capture's declared **returned-value ceiling of 46 bits**. It does not independently
measure the physical counter's exact width, its wrap period, or consistency for
all executions. The identity helper reads unmasked SIPINFO and returns.

The actual declaration comes from the original SHA-bound input snapshot and
fatbin, not a newly invented or replayed configuration. The first checker used
an incorrect instruction-PC-minus-eight branch landing; its two failed results
remain. The corrected finite check uses the actual 16-byte bundle base and was
run only on retained files. No application, SDK compile, device, SQL, or UI ran.
No product or SDK implementation changed.

Inline-reader-to-raw binding, source-region, shared epoch, absolute frequency,
and hardware-busy qualifications remain explicitly false. Equal MMIO addresses
and SIPINFO reads do not establish shared epochs. Full native text/actual result
bytes remain externally indexed; SDK private source is not included.
