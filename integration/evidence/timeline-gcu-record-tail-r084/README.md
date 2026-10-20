# GCU relative native record-tail value flow

The new internal `gcu_native_values.check_record_tail` follows bounded native
32-bit scalar definitions, address arithmetic and stores. It checks end low,
masked high and both identity fields relative to one record magic address.
Unknown aliasing stores, unaligned overwrites, late field/magic overwrites,
unsupported instructions and unproved intra-packet RAW/WAW are rejected.
It does not select kernels by names, shapes, site IDs or hashes.

The source-loaded module and 18 semantic fixtures ran in the existing GCU Docker
under normal Python and `-O`, each passing in 0.02s. The same helper checked all
219 displayed instructions of the retained original ELF's specified recorder
tail against original executable bytes and followed the end values into fields
6/7/8/19. Original SDK/native/device/Mathematics/TP/UI runs were not repeated.
Ruff, yapf and check-ast passed with unchanged final source hashes.

This is an internal component toward automatic boundary inspection. The actual
runner still supplies manually identified entry registers and tail extent;
MMIO reader/selection, incoming begin/site tuple, ring allocation/sequence,
source region and loop paths remain unqualified. It is not yet connected to the
automatic inspection entry or claimed normally installed. The result's broad
qualification flags remain false. Standard collection/export behavior is unchanged.

Full unchanged ELF/native inputs, earlier source versions and complete controller
receipts remain outside Git under root artifacts and on the original server.
The independent compiler review gives only the above finite scope, not whole-goal
signoff. The requested reviewer configuration is GPT-6.1-Sol/xhigh; resolved
serving configuration is not exposed.
