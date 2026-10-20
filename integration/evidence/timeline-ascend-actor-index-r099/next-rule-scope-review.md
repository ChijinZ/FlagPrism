# Ascend下一条自动source/loop规则：最小范围建议

**建议推进LLVM15只读结构规则，并与现有final reader/raw绑定组合。** 这正好补R091最低路线的自动tuple/source/loop连接；LLVM索引本身不单独授native边界，也不需要完整SSA/ISA或逐fragment机器码证明器。

本席只读既有合同相关段落、`ascend-source-shapes-result-v1.json`、当前producer的begin/end writer及Asc actor/counter/native-control/offline入口；未读peer，未执行产品、测试、SDK、模型、设备或数学。请求GPT-6.1-Sol/xhigh，resolved未知。形态材料SHA **9c44a278958564adea60181b23ec02825edfebad2d9c1b8f6418df007e9fbdd3**；含q01/q03的AIV与q05的AIC/AIV四份实际adapted LLVM、manifest及finished driver job，足够开始CPU数据路径，无需新增取证矩阵。本报告不复制private源码。随后获知R099索引器已实现；本次未审其新源码，不据消息中的结果给代码通过票。

## 最少实现三步

1. **绑定实际actor输入再索引。** 复用 `compiler_actors` 的原/adapted SHA、manifest/compile ID与actor/slot检查，再对上driver实际executed input和compiled object；final image沿 `_bound_binary` 绑定loaded snapshot。用LLVM15 IRReader/Verifier、typed SSA/PHI/successors和LoopInfo，entry取actor binding指定函数，不能取首个definition。记录必要宽度、overflow flags、GEP、volatile、InlineAsm、callee/DI；未知类型/操作保opaque，不靠删指令或改IR通过解析。
2. **核这个producer的有限协议及body/loop。** Asc是8×i64 record：fresh begin tick/zero PHI→实际body→end tick→guarded descriptor/attempt/start/end/program/actor/physical/commit，不能套GCU的32×i32布局。沿必要cone核完整tuple、slot/capacity和selected路径，失败分支不能丢弃。source用原carrier、manifest fragment与typed SDK原语连接，排除logger算术；保原membership，不要求所有原指令都计入source-exclusive区间。有限循环复用0/+1、header/latch、reset/绕过检查；literal与runtime trip分别报告，raw occurrence不填成iteration_id。
3. **接同一默认/offline分析服务。** 可在 `timeline_ascend_machine` 的实际binary检查旁生成独立结构supplement，由offline重算同规则。绑定输入与分析规则SHA，保原producer身份、raw/metadata及旧boundary_status；不读缓存checked字段充证明。原SDK/native、clock与已闭数学不因新增只读服务重跑。

## native边界的准确上限

| 现有依据 | 可以组合出的事实 | 仍不能自动肯定 |
| --- | --- | --- |
| counter_map的actual ELF/DWARF/SYS_CNT word | 同actor/function/site的真实final readers | 原body成员实际位置或完整native路径 |
| native_control_map的exact flag word/参数/marker | 已支持set/wait的实际原语身份及点位置 | 任意compute region、全部路径或完成时刻 |
| actual adapted LLVM + 精确SDK callee/resource | typed source body、tuple及循环关系，解释真实observer bracket和重复 | 新ELF内compute issue-member仍在reader之间 |

因此下一版可先诚实输出 **typed tuple/body/loop checked + final reader bound + actual occurrences**。SDK callee名字或正duration不能单独把native issue前缀升为已证；fullmembership/native_region/source-exclusive/busy仍false。

若要追加某条family的“verified issue-member前缀”，最小native补项是：**同实际ELF/actor内，相关原语opcode/member与这对readers的有限位置关系**。已有exact flag原语/保留opcode材料可先复用；R063的VMULS/VADDS前缀只用于同73c2d8…对象，不能直接继承到新binary。无相应材料的条目保native unknown即可；本建议不要求逐fragment新跑SDK MODEL、解释完整ISA或重做独立数学。

## 新规则最少negative

- 错adapted输入、compile/job或AIC/AIV互换；旧opcode/counter证据不能绑定新binary。
- stale/错site或actor tuple、缺必需word、shared end错误forwarding、一个selected分支失败、双begin同site；必须拒绝而非只收成功路径。
- 只有logger算术/空body不能取得原compute来源；错误clock asm/约束及注释伪callee不能冒充原语。
- loop跳过end/reset回initial、literal3冒runtime、flagged-overflow bound，以及预算中断后冒称唯一，沿已有有限规则拒绝。

这些只是新声称事实的定向CPU反例，不增加whole验收门。最短下一步就是现四actor输入的typed索引、必要tuple/body/loop规则和旧raw重算；native缺项精确留unknown，完整goal另评。
