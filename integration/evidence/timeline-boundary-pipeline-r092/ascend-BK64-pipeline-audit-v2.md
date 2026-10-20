# R092 Ascend BK64 三方关键 pipeline：有限 delta 审计 v2

结论：**现有 actual BK64 ordinary / sparse1 / default8 原件足以关闭本席 R091 G3 中 Ascend BK64 的有限关键关系缺口。** 原 GM→L1 提交、readiness、MMA 消费、L1/L0 复用、每轮原 MMA 返回 cut、末轮 C publication 与 AIV State 路径保持；未发现 logger 新增原本没有的完成等待或 compute/clock 结果到原提交/控制的串行数据边。此结论不是仅按 primitive 同数/同名。

这是 v1 提出最小缺件后的有限追加。ordinary 已取得同 SDK CPU passive-codegen 输入链，whole kernel.o 与旧 npubin 亲自比对字节完全相同；**没有新设备/数学/profile**。历史 sparse1 第二 capture 仅1 positive 的失败和未启动第三次继续保留，不要求变通过；该历史失败不否认本次已核对象的静态关键关系或 default8 成功。

本报告只关闭该 Ascend C2 变体的上述有限关系项；不授 whole-goal、source/loop 自动资格、native reader→raw、epoch、hardware overlap、engine busy 或 source-exclusive cost，也不替 GCU/NVIDIA 另一变体下结论。

## 实际范围与身份

沿用原请求 GPT-6.1-Sol / xhigh；实际 resolved 型号/effort 工具未暴露，记 unknown。未读 peer。本席只做本地文本/JSON/Git、SHA/字节比较，未执行产品、测试、SDK、编译、设备、模型、数学、TP/UI 或 SSH；只写自己的报告。

本次在 v1 后实际读取了新回收的两个 exact capture、events/raw身份、machine loaded ELF、四个 actual AIC/AIV `original-input-0.ll` / adapted LLVM / manifests / receipts，以及 ordinary passive probe 的实际 AIC/AIV LLVM、command/resource receipts、runner/terminal/result。helper 复用本席 R090 已逐实际库核的特定闭包，复读了 part、readiness、release、MAD、返回等待路径。未逐条重算所有 warm raw endpoint 或模拟 native 执行；这不是本项静态 preservation 判据的新要求。

路径缩写：

- `B = artifacts/timeline/run-092/preflight/ascend-BK64-pipeline-receipts-v1`，80 regular 文件的 index 已读，归档 SHA登记为 **d4a58f6e7001d9579f57eea9a199c0234b7fd6f0f4381a373692e8a2a6b503aa**。
- `S = B/retained/chijin-timeline-r057-ascend/runs/controlled-density-v1`。
- `D = B/retained/chijin-timeline-r057-ascend/runs/controlled-density-default64-v1`。
- `O = artifacts/timeline/run-092/preflight/ascend-ordinary-BK64-receipts-v1/runs/ordinary-BK64-codegen-v1/output`；22 文件索引，归档 SHA登记为 **6a1ee04f07b9c57081388ee5a92e85500a034d028f83313ada4ad928c9160f5b**。
- `H = artifacts/timeline/run-090/preflight/ascend-mma-helper-receipts-v1/runs/mma-helper-closure-v1/output/mma-helper.ll`。

四个实际 job 后缀（以下表中 SA/DA 分别是 AIC，SV/DV 是 AIV）：

| alias | B 下相对 job 路径 |
| --- | --- |
| SA | retained/chijin-timeline-r057-ascend/runs/controlled-density-v1/tmp/flagprism-ascend-compiler-v5oqnvn7/9853acac-68ce-4c3b-b14c-917108e7546a/jobs/d7a30fdd-7278-480b-9b88-4852f8301d5a |
| SV | 同一 compile 的 jobs/6081237f-f530-4b6b-863e-3881f4dbdd65 |
| DA | retained/chijin-timeline-r057-ascend/runs/controlled-density-default64-v1/tmp/flagprism-ascend-compiler-w7cn13k5/730ce746-5db8-4e07-8a54-d62eecbe9109/jobs/c47ed4e5-d11d-4de4-9656-9cee31672ec3 |
| DV | 同一 compile 的 jobs/538e17d9-6758-458a-a5ef-cf8dd5373923 |

