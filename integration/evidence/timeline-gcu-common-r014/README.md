# Installed common raw v2 and actual GCU pair reinspection

This checkpoint is an installed Python reader/adapter result, not full P01,
GCU public timeline collection, certified ns, async generation, or Perfetto.

Product freeze: `a0ef3c904e076e0f4f1743d16fa4399ea4829288`; tests-only legacy
reader driver: `7fceb5e41e33359146353edca36e37feb18527c3`. NVIDIA installation:
`chijin-study-pro6000:/workspace/chijin-timeline-r014/runs/install-v1/output/venv`.
The wheel SHA is `7deb63383bfe57de40103f17b0e3f1911bbe11b891e8bd6e23c9186914c653f0`;
608 installed members were byte-checked. Seven native libraries match the prior
actual `4f5b2bf` build; native source was unchanged and not rebuilt.

Normal and Python -O each passed 11 new order/GCU contracts, 16 legacy event
contracts, 25 machine-map contracts, and four public CPU contracts. Actual prior
GCU captures at runtime K=3/7/11 produced 42 intervals and 84 exact 8-byte raw
field references. Actual prior NVIDIA 26 captures were reread unchanged:
11456 endpoint references, 5720 pairs, 16 orphan endpoints. No new GPU execution
was performed. Pair completion order is distinct from tick order and iteration;
common v2 loss counts use canonical endpoint references, with native pair units
retained separately. No clock, source-cost, or engine qualification is inferred.

Original archive: `artifacts/timeline/run-014/preflight/gcu-common-original-evidence.tgz`,
91559 bytes, SHA `8ffba38da8ba13dce98e03d5c44dde7a6911d310756b549620f422e38d5f7a6a`.
The GCU original input archive remains
`artifacts/timeline/run-013/preflight/gcu-dynamic-original-evidence.tgz`.
Small receipts here retain installed/source/native bridges, normal/-O results,
process terminal states, and the complete archive member hash index.

Reproduce the stdlib/Git retained-byte audit from the workspace root:

```sh
python FlagPrism-method/integration/evidence/timeline-gcu-common-r014/audit-retained-bytes.py \
  --repo FlagPrism-method \
  --archive artifacts/timeline/run-014/preflight/gcu-common-original-evidence.tgz \
  --gcu-original artifacts/timeline/run-013/preflight/gcu-dynamic-original-evidence.tgz \
  --output /tmp/gcu-common-retained-byte-audit.json
```

The adapter remains an offline physical decoder of a real advanced producer.
Default first/last-program selection, launch owner/transport, safe persistence,
clock qualification, async reuse, and standard Perfetto still require completion.
