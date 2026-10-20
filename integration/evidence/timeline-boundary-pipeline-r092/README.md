# Original C2 BK64 finite pipeline closure (R092)

The original testing section8.7 requires each C2 scheduling variant. BK32
closure does not substitute for BK64. These independent finite audits close
the missing BK64 critical-relation comparison on existing actual ordinary,
default8 and true-sparse1 inputs; original sparse failures remain failures.
They grant no generic native source/loop, hardware busy/overlap or whole-goal
qualification. The R091 full review reports retain the real remaining product
integration/coverage gap; this directory does not turn those votes into passes.

GCU:52 existing files/25,130,122 bytes,index SHA verified; archive
`d5db887411232db23a2664b0cd6a25bc240db54c03c237661836137211262c93`.
Ascend:80 existing files/21,868,097 bytes,index SHA verified; archive
`d4a58f6e7001d9579f57eea9a199c0234b7fd6f0f4381a373692e8a2a6b503aa`.
Only the missing Ascend ordinary LLVM required one passive CPU SDK compilation:
terminal0/3.170804765s, whole kernel.o byte-identical to original npubin SHA
`7a0eb2a0f452653cb0c5a48c17f16b9b623ae2ba726a49729efd79d80b127238`.
Its archive has22 files/98,754 bytes and SHA
`6a1ee04f07b9c57081388ee5a92e85500a034d028f83313ada4ad928c9160f5b`.
The reconstructed ordinary CLI is explicitly marked reconstructed; it is not
represented as a receipt from the historical compile. SDK1f5 is unchanged.
No device/kernel/math/profile/TP/UI was rerun. Private LLVM, vendor resources,
compiled images and full captures stay in workspace/server archives.

The first GCU read-only fetch used the wrong BK64 run root; the second treated
an embedded IR string as a pathname. Both reads failed and launched no device
or compiler. V3 uses the actual controlled-density64-v1 root and the recorded
rewrite argv to locate files. Neither failure alters experiment results.