### ordinary 与真实 profile 的绑定

原 C2 driver SHA **298743dc44abde27a6326f02be3b0204c1a046c855a8eb6f24fe5a27006cca50**，同数学/输入/shape/精度条件，M=N64、K192、grid(2,2)、num_warps4、num_stages1。BK64 是原已登记 tile 变体，不是临时增加的数学。旧 metadata hash 为 **21681db4dbb5059b5954421e5b97334d670b29a5718d8f0d544af54504a6e91d**。

本席实际比较：

- O/kernel.mlir == S/output/BK64-density-1/64-ordinary-1/ordinary.bcmlir，SHA **ba28b45729536dd89c4bc13e615ac0b64409b909ab5f15bb7c2f4eacf9252302**；
- O/kernel.o == 同一旧 ordinary.npubin，whole 5624B、SHA **7a0eb2a0f452653cb0c5a48c17f16b9b623ae2ba726a49729efd79d80b127238**。不是仅 .text 相同，也没有拿 mix_aic.o 单独代替原 whole npubin；
- O/objects/**a0e9d2c37577b0e387a191893a39c6adf7603af376541503951e54a885ace159.ll** 是实际 AIC codegen 输入；O/objects/**1933e02e5b94638c23ef2078abca10b20e6260ed194505472caef4ed2a7bbc67.ll** 是 AIV 输入，亲自核 SHA；
- actual AIC receipt `codegen/6120eaabba674849aa498eca6bf27f2d/receipt.json` 绑定上述 AIC 和 resource **94c9885a52c9e4cfdfbc239ad104f0a4d14cd330cff9c51d141eb08e88f9ef4f**；真实 bisheng SHA **2b5d17a037767ad41123868e14bedb91741b0682cafd1a2aa05a1da5d8b8bade**、-O2/cube target。AIV 相应 receipt 绑定原库 **c816c724c8d0455ff1a85cd08b1f6097131f67809dfc0fbe31209d66139d04a6**，libdevice **9142883f2a38a17980b83c5d1e777744d823ddd4af370674015364dfc7eee11f**；
- probe SDK仍 **1f5cc5054402e901add18af133b3495b861775d68e2113bb8ba94667eef6cf9e**。命令明确是从冻结 metadata 重建 ordinary options 的新 CPU 诊断，不冒称找回了旧 CLI 收据。控制器 terminal0，**3.170804765s**；内 result 的2.9704s是不同计时范围，不混为一项。

两个真实 profile：

| 项 | sparse1 | default8 |
| --- | --- | --- |
| binary ID | 31f2a9ce155693913e894535db6eeb06db56c326da08279ebb608a46228da20c | 2b76cd0cfcc0de6d13a28596095764dec41f7956f37eac117a5bc8470a514c74 |
| invocation | b6c9871feb4f4c1fb5f084a704e049d4 | 57c17c5b907847fe9bd0801916e1d5c7 |
| capture JSON SHA | d0c2e45f6c60724ebde5b1cb728a92d36aa28637de1099aa80425782ce4e38c2 | dfd2633da62b709fcb5935df58dbda3b4de2e35c11f35f66846eaf17cde140ca |
| whole loaded ELF / snapshot decoded SHA | b81cc9b3f33de8730b899395ea54f2491dcfed5a5bb0af0c9f8256afc15a5d72 | 63c989a8ae456048d580a046c36b5f1a91d022f3a820e67c1df2b56b4ae13ad5 |
| adapted AIC SHA | 64df64e78e9ac21852edea1583cb4371accb95db3d0e2bd3f4284fd9557928fc | bb24d757abec68e379c99701e3b30a584251c1ccde900ba60f25e888a3f6fb40 |
| adapted AIV SHA | 65fea3e8995bce439a80cce34c4d2595ae95a787152e64472d55bb1982000a49 | 0da49020468104d5e9779c5180c19f89b7088b4032d5fbbe1440fb7046b14219 |

本席核 loaded ELF SHA、snapshot base64 解码 SHA、handoff.producer_association.final_binary_sha256 三者一致；association明确 same enclosing SDK process group / exact final output bytes。四 job receipt finished/exit0，executed adapted输入 SHA 匹配实际文件；两个 AIC executed resource 同 **94c988…**，故 H 的特定 MMA 语义确实适用。未另要求回收本地未包含的四个 output.bin，因为本项已由实际 job收据、同进程 final whole association 与实际 loaded bytes 建立所需链；未假称亲自散列了未包含的文件。

## 三方实际关系表

ordinary 行号指 O/objects/a0e9…ll，后两列指 SA/DA 的 adapted-0.ll。此表按实际实参/定义追踪，不只比较名称。

| 关键关系 | ordinary | sparse1 / default8 |
| --- | --- | --- |
| 首轮 L1 可写 | 40/41 SET(3,4,1/2) | 91/231；276/416，均在原循环前 |
| 三轮 K推进 | 44–51 phi i=0..2，i*64；118/119递增回边 | SA330–338、DA611–619同3轮与步长；trace分支不改变原 i |
| A buffer/提交 | 90 WAIT(3,4,1) →91 nd2nz A，GM offset row*192+i*64，m32×k64，L1 base0 →92 SET(4,3,0) | 837/934/978；1118/1215/1259，同地址来源/shape/stride/事件 |
| B buffer/提交 | 113 WAIT(3,4,2) →114 nd2nz B，GM offset i*64*64+col，k64×n32，L1 base4096 →115 SET(4,3,1) | 1416/1513/1557；1837/1934/1978，同参数与事件 |
| MMA 消费/归还 | 117实际 m32,k64,n32、readiness0/1、L1 release1/2、kloop=i、back-event=-1/-1，init=(i==0) | 1655；2120，同 descriptors/实参；原A/B/C formals保持 |
| 末轮 drain | 122/123 WAIT(3,4,1/2)，124 SET(2,10,0) | 1703/1843/1983；2264/2404/2544 |
| C publication | 141 WAIT(2,10,0) →142 fixpipe L0C→原 C →143 BARRIER6 | 2139/2236/2237；2744/2841/2982 |

实际 grid 的行/列起点为0/32、K偏移0/64/128，所有 tile完整；A/B各 **4096B**，L1区间分别0..4095、4096..8191，仍是独立真实buffer；相比BK32各2048B和六轮，本例不是简单复制同一个table常量。zero-fill/padding的SET/WAIT事件0和BARRIER4原分支保留，但本实际full tile不走，不拿未执行 padding 的事件当实际 generation。

### 原返回 cut 不因 BK64 改变

H 是同资源的实际闭包，SHA **7f4e64f840da5f1c581754e8e57cfa3f9510ddff57b422fc2f3f05824d70c7e9**。已核：

1. descriptor A/B 的 mn_max=32，H:351–360 得 k_part=512；k_actual64，H:453–459 的 ceil 得 **1个非空part**。这次是按实际 BK64 descriptor 算，不按 num_stages=1 猜。
2. H:628 的 M→MTE1复用等待，640/679 的 A/B MTE2→MTE1 readiness0/1；652/691 L1→L0，664/703发布L1 reuse1/2；753–755 MTE1→M、870 MAD。这些方向/事件与caller参数配套，release本身仍不是MMA完成。
3. L0C m-size=2×16=32，n32，小tile条件4<10，原883 BARRIER(M)依然成立。
4. 更直接的原cut：两个actual back-event均 **-1**，H:907–922 在helper return前仍执行 WAIT(M→MTE1,0/1)。这不是新 logger wait，且不受 k32改k64影响。

因此 ordinary 的“本轮 helper return→下一 caller轮 GM提交”本来没有未完成前轮MMA。sparse/default没有在这个cut额外drain一个原本可继续飞行的future MMA。本例有真实异步pipe/event及非空buffer生命周期，但不作为跨caller轮 GM/MMA overlap正例；其每轮内部原submit/readiness/consumer/reuse许可关系保持。无需发明相同 issue 排序或硬件 busy 证书才能作这个有限判断。

## AIV 与 logger 的有限核验

ordinary AIV SHA **1933e02…bbc67** 与已审BK32 AIV同bytes，可复用其State逻辑：GM State→UB、SET/WAIT(4,1,0)、int32 +1、SET/WAIT(1,5,0)、UB→原State GM、BARRIER6。SV实际614/659/801/899/944/1086/1184/1185，DV1043/1088/1230/1328/1373/1560/1658/1659；State formal仍%6、每实际subblock16×32范围与offset保持。DV三轮 `tt.dot` source marker 空循环不是AIV MMA，不构造AIC C→AIV State通道。

四份adapted所增trace访存经hidden formal%7，原A/B/C/State formals没有变成logger根。clock asm只读SYS_CNT，source asm为空且只携坐标；其结果和trace cursor只控制记录分支。原 GM offset、shape/clamp、MMA实参、loop induction来自原坐标/常量/phi，不依赖MMA返回值或clock。相关数学calls均void；新增分支在原continuation合流，overflow不改原mathbackedge。实际SET/WAIT/BARRIER调用集合与原各路径一致，未见新完成barrier、轮询、atomic/global logger lock。这同时核来源/控制/资源，不仅是“无新barrier”。

记录器额外GM流量/指令确会扰动observer经过时间；本报告不承诺零扰动、ordinary walltime保持或性能收益。旧warm profile跨度含host gaps，也不是纯设备logger开销。

## 动态记录与明确不提升的资格

实际首sparse/default事件文件分别 complete、70/106 interval，端点140/212；两展示AIC的循环内WAIT(3,4,1/2)、SET(4,3,0/1)各 **3 occurrences**，首SET和末drain各1，与实际三轮非空提交一致；default AIC dot各3。AIV markers/State与原各自路径保留，不能将AIV空source循环认作计算消费。

raw SHA实际为 **fc2bcd65c207045f858047aa44110aa707a575e9ced4e5c7f3264c95da41c9b2** / **d57ad660e60dbd57c14ad7ac5007db07d3db350f2ef689ac71a1cddb3d1064a8**，与capture登记一致。这里只核结构/次数交叉关系，未重新授source/native iteration_id。

两旧capture仍 time_arrow_verified=false、observed_dependency unavailable（Native instruction/getter bindings are incomplete）、static_readiness partial。保持这些事实；本有限静态preservation报告不填clock/valueflow/native-region/跨actor epoch资格，也不强迫该BK64另造一条时间箭头来关闭三方关系项。

## 缺陷、缺口和本子门结论

**Confirmed blocker / major / minor：没有新增。** 没有发现需要修改插桩才能保留BK64原关键阶段关系的具体路径。

**本子门必要 verification gaps：已闭合。** v1 缺的 ordinary final actor/whole绑定及profileactual参数/resource原件均已到达并实际核验；不再以那份旧缺物清单阻塞本项。无须新数学、SDK helper提取、设备/模型或完整ISA审核。

**其它范围：** 未授 native source/loop 自动规则、reader→record值流/epoch及whole-goal；历史explicit sparse1失败保持。原R091 G1/G2及其它后端原范围由各自实际修复/材料判断，不随此子门通过。

**Optional：** 摘要可将BK32六轮各2048B与BK64三轮各4096B、两者原MMA返回cut均存在并列解释，避免把tile变大或stages=1误述成必然overlap变化。这不是新的实现或验收门。

