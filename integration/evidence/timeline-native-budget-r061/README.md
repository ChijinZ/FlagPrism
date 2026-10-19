# R061 bounded full-CTA physical allocation correction

Implementation 730b9fef337de870939e77ce7d2dcaefadae47cd. Default session raw
physical limit stays 8 MiB, trace 16 MiB and bundle 64 MiB. This does not expose
new user-facing resource options or claim arbitrary long capture fits.

The real runtime-K GEMM first run passed ordinary K3/K7 and profile K3, but the
second profile admission correctly rejected cumulative physical budget before
allocation/math. The old per-pair target 512 records x 128 threads consumed
4,206,592 raw bytes plus 128 guard bytes: two exceeded 8 MiB. The first whole
failure and its three successful mathematical call receipts remain retained.

Policy v4 rounds the complete-CTA physical pair target down to a 2/4/8 MiB
power-of-two allowance, reserving guard bytes before deriving capacity. Actual
32/64/128/256-thread capacities are 1022/510/510/510. Sampled 4096 and explicit
capacity paths, ABI, guard enforcement and budget admission are unchanged.
The new native tool SHA remains part of compiler identity; an old compiled
v3 tool cannot be silently accepted by the v4 Python manifest check.
Retained v3 decoders still interpret each original manifest capacity.

Seven affected budget tests passed in normal/-O in the existing GCU Docker;
two-pass formatter fixed point and Python AST identity were checked. Actual
normal standalone build, matching 639-member wheel and isolated installed
runtime are in the native/install receipt. Unchanged core/runtime objects
were reused with source checks, not falsely claimed as rebuilt.

The same existing runtime-K GEMM then passed ordinary K3/K7 and profile K3/K7
(four math calls; each phase shares one binary). Each capture has 4,190,208 raw
plus 128 guard bytes; total physical 8,380,672 <= 8,388,608. Actual maximum
committed records per thread are 83/163, below capacity 510. Both have eight
observer-ns exports and two current observed-dependency exports. Actual groups
are 5/9 per selected program, consumer edges 72/104, reuse edges 26/42. Each
loaded object passed the dedicated finite four-native-family checks and
negative fixtures, with actual original files unchanged. No performance or
ordinary-schedule certificate is inferred. All workers are terminal; controller
zombies are not live work. Exact cache object index binds recorded ordinary
and profile math hashes without replaying to recover their binary inputs.
