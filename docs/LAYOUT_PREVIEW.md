# 自动布局说明与验证记录 / Auto-layout notes and validation history

## 中文

自动布局与移动吸附作为 v1.0.0 一同发布，当前安装包为 `Smart_Align_Nodes_v1.0.1.zip`。本文保留开发过程中各轮验证的环境、结果与限制；各轮测试数量属于当时的历史记录。当前主要验证环境为 macOS / Blender 5.2.2，发布信息见 [v1.0.1 发布说明](releases/v1.0.1.md)。

### v1.0.1 Frame 对齐修复

修复“Estimate merge distance” 外层框中 round / custom 分组受限回退导致的对齐破坏。保留原行列与等间距、三个 Frame 的绝对位置以及未选节点位置；当前副本最大普通节点位移 34.40，连续 10 次无累积漂移，撤销/重做误差为 0。仍有 6 处内部连线遮挡估算，详见 [验证记录](releases/v1.0.1-validation.json)。

### v1.0.0 已知布局问题（仍待完善）

“Extrapolate Radius” 案例中，原本畅通的中间连线因接近节点边缘被 8 单位安全边距计入遮挡。局部压缩又将两排间隙从约 54 缩至 10，后续固定节点位置的路由搜索新增 3 个转接点并改为顶部绕行。结构布局因范围超限回退时，备用算法也未保留整列边缘对齐约束。此问题已分析但尚未修复；发布 1.0.0 不改变该行为。

### 2026-10-06 偏好设置与 Frame 选择

- 快捷键说明在吸附距离上方独立强调；网格大小与网格吸附同排，自动布局横向间距与避开未选中节点同排。
- 65 条消息在英文及简体中文下验证，包括界面、Operator 上下文和工具提示；中英文偏好设置截图见 `images/preferences_en_US.png` 与 `images/preferences_zh_HANS.png`。
- 105 项单元测试、12 项 Blender 矩阵检查通过。只选框、部分子节点选中、全部子节点选中的三种嵌套框案例布局一致，保留可见选区，复用原转接点，并验证连续执行和撤销/重做。
- 原 617 节点案例取消框内节点的显式选择后，最大位移仍约 141.76，连续执行 10 次无累积位移，撤销/重做误差为 0；仍有 5 处内部连线遮挡估算。完整记录见 `frame_selection_validation_results.json`。

### 使用方式

安装本地 ZIP 并重新启用插件后，在节点编辑器选择节点，按 macOS `Command + O` / Windows、Linux `Ctrl + O`，或使用 Smart Align 侧栏的 `Arrange Selected Nodes`。不同旧版本共存时，请确认启用的是本包。

- 数据流按左到右布局，综合输入与输出 Socket 顺序；多连接块分别排列，孤立内容放下方。
- 选中 Frame 会递归包含框内全部节点，先排内部再计算框范围，不改变界面选中状态。选区内部受阻连线可自动增加少量标记转接点，逻辑连接保持不变。
- 默认水平/垂直/连接块留白是 100/50/100 画布单位。水平留白可在插件偏好设置的“自动布局横向间距”调整（24–400），下次执行生效。保持选择左上锚点；默认遇到未选中节点时整组下移，可关闭 `Avoid Unselected Nodes`。
- 一次撤销恢复整次布局，短暂的刷新校验阶段可按 Esc 取消。最多四次刷新不收敛时自动恢复并提示。
- `Smart Align Layout Debug` 保存原始几何、估算比例、连接与端口、目标位置、警告、耗时和检查完整性。

### 局部选择：结构优先（Blender 5.2.2）

普通节点/转接点的局部选择有外部连接时，按到下游的距离反推列：两个汇入同一消费者的短分支不会因为输入来自选区外而被推到最左侧。转接点不额外占一列，连接外部的转接点保持固定。

每个消费者选一条主连接组成主链；其他输入按插口顺序进入下方分支。主链根据显示高度和插口相对位置选择顶边、底边或插口对齐。共同汇入一个节点的同列分支优先右边缘，其余列采用左边缘。平行分支最小留白 50；可因障碍留出更多空间。避让时整条主链移动，保持链内关系。无法同时对齐所有输入时，优先保证列和分支清楚。

