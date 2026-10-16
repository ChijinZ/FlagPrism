# Source-site visit census protocol

This document describes the new census wire format and reader. Backend build,
installation, hardware and public-default acceptance for this version must be
recorded separately; the presence of this document is not proof of acceptance.

The census observes selected source control positions in the original user
launch. Each admitted logical program has independent cells for its declared
logical observer and compiler-selected sites. A count means the position was
reached. It does not establish active data lanes, completed memory transactions,
hardware utilization, elapsed time or the cost of the uninstrumented program.
In particular an all-false masked operation can still reach its control position.

The request is explicit in the public `ObservationRequest` contract:

```python
from flagtree.profiler import ObservationRequest

request = ObservationRequest(
    semantics=('counter',), programs=None, automatic=True,
    program_policy='all_grid_census',
    max_census_cells=1048576, max_census_bytes=8388608,
)
```

The byte budget includes physical padding and headers. Both budgets are checked
before the original launch. Byte limits are also checked before allocation;
NVIDIA currently validates its cell count at the prelaunch hook after bounded
scratch allocation. This ordering remains an engineering gap until the allocator
receives exact compiled launch geometry. Explicit requests may change these limits, subject to
the backend's representable index and allocation range. Export uses the same
compiler-recorded request limits; it rejects conflicting descriptor limits.
The ordinary reader keeps its safe defaults unless its caller supplies an
explicit override. Historical captures without a retained compiler request
cannot silently raise those defaults. This policy does not select the first N
programs, sample visits, rerun the application or choose a fixed fallback
program. The existing fixed-program interval request remains a different mode.

The common descriptor has schema `flagprism.source-census`, version 1,
`cell_size=8`, `byte_order="little"`, an actual three-dimensional `grid`, its
`program_count`, ordered `sites` and typed logical `actors`. Sites carry their
compiler site ID, `primary` or `context` role, and actual compiler origin.
`cells_offset`, `program_stride`, `actor_stride` and `site_stride` specify the
physical byte layout. A cell starts at:

```
cells_offset + program * program_stride
             + actor_index * actor_stride + site_index * site_stride
```

Linear program IDs use `x + grid_x * (y + grid_y * z)`. The cell contains a
little-endian u32 count followed by u32 flags: visited is bit 0, saturation is
bit 1. An unvisited cell is `(0, 0)`. Saturation preserves `UINT32_MAX` as a lower
bound and marks the capture inexact; it cannot prove an exact loop count. Other
flags, overlapping cells, truncation and mismatched raw SHA-256 are errors.
Backend transport headers and publisher padding have additional backend checks.

The full raw matrix and descriptor remain in the capture. The default detail
table presents the lowest actual program with nonzero primary-site visits. This
is a presentation choice after collection, not a collection filter. Context-only
visits cannot establish body execution. The summary reports observed programs,
primary-observed programs and saturation across the whole matrix, including
programs not expanded in the detail table. No-primary-visits is an explicit
result rather than successful body observation.

To query another program from retained, decoded raw bytes:

```python
from flagtree.profiler.source_census import CensusReader

reader = CensusReader(raw_bytes, descriptor)
cell = reader.cell(program=7, actor_index=0, site_index=1)
print(cell['site'], cell['count'], cell['exact'])
```

The example program ID is a reader query, not an instrumentation special case.
The reader validates every cell before returning counts, including unselected
programs. A count of N stays one counter record with value N. It never becomes N
synthetic intervals. Its clock, start/end ticks, duration and loop-iteration ID
are null. Raw byte offsets and digests retain the connection to the original
cell. Source and invocation association require independent producer evidence;
the descriptor's strings or SHA alone do not verify compiler provenance.


## NVIDIA partition observers

NVIDIA keeps one independent observer plane for the default logical warp zero
and each compiler-selected warp-specialized worker region. Worker actors have
`kind="logical_program_observer"` and a compiler-assigned ID, plus the actual
`compiler_partition_region` and `partition_threads`. These IDs do not name
physical warps. Source origins carry the actual emitted observer assignment.

For a worker partition containing a contiguous interval of P physical threads,
exactly one thread satisfies `physical_thread_id % P == 0`, regardless of the
interval's physical start. That thread owns the region's cells. The default
observer remains physical thread zero. Counters describe reaching each selected
source position; a worker observer does not imply that its lane issued an
asynchronous memory transaction or that all data masks were active.

The compiler passes the same per-program scratch pointer as an explicit hidden
warp-specialize capture and a worker-region block argument. Each observer uses
its own `sites * 8` byte plane. Physical per-program storage is padded to the
compiler's128-byte scratch alignment; both cell and actual-byte admission count
all observer planes. Nested captures use the enclosing region's argument rather
than an out-of-scope pointer. No atomics, cross-partition counter sharing, replay
or synthetic timestamp intervals are introduced.
