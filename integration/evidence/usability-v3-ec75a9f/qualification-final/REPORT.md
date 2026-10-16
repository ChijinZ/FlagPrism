Independent Ascend v3 qualification remains incomplete. The frozen final runtime is source `ec75a9f0592c76f22d64eff443034ab89442b477`, wheel SHA256 `821b929b9582080b2f2a6996be25ccd7c41a6443dfcd9da39129e10a554d7206`. No product code was changed by this qualification.

| Cohort | Ordinary | Default profiles | Generated-input closure supplement |
| --- | --- | --- | --- |
| Original 24 mathematical cases, unchanged source/input/seed/tolerance | 22 eligible, 2 State assertion failures | 44 attempted: 42 complete gate passes, 2 State assertion CLI failures | 42/42 complete bundles passed; the 2 failed CLI runs have no complete export |
| Known shadow diagnostic | 2 passes | 2 derived complete gate passes | 2/2 passed |
| Independently frozen post-fix mathematical kernel, two shapes and two configurations | 4 passes | 8 passes, 16 actual runtime calls/captures | 8/8 passed |

The original historical cohort remains separately recorded as 24 ordinary cases, 23 eligible, 46 profiles with 45 passes and one unexplained State failure. Its records, failures and denominator were not changed. Legacy v1/v2 counter records are not new v3 exact qualification evidence. Previous NVIDIA/GCU validation was not repeated by this affected-backend qualification.

The current two eligible profile failures observed scalar State values `[2,2]` and `[2]`, where the unchanged assertion expected one after the first call. Each had one host call; earlier floating-point mathematics, input and canary assertions completed. Neither run produced a complete export, and neither was retried. These observations establish a failed contract assertion, but do not yet establish profiler-induced repeated execution or an invalid scalar oracle. The exact historical failed case is ordinary-eligible on this runtime: its cold profile failed and its warm profile passed. Neither of the two current ordinary failures is that historical exact case. One ordinary failure corresponds to the historical ineligible case; the other was previously eligible.

The known shadow diagnostic has disjoint per-element integer State ownership evidence. Both profiles produced all 1,024 State elements equal to one and all four required AIV State marker cells equal to one. The original strict-empty rejection and later missing-budget `KeyError` records remain unchanged. A separate CPU derivation on the same exported bytes supplied the original budget rule and independently checked schema equivalence before projection; it retained per-call input, seed, mathematical tolerance, witness and host-once requirements. This is known-case evidence and does not erase any scalar failure.

The new mathematical kernel was frozen independently after the fix and was not shared with engineering. All four ordinary cases and eight cold/warm profiles passed the full v3 gate and the generated-input supplement. Actual captures include AIC and AIV modules, guarded integer State, same-binary runtime count variation, source/compiler/raw/identity checks, host-once and the original budgets. Its source and manifest hashes appear in `FINAL_SAFE_VERDICT.json`; private mathematics and IR are excluded from this directory.

| Observed maximum | Original matrix | Known shadow | New kernel |
| --- | ---: | ---: | ---: |
| Ordinary compile + launch + synchronization | 25.5653 s | 22.9393 s | 23.5812 s |
| Profile host process wall time | 46.7095 s | 44.4799 s | 46.1381 s |
| Complete finalize/export | 1.2253 s | 1.0487 s | 1.4060 s |
| Bundle size | 22,082,692 B | 20,827,510 B | 22,633,343 B |
| Raw size / physical cells | 2,176 B / 272 | 448 B / 56 | 832 B / 104 |

All compile limits were 120 s and export limits 60 s. These are functional qualification observations, not device performance measurements.

The additional generated-input closure module checks the actual generated main LLVM bytes against original adapted-input and executed-input receipts, including SHA, length, path, argv and retained bytes. Two actual public positive bundles passed. Six receipt mutations passed the older proof (the retained red result) and were rejected by the supplement. The supplement then passed all 52 available matrix/shadow/new bundles without changing their original bytes. It read generated artifacts only, not SDK libraries.

One separately authorized ordinary compile-only observation executed zero user kernels and imported no profiler API. Its 4,800-byte binary was byte-identical to the original ordinary binary, SHA256 `a0a09d04080b04a129eb4da13122232172692f7734eba38666093ebab0fb295e`. The retained ordinary LLVM and successful profiled LLVM have the same checked State caller structure: BLOCK-only scalar GM offset, length-one non-atomic copy, and no caller SUBBLOCK election. The helper body is only declared in these inputs. This comparison does not prove helper-internal election, multiple actual writers, a scheduler property, or the cause of either failed profile. Failed-run loaded binary bytes were not exported; successful counterpart cache identity is distinguished from that missing evidence.

NPU4 was released after all owned controllers terminated; the safe release receipt reports zero owned live processes. Engineering now owns any further device diagnosis. This qualification adds no further random retry, library scan or scheduler investigation.

Every file indexed by `SAFE_FILE_INDEX.json` is permitted for root's review. The private archive named only by hash and length in the verdict must not be read or published by root. Detailed safe receipts, immutable historical lineage, the finite compile-only comparison, terminal records and closure indices are included here. The overall verdict remains false pending explanation and resolution of the two current State failures; passing shadow/new-kernel controls cannot close them.