水平间距根据原有空间压缩到 24–设定值（默认 100）；保留下游锚点并按目标间距排列上游列。允许有限扩展：宽度上限为原宽度的 1.35 倍或增加两倍设定间距（取大值），高度上限为原高度的 1.5 倍或增加 200（取大值）。不得增加重叠或内部反向连接；结构方案无法满足约束时尝试原范围内的局部优化，仍失败则只保留受影响连接块的输入位置。完整选区、选中 Frame、区域保护与循环仍保留相应流程。初始彼此重叠的普通节点先展开再结构整理。

自动布局的插口估算与手动吸附分离：折叠节点多个端口按 10 单位行距分布；常见节点的简单输入行根据实际节点底部反推，避免把输入和输出都当成同一高度。依据 Blender 5.2 官方 [node_draw.cc](https://github.com/blender/blender/blob/blender-v5.2-release/source/blender/editors/space_node/node_draw.cc) 和 [node_intern.hh](https://github.com/blender/blender/blob/blender-v5.2-release/source/blender/editors/space_node/node_intern.hh) 的绘制规则校正。未知自定义面板、多行向量控件等仍用保守估算，不能承诺像素精确。

上一轮结构布局通过 67 项单元测试、Blender 5.2.2 的 12 类 GUI 回归及专用分支重现（列对齐、固定节点、撤销/重做、重复执行）。617 节点/17 选中节点样例无重叠，重复最大位移 0，选区宽度保持 1395.62，高度从 445.37 变为 422.00。估算端点直线交叉保持 34，估算穿节点从 20 变为 23；结构对齐优先并不保证每项连线指标都减少。新插口估算也改变了基准，不能与旧报告直接混比。求解约 2.2 秒（不含重绘）。详见 [上一轮验证结果](structured_layout_validation_results.json)。

用 `blender --factory-startup --python tests/blender_structured_partial.py` 在独立窗口复现专用分支。当前安装目标为 Blender 5.2.2；原先 5.1.2 的安装不变。

### 混合对齐迭代（Blender 5.2.2）

- 相近高度的展开节点优先顶边对齐，允许小幅倾斜连线换取连续、清楚的节点行。
- 两端插口都在下半部，底边对齐后连线仍接近水平时，采用底边对齐。
- 折叠节点、Frame/转接点，以及高度或端口落差明显的连接，优先按估算插口对齐。
- 同列节点共同汇入一个消费者时右边缘对齐；分叉及其他列左边缘对齐。宽度相同的节点两侧会同时对齐。
- 分支顺序、留白和避让优先于跨分支对齐；不会为拉平多个输入而把平行节点压在一起。规则由尺寸和端口决定，不随上次位置改变。

局部布局报告新增 `alignment_decisions`：`horizontal`、`vertical` 为选择的规则，`target` 为参考消费者，`vertical_error` 为剩余偏差，`vertical_satisfied` 标记是否实际满足。下方分支受间距/障碍限制时可能不满足所选规则；这些字段不会把“尝试顶边对齐”误报为“已经对齐”。完整选区也使用混合规则，但该逐节点记录目前仅覆盖局部结构布局。

同一份 617 节点/17 选中节点数据，对比纯插口主链和混合对齐：选区宽高保持 1395.62 × 422.00，重复最大位移 0，未选节点不动；估算端点交叉 34 → 32，估算穿节点 23 → 21（原始布局为 20）。这些是近似诊断，不代表所有 Blender 曲线已避让。专用 GUI 重现可看到“位置 → 变换点 → 分离 XYZ”和“分离变换 → 合并变换”的顶边形成直线，折叠数学节点仍保持主连接水平。详见 [混合对齐验证](hybrid_layout_validation_results.json)。

画面对照：[上一版插口主链](images/layout_socket_reference.png) · [本轮混合对齐](images/layout_hybrid.png)。

该轮验证：73 项单元测试（含 100 组可变尺寸局部图重复稳定性）、12 类 GUI 回归、专用重现的顶边/插口规则、固定节点、重复执行和撤销/重做。规则阈值详见 [算法说明](ALGORITHM.md)。

### 选区内部避线（2026-10-05）

避线、评分与遮挡警告只检查两端都在选区内的连线。外部输入/输出线、路过选区的线不参与；未选中节点保持固定，节点实体仍参与碰撞和内部连线遮挡检查。选中 Frame 随动的后代纳入有效选区。

局部选择按连接块独立处理。某块结构方案过高、过宽或受阻时，先尝试原范围内的小幅优化；失败只保留这一块，不再取消其他块的成功结果。主链内部跨级连线挡住中间节点时，允许适当放松该节点的纵向对齐。调试报告新增 `partial_results`、`wire_scope`、`internal_links_checked`，分别说明回退原因、检查范围和参与连线数量。

本次 78 项单元测试、12 类 Blender 5.2.2 GUI 回归，以及两组专用场景的固定节点、重复执行、撤销/重做通过。在完整 617 节点/768 连线的数据中，8 选中节点案例的 9 条内部连线估算遮挡从 2 处降到 1 处；8 节点均完成调整，无节点重叠，未选节点不动，重复位移为 0。选区宽度保持 1091.85，高度为 484.00。专用 GUI 重建也得到相同结果。仍有的 1 处内部遮挡会继续提示，不能承诺完全无遮挡。17 节点案例保持原有混合对齐规则、固定节点和重复稳定性。

旧版统计包含选区外连线，不能与新版内部计数直接比较。新报告及界面截图见 [验证结果](internal_scope_validation_results.json) 和 [8 节点整理结果](images/layout_internal_eight.png)。使用 `SAN_LAYOUT_FIXTURE=partial_eight_layout blender --factory-startup --python tests/blender_structured_partial.py` 复现 8 节点场景；不设置该环境变量则复现原先 17 节点场景。

### 转接点与 Frame 一致性（2026-10-05）

原先额外选中外层 Frame 会跳过局部策略，内部节点重新按全局层级展开；现已统一处理。当前选中 Frame 会递归纳入全部后代，因此只选框、框内部分选中、框内全部选中的排列范围一致；只选部分子节点而不选框时仍只整理该部分。

内部单来源分叉转接点会与来源输出插口水平对齐。对于因此需要绕开的长线，按需添加两点或四点路径，保持首尾水平。只处理两端明确选中的普通、有效、可见、未静音连线；多输入连接不重写。自动点会标记，重复整理时重建，不持续累积；选区外路径和已被用户改成分叉的点保留。一次撤销同时恢复节点位置和原连线。

本轮 84 项单元测试、12 类 Blender 5.2.2 GUI 用例，以及 8/17 节点旧场景回归通过。新增专用 GUI 重建验证 20 个选中子节点、两个分叉点、自动绕行、Frame 选择一致性、重复执行、撤销/重做、写入后注入异常回滚、选区外自动点及静音路径保留。

该场景两个分叉点与来源插口对齐，为一条受阻长线增加 4 个自动转接点。普通节点无重叠，选区宽高为 1817.59 × 631.44；重复位移为 0，未选中普通节点保持原位。仍有 1 处内部估算遮挡，不能承诺所有线都已避让。8 节点旧场景的内部估算遮挡从上一版的 1 处降为 0。

详见 [验证结果](frame_routing_validation_results.json)、[节点选择结果](images/layout_frame_routing.png) 与 [额外选中 Frame 的结果](images/layout_frame_routing_selected.png)。专用重现命令：`blender --factory-startup --python tests/blender_frame_routing.py`。曲线和 socket 位置仍为估算；报告另外记录自动路径、生成点数和计算预算。

### 转接点复用与计算优化（2026-10-05）

内部单入单出的已选手动转接点会作为路径参与布局，不占节点列，也不再作为需要绕开的实体。先复用这些点，再复用自动点，仅添加缺少的折点。保留手动点的标签、自定义属性和 parent；自动点被用户加了标签、颜色或自定义数据后也受保护。已有分叉点直接承担转弯，多余同轴候选点合并。

加入两个原有串联点的 Frame 重现中，两点全部复用，只新增 1 点；无原有串联点的版本由新增 4 点减为 3 点。重复执行时位置写入数与新建点数均为 0，逻辑连接、Frame 选择一致性、撤销/重做和异常回滚通过。

新版在重绘后先比对实际几何，未变化时跳过第二次完整求解；复用曲线采样和连接索引，过滤局部搜索无法触及的远处障碍。只写入有变化的位置和连接，纯位置变化不再强制更新整棵树。

同一份 617 节点 / 768 连线快照，五次离线运行的中位数由 555.95 ms 降为 315.14 ms，减少约 43%；普通节点位置最大差为 0，内部估算遮挡仍为 1。该计时包括纯求解、绕行规划和诊断，不包括 Blender 重绘、几何求值或 UI 等待，不能当作所有文件的快捷键总耗时。专用 GUI 已验证 solve_calls=1 和 verification_reused_plan=true。

验证：88 项单元测试、12 类 GUI 回归、已有 8/17 节点案例、Frame 原例及两个手动点变体、后台事务测试。详见 [复用与性能验证](reroute_reuse_validation_results.json)。运行 `SAN_REUSE_MANUAL_POINTS=1 blender --factory-startup --python tests/blender_frame_routing.py` 可重现复用案例；后台事务脚本为 `tests/blender_reroute_reuse.py`。

### 同步更新与横向间距（2026-10-05）

修复先显示节点位置、等待约 80 ms 重绘复核后才重排转接路径的执行顺序。现在先规划路径，节点与转接点在同一轮事件里写入，随后一起重绘。Frame 仍有必要的重绘复核；变化时统一校正，多轮路由可逆序回滚。此调整消除插件主动分阶段显示，不承诺任意复杂节点树的 Blender 自身求值或 GPU 绘制耗时为零。

插件偏好设置新增“自动布局横向间距”（Layout Horizontal Gap），默认 100、范围 24–400，使用节点画布单位，独立于移动吸附网格。更改设置不直接修改现有节点，下次 Command/Ctrl + O 生效。局部边界和避让仍优先，因此复杂选区实际留白不保证处处等于该值。

验证通过 90 项单元测试、12 类 GUI 回归、Frame 原例以及手动转接点复用变体。首次 invoke 返回时已存在最终路由，不必等待复核；复核失败能恢复原点和连接。独立 GUI 从真实插件偏好读取 60、160、24，实际列间距与请求值相同，重复稳定，中文标签通过。详见 [同步更新与间距验证](sync_spacing_validation_results.json)。

### 局部垂直锚点（2026-10-05）

修复 “Adjust UVs - V” 中底部 UV Map 辅助输入通过主链高度中位数把整个主干拉低的问题。局部主链优先保持终点节点原始高度，分支围绕它排列；真实节点碰撞及分支间距约束仍优先。

在当前 617 节点、768 连线的完整快照上，主干终点从下移 625.48 单位改为保持原位，左侧主要分支从下移 557.52 单位改为上移 67.96 单位。重复计算位移为 0；外部连线斜率变化和额外选中唯一外层 Frame 不改变子节点结果，未选节点位置不变。此修复调整定位基准，不代表所有连线均无遮挡。

92 项单元测试、12 类 Blender 5.2.2 界面回归、Frame/转接点及八节点案例的重复、撤销、重做和回滚检查通过。完整当前选区采用只读快照计算，界面测试使用独立临时实例。详见 [垂直锚点验证](anchor_validation_results.json)。

### 多 Frame 局部定位修复（2026-10-05）

跨框连接按当前 scope 判断，即使另一端也被选中仍算当前框的边界。两个或更多同层 Frame 同时编辑时，内部整理后不再把这些框作为外层大节点重排；锚定沿选中祖先传递，避免加选外层框再次带来整体偏移。选中 Frame 的全部后代自动纳入上述范围。

局部候选限制整体平移和扩张，并检查预测外框是否增加对相邻框、节点的覆盖。空间不足时尝试原范围内的紧凑整理，再不满足则保留该连接块。回退不会保留已拒绝方案的对齐说明。

当前完整 617 节点、24 选中节点案例：最大下移从 1485.02 降至 141.76，最大横移从 1394.39 降至 20.00；custom / round 两个选中 Frame 的位置不变，未选节点不动，实际重绘后重叠诊断为 0。round 的单框结构布局会扩张到 custom，因此此组合使用紧凑回退，不能把两个独立结果直接重叠叠放。仍有 5 处估算的内部连线遮挡，本轮不保证完全避线。

实际 Blender 连续执行 10 次，第二次起无位置写入，每次一次求解、一次重绘；撤销、重做误差均为 0。100 项单元测试、12 类 GUI 布局回归和 9 项 Frame/转接点回归通过。新增 57 节点裁剪回归与完整树结果一致，并覆盖额外选中祖先及祖先外节点、输入顺序、重复执行和相邻框边界。详见 [验证数据](multi_frame_validation_results.json)、[操作前](images/layout_multi_frame_before.png)、[操作后](images/layout_multi_frame_after.png)。

### 最初预览版验证（历史记录）

环境：本机 macOS、Blender 5.1.2；新模块从工作区加载。以下均为本次重新执行的结果，而非沿用交接记录。

- 55 项 Python 单元测试通过，包含原有 29 项；另包含固定种子的 100 张随机 DAG 重复执行检查和 1000 节点链。
- 12 个独立 Blender 界面用例通过：仅 Frame、仅子节点、Frame 部分选择、嵌套、手动尺寸、折叠/隐藏 Socket、画面外选择、UI 缩放、Esc 取消、注入异常后的回滚、实际 Command+O、多输入 Socket。
- UI scale 1.0 与 1.25 的同一布局在 1 个画布单位容差内一致，没有出现倍数位移；这些是同一 Retina 机器上的 UI 缩放测试，不代表跨操作系统 DPI 验证。
- 独立界面脚本验证真实 Frame/Reroute、单次撤销、重做、重复执行、恢复后的刷新，以及重新启用/卸载。
- 后台验证两次注册/卸载、G/拖动/Shift+D/O 绑定、原生创建入口恢复、Node Console 替身桥接恢复、定时器清理、非节点编辑器 poll 拒绝。
- 实际绘制的 100/500/1000 个 Math 节点，分别使用长链及三路前向连接测试快照、求解、写回。所有六组重复执行最大坐标误差为 0。

| 节点 / 连线 | 快照 ms | 求解 ms | 写回 ms | 诊断 ms |
|---|---:|---:|---:|---:|
| 100 / 99 | 4.4 | 3.5 | 7.3 | 9.0 |
| 100 / 294 | 6.7 | 15.1 | 8.2 | 45.1 |
| 500 / 499 | 19.6 | 15.4 | 140.7 | 140.1 |
| 500 / 1494 | 18.8 | 51.0 | 180.0 | 141.9 |
| 1000 / 999 | 29.3 | 27.6 | 547.7 | 142.6 |
| 1000 / 2994 | 38.0 | 107.2 | 695.2 | 143.7 |

这张表不含事件等待与界面重绘耗时，不能当作快捷键总延迟。大图主要耗时在 Blender 的位置写回。原始数值及检查完整性见 [验证结果](layout_validation_results.json)。

### 已知边界与待人工试用

- Socket 绘制高度和连线弯曲形状仍是估算。输入带默认值控件时，不能承诺连线水平或所有节点都不挡线。
- 三路连接的 100 节点压力样例仍报告 198 次估计的连线/节点相交、60 次端点直线交叉；这不是实际 Blender 曲线交叉计数。首版避线是有限的局部优化，密集图仍需改进。
- 500/1000 节点诊断触发 100000 对检查预算，零计数不能证明全图零冲突。报告中的完整性标记必须一起看。
- 环与未验证的 Simulation、Repeat、Foreach 区域保留连接块内部布局，没有强连通块内部最优排序。普通节点组只在当前编辑树参与布局。
- 全树几何尚未绘制或无效时会取消并提示，不使用零尺寸凑结果。纯 Reroute 且没有可测量缩放参考的树也会保守取消。
- Windows/Linux、Blender 4.x/5.2、自定义节点、各种预览/默认值控件、用户自定义快捷键冲突、文本框编辑中的快捷键行为尚未全面实测。
- 本轮没有完整人工复跑 G、左键拖动、Shift+A、Shift+D、Alt/Option 和真实 Node Console 创建移动；旧单元测试与注册恢复通过不能替代这些交互验收。Node Console 桥接验证使用替身类，未声称实测了已安装的 Node Console。
- 当前 .blend 内容、用户偏好设置和已安装插件未被测试脚本覆盖。测试使用独立 factory-startup 实例和临时节点树，关闭时 Blender 会写自己的临时恢复文件。

### 复现

```bash
python3 -m unittest discover -s tests -v
blender --background --factory-startup --python tests/blender_registration_smoke.py
blender --factory-startup --python tests/blender_layout_smoke.py
blender --factory-startup --enable-event-simulate --python tests/blender_layout_matrix.py
blender --factory-startup --python tests/blender_layout_benchmark.py
```

Blender 脚本在独立窗口中自动运行并退出；结果 JSON 写入 `/private/tmp/smart_align_layout_*.json`，目前脚本针对本机 macOS 验证环境。

## Frame 重绘精度修复 / 2026-10-05

修复选中自动缩放 Frame 时，约 0.2–0.3 个画布单位的绘制取整误差被当作布局不收敛、四次重绘后误回退的问题。容差仅用于自动缩放 Frame 的外框，按当前快照的绘制比例计算；普通节点、手动 Frame、子节点绝对坐标和端口连接仍严格校验。

当前 617 节点、24 选中节点（含 custom / round 两个 Frame）的临时副本，修复前四次重绘、五次求解后回退；修复后连续十次均只求解一次、重绘一次。第二次最大微调为 Frame 0.5、普通节点 0.3833 个画布单位，第三至第十次无位置写入，没有累积漂移。十次撤销后和重做后的坐标误差均为 0，逻辑连接、父级及选择保持一致。内部估算穿节点数为 0；仍有三处与未选 Frame 的外框相交诊断，此修复不改变其评分。

96 项单元测试、12 类 GUI 回归、9 项 Frame/路由回归通过。详见 [重绘精度验证](frame_precision_validation_results.json)。

## English

Automatic arrangement and live snapping shipped together in v1.0.0; the current package is `Smart_Align_Nodes_v1.0.1.zip`. This document retains the environments, results and limitations of individual development iterations; their test counts are historical. The primary validation environment is macOS / Blender 5.2.2. See the [v1.0.1 release notes](releases/v1.0.1.md).

Version 1.0.1 preserves existing rows, peer columns and equal gaps in the enclosing “Estimate merge distance” Frame. Its three Frames and unselected nodes stay in place. The captured copy shows a maximum ordinary-node movement of 34.40 units, no accumulated drift over ten invocations, and zero undo/redo error. Six estimated internal wire obstructions remain. See the [validation record](releases/v1.0.1-validation.json).

Known unresolved case: in “Extrapolate Radius”, an unobstructed central wire falls inside the 8-unit clearance padding. Compact fallback narrows the row gap from about 54 to 10 units, after which routing adds three points above the nodes. The fallback also loses shared column-edge alignment after rejecting a structural layout for excessive extent. Version 1.0.0 does not change this behavior.

Use Command+O on macOS, Ctrl+O on Windows/Linux, or Arrange Selected Nodes in the sidebar. The solver organizes flow, socket order, components, Frames and Reroutes while preserving logical connections and existing parents. Obstructed internal wires may receive tagged routing points. Trial gaps are 100/50/100 canvas units. Fixed-node avoidance defaults to enabled and can shift the scope downward; disable it if desired. One undo restores the operation, and Esc cancels during verification. Nonconvergence after four redraws restores the original layout.

### Verified on macOS / Blender 5.1.2

- All 55 unit tests, including the original 29, 100 seeded random-DAG repeat checks and a 1000-node chain.
- Twelve GUI cases covering Frame selection variants, nesting, manual sizes, collapsed/hidden sockets, offscreen selection, UI scale, cancellation, injected failure rollback, the actual Command+O binding and multi-input sockets.
- Equivalent layouts at UI scale 1.0 and 1.25 within one canvas unit on this Retina machine; this is not a cross-platform DPI claim.
- Real Frame/Reroute layout, one undo, redo, repeat stability and post-restore redraw in a separate GUI smoke test.
- Two registration cycles, keymaps, native add-hook restoration, a Node Console stub bridge, timer cleanup and non-node-editor poll rejection in background Blender.
- Six benchmarks with drawn Math nodes. The table above separates snapshot, solve, write and diagnostic times; it excludes event waits and redraw latency. Repeat displacement was zero in all six. Raw metrics and completeness flags are in [validation results](layout_validation_results.json).

### Limits

Socket coordinates and cubic wire paths remain estimates. Dense graphs still contain obstructions: the 100-node / 294-link stress case reported 198 estimated wire/node hits and 60 endpoint-chord crossings, not actual rendered-curve crossing counts. Larger benchmarks hit the 100000-pair diagnostic budget, so zero partial counts do not certify a conflict-free graph.

Cyclic and unverified Simulation / Repeat / Foreach components retain their internal arrangement. Missing geometry, including Reroute-only trees without a measurable scale reference, cancels conservatively. Windows/Linux, other Blender versions, custom nodes, varied control/preview layouts, custom-keymap conflicts and text-entry shortcut behavior remain unverified.

Full manual regression of G, dragging, Shift+A, Shift+D, Alt/Option and the installed Node Console remains outstanding. Unit and hook-restoration tests are not substitutes for those interaction checks. The Node Console test used a stub. GUI scripts use separate factory-startup instances, do not save preferences or user projects, and exit automatically; Blender may write its temporary recovery file. Reproduction commands appear above and currently target this macOS environment.

### Structured partial selections / Blender 5.2.2

Partial DAGs now use consumer-relative columns and ordered branch lanes. Main socket-aligned chains move as units; fixed nodes and boundary reroutes remain anchored. Bounded expansion is allowed. Structure takes priority over wire length, so estimated obstruction counts can occasionally increase. Collapsed and common conventional input socket estimates were corrected without changing manual snapping. The 67-test suite, twelve GUI cases and the dedicated branch/undo/redo/repeat regression pass. See `structured_layout_validation_results.json` for that iteration; the older benchmark table above is historical.

### Adaptive edge/socket alignment

Expanded cards of similar height prefer top edges when the resulting wire slope is small. Compatible lower-port connections prefer bottom edges. Collapsed, mismatched or protected-container geometry retains socket alignment. Shared-consumer siblings align right edges; other columns align left edges. Branch spacing and collision clearance override cross-branch alignment. Local diagnostics record the chosen rule and whether it was satisfied. The same 617-node case improves estimated crossings from 34 to 32 and wire obstructions from 23 to 21 versus the preceding socket-only pass; repeat displacement remains zero. See `hybrid_layout_validation_results.json` for the 73-test suite, GUI regression and comparison evidence.

### Internal selection wires / 2026-10-05

Only wires between effectively selected nodes contribute to partial-layout costs and obstruction warnings. Selected-Frame followers count as selected; fixed node bodies remain obstacles. Failed connected blocks can use compact local fallback without cancelling successful blocks. The 78-test suite, twelve GUI cases and both dedicated undo/redo/repeat fixtures pass on Blender 5.2.2. In the full 617-node tree, the eight-node selection now moves all eight nodes, preserves fixed nodes and repeats exactly; estimated internal obstructions fall from two to one across nine internal wires. One obstruction still remains. Historical mixed-scope counts are not directly comparable. See `internal_scope_validation_results.json` for current evidence.

### Junction routing and enclosing-Frame consistency / 2026-10-05

Adding the sole enclosing Frame no longer bypasses local arrangement. Internal one-source junctions follow source socket rows; obstructed ordinary links may receive bounded two/four-point routes with horizontal end segments. Tagged routes are rebuilt without growth, and participate in the same undo and rollback transaction. External, muted, hidden, invalid and multi-input wires are excluded from automatic routing.

The 84-test suite, twelve Blender 5.2.2 GUI cases, both earlier fixtures and the new routing/Frame regression pass. The twenty-child reconstruction aligns both junctions, adds four points to one bypass wire, preserves fixed cards, repeats without drift, and keeps identical card positions with or without the enclosing Frame. One estimated internal obstruction remains. The earlier eight-node case now has zero estimated internal obstructions. See `frame_routing_validation_results.json` and the two screenshots linked in the Chinese section.
