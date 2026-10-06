# Smart Align Nodes 算法 / Algorithms

## 中文

本项目从 v0.3.x 的调试测量起步，v0.4.x 加入移动吸附，v1.0.0 加入一次性自动布局；没有引入已废弃的旧插件算法。

### 几何与证据

- 复用 `geometry.py` / `debug.py`：读取 dimensions、width、location_absolute、parent、折叠状态、Frame 与 Reroute 类型。用可靠可见节点的 dimensions.x / width 中位数归一化，不能固定除以 2，也不用 node.height 作为显示高度。
- 折叠节点沿用现有绘制边界偏移；不使用 Node Wrangler 的高亮轮廓。
- Reroute 的 location 是中心，小外框只用于碰撞检测。
- Socket 身份、顺序和 link 为拓扑输入；画布高度仍是估算。隐藏、默认值控件、自定义节点和预览可能使估算偏离。原始值与估计值分别记入调试报告。
- 原来的 Debug Selected Nodes 保持只读。自动布局的 JSON 报告写入独立文本块 Smart Align Layout Debug。

### 一次性自动布局

1. `layout_adapter.py` 快照读取当前编辑树全部节点，包括画面外选择；一次遍历 tree.links，记录端口序号、标识、状态及 multi_input_sort_id，不逐 Socket 查询 links。零尺寸或不可靠几何直接取消并提示。
2. `layout.py` 是不依赖 bpy 的纯求解器，返回所有节点的目标绝对坐标、移动原因、警告和度量。有效未静音连接决定流向；隐藏连接仍参与拓扑，静音/无效连接保留在诊断中。不能穿过未选中普通节点构造连接。
3. 快照前将选中 Frame 的全部后代递归计入有效选区（含嵌套 Frame 和转接点），不修改 Blender 的 select 属性。按最近的有效选中祖先 Frame 分组，由内向外求解；先排内部，再计算外框。未选 Frame 时，仅选中的子节点参与排列，保留 parent 和未选中兄弟的绝对位置。
4. Frame 外框预测使用实际子节点边距，手动 Frame 不主动缩小，不修改 shrink。跨 Frame 连接使用内部真实端点相对于外框的高度作为虚拟端口，不把所有连接压到 Frame 中心。
5. 按弱连通块分别整理，并以原来的上下关系排列。没有所选内部连接的节点放到下方多列区域；只连接未选中内容的节点也属于此区域，不称其为全树孤立节点。
6. 无分叉、单入单出的选中 Reroute 串链临时压缩为逻辑边，求解后恢复中心位置。选区内部的单来源分叉点跟随来源插口水平行；边界及未选中 Reroute 保持固定。串链不会每个点占据一个完整列。在首次重绘前将受阻内部连线的标记转接点与节点位置一并写入，细则见下文。
7. 迭代式拓扑排序决定列，使用每列最大真实宽度加水平留白。循环或 Frame 聚合形成的循环保留整个相关连接块的内部位置并提示；未验证的 Simulation / Repeat / Foreach 节点连接块同样保守处理，暂不做强连通块内部优化。
8. 四轮双向端口排序综合源输出、目标输入顺序和 multi-input 顺序（较高 sort ID 在上），固定节点名顺序作为确定性起点。每列按真实高度压紧，并尽量靠近关联端口的估计高度。
9. 对跨列长连接采用近似三次曲线采样、最多两轮局部向下避让，保持列内不重叠。已有 Reroute 在列间插值并避让小碰撞框。不能保证所有曲线完全无遮挡或全局最少交叉。
10. 默认避让未选中普通节点：按 X 范围筛选障碍，合并禁用的 Y 位移区间，整体向下移到安全位置。Frame 内部不是实心障碍，独立选中 Frame 则以外框参加排列。该策略可关闭；不自动改变视图，不强制吸附到移动网格。
11. `layout_operator.py` 在一个 UNDO 操作内写回。先写父层，再按当前父绝对位置换算每个子节点的 local location；随动节点不累加第二次位移。最多四次实际绘制刷新后重新求解核验；不收敛、取消或异常则恢复原始坐标及 Frame 尺寸。Frame 的脚本调用必须用 INVOKE_DEFAULT，EXEC_DEFAULT 不支持等待绘制。
12. 诊断最多各检查 100000 对节点、连线与节点、连线与连线，明确标记检查是否完整。节点遮线使用近似曲线；交叉数仅是端点直线相交的廉价估计，不能作为 Blender 真实曲线证明。预算截断时计数是已检查部分的下界。

默认水平/纵向/连接块间距为 100/50/100 画布单位。保持选择左上锚点，障碍避让允许整体下移。纯求解不读视图或 DPI；测量比例由适配层提供。v1.0.0 的已知限制包括局部回退后的整列对齐丢失和中间通道过度绕行，详见发布说明。

### 实时移动吸附（原有入口）

- G、左键拖动、Shift+A 创建、Shift+D 复制、Node Console 桥接继续使用独立的 Smart Snap 操作；自动布局不进入移动热路径。卸载恢复原生创建入口和桥接方法。
- 普通节点只用左、右、上边界；Reroute 用中心及普通节点的估计 Socket 高度。多选作为整体，不修改内部相对位置。方向键对齐已放弃。
- 移动开始缓存节点几何。只筛选当前视口与 32 px 缓冲区；平移或缩放后重新筛选。
- 默认 50 单位粗网格，每轴检查最近三条网格线，最多九个组合。边界候选优先；网格和边界都拒绝与可见普通节点重叠的结果。Frame 容器不视为整块实心障碍。
- 12 px 默认吸附触发距离与画布网格大小不同，经 View2D 和测量比例换算。鼠标、边界与引导线使用一致坐标转换，不构建全画布无限网格。
- X/Y 限轴，Alt/Option 临时绕过；同一候选合并共线目标，引导线两端渐隐。Socket 边缘窄区不启动拖动，避免干扰连线。
- Frame 的选中后代不重复平移；绝对位置在每次更新中对当前父位置换算，允许跨 Frame 参考，排除移动内容自己的祖先 Frame。
- 创建时等待有效绘制尺寸；禁用插件恢复原生行为。实时等间距组合和固定 gap 已移除。

## English

The project began with v0.3.x geometry diagnostics and added live snapping in v0.4.x. Version 1.0.0 adds one-shot auto-layout without importing the discarded predecessor's algorithms.

### Geometry and evidence

Reuse the existing geometry layer: normalize drawn dimensions through measured dimensions.x / width ratios, preserve collapsed-node calibration, and treat Reroute locations as centers. Do not hardcode DPI, use node.height as rendered height, or incorporate Node Wrangler highlighting. Socket identities and order are reliable topology inputs; socket coordinates remain estimates, especially with controls, previews and custom nodes. Debug Selected Nodes stays read-only; layout writes its own JSON report.

### One-shot layout

1. Snapshot the entire edit tree, including offscreen selections. Traverse tree.links once and retain socket identities, ordinals, flags and multi_input_sort_id. Reject unavailable or zero geometry.
2. Solve without bpy and return absolute targets, reasons, warnings and metrics. Valid unmuted links determine flow; hidden links retain topology and all other links remain in diagnostics. Never invent paths through unselected ordinary nodes.
3. Before capture, recursively expand selected Frames to include all descendants, including nested Frames and reroutes, without writing Blender selection flags. Process scopes from the deepest effective selected Frame outward, arranging contents before measuring the containing Frame. When the Frame itself is unselected, only explicitly selected children participate; fixed siblings retain absolute positions.
4. Predict Frame bounds using measured margins; retain shrink and manual sizing. External Frame ports reflect internal endpoint heights instead of the Frame center.
5. Lay out weakly connected components separately, preserving component vertical order. Place content without internal selected links below in rows, including nodes connected only to unselected content.
6. Temporarily compress unbranched selected Reroute chains into logical edges, then restore center positions in the inter-column corridor. Align internal one-source junctions to their source row; retain boundary and fixed Reroutes. Plan tagged routing points from target boxes and apply them with card positions before the first redraw, as described below.
7. Use iterative topological layering and actual maximum column widths. Cyclic components, including Frame aggregation cycles, and unverified Simulation / Repeat / Foreach components retain their internal arrangement with warnings. SCC-internal optimization is deferred.
8. Run four bidirectional ordering sweeps using both socket orders and descending multi-input sort IDs. Start from canonical names for repeatability; pack actual heights and approach estimated socket heights where possible.
9. Run at most two local downward avoidance passes for long edges using sampled approximate cubic curves. Place Reroute centers between endpoints and avoid small collisions. This does not guarantee exact wire clearance or minimal crossings.
10. Optionally avoid fixed ordinary nodes by querying their horizontal ranges and sweeping forbidden vertical offsets, shifting the scope downward as a unit. Frame interiors are not solid obstacles. Preserve the view and keep live grid quantization independent.
11. Write parent-first inside one UNDO operation, converting absolute targets through current parent origins. Verify after at most four redraws and restore on cancellation, failure or nonconvergence. Frame transactions require INVOKE_DEFAULT; EXEC_DEFAULT cannot wait for drawing.
12. Diagnostics separately bound node pairs, wire/node pairs and wire pairs to 100000 checks each. Completeness flags accompany counts. Wire obstructions use approximate cubic samples; crossing counts use endpoint chords only. Incomplete counts are lower bounds on examined data, not certificates.

Default gaps are 100/50/100 canvas units horizontally, vertically and between components. Preserve the original top-left anchor unless avoiding fixed nodes requires a downward shift. The solver is independent of viewport and DPI. Known 1.0.0 limitations include lost column alignment after local fallback and excessive detours around central corridors; see the release notes.

### Existing live snapping

G, dragging, Shift+A, Shift+D and Node Console retain their separate Smart Snap paths. Geometry is cached at movement start and filtered to the viewport plus 32 px; view changes refresh filtering. Ordinary nodes use left/right/top anchors, while Reroutes use centers and estimated socket heights. Multi-selection moves rigidly. The coarse grid defaults to 50 canvas units and checks at most nine candidates, rejecting overlaps with visible ordinary nodes. Boundary snapping takes precedence; Frame interiors are not solid obstacles.

The default 12 px snap distance is distinct from grid spacing and uses View2D plus measured geometry scaling. X/Y constrain axes, Alt/Option bypasses snapping, and guides merge collinear targets with faded ends. Narrow socket edges do not initiate dragging. Frame motion uses current absolute parent origins, permits cross-Frame references and excludes the moving content's ancestors. New nodes wait for valid dimensions. Disabling restores native hooks. Direction-key alignment, live equal-spacing combinations and fixed-gap snapping remain removed.


## 自动布局混合对齐规则 / Adaptive alignment rules

规则以归一化画布单位比较真实节点框和估算端口位置，局部结构主链与完整选区的分层布局共用判断函数。优先判断插口保留，再判断底边，最后判断顶边：

1. 折叠节点、任一高度不超过 40，或 Frame/Reroute 虚拟端点，保留插口对齐。
2. 两个端口相对顶部的距离均至少为各自高度的 55%，底边对齐后端口高度差不超过 16，且比顶边对齐改善超过 8，则选择底边。
3. 高度差不超过 `max(24, 最大高度 × 25%)`，且顶边对齐后的端口高度差不超过 `min(30, 最小高度 × 40%)`，选择顶边。
4. 其余连接使用插口对齐。分支的主连接优先级沿用端口顺序，其他输入受分支留白与障碍约束。
5. 同列至少两个节点的下游集合有共同节点时采用右边缘；其他列左边缘。列宽用最大节点宽度，窄节点仅在列内靠右，不侵占下一列留白。

纯求解设置 `alignment_style="socket"` 可用于旧规则对比；默认 `"adaptive"`。这是测试接口，未增加用户设置。规则不读取当前 Y 判断风格，避免反复执行切换风格。局部报告逐节点提供所选规则、目标、实际残差和满足标记；完整布局暂不提供逐节点选择记录。此处的底边策略仅适用于自动布局，手动移动吸附规则保持独立。

The shared decision function compares normalized drawn card heights and estimated port offsets. Collapsed/small cards and container/reroute endpoints retain socket alignment. Compatible lower ports can choose bottom alignment; similarly sized cards with a small induced slope choose top alignment. Other edges retain socket alignment. Shared-consumer columns align right edges within the maximum column width, others align left. Spacing and collision constraints can override a branch's desired alignment. The test-only socket reference mode supports repeatable comparisons without adding a user preference.

## 选区内部连线与局部回退（2026-10-05）

有效选区包括选中节点，以及选中 Frame 随动的后代。曲线遮挡与端点交叉诊断仅检查有效选区内两端都存在的可见、有效、未静音连线；内部曲线仍与所有普通节点实体检查相交。报告提供 `wire_scope="selection_internal"`、`internal_links_checked` 和检查完整性标记。外部连线不作为局部布局的避线目标、评分项或反向连线约束。节点本体避让和边界转接点固定规则仍保留。

普通局部选择按内部连通块独立处理。每块先尝试结构布局：最多 128 条内部边、10000 次转接点展开；宽度上限 `max(原宽×1.35, 原宽+200)`，高度上限 `max(原高×1.5, 原高+200)`。不增加节点重叠、内部反向连接或内部估算遮挡。主链内跨级连线最多两轮放松中间节点的纵向对齐，降低自身链条挡线的概率。

主链纵向优先以选区内终点节点的原始 top 为锚点，上游沿插口/边界对齐规则求相对高度；取消整条链的原始高度中位数定位，避免远处辅助输入拉动整个主干。其他分支继续相对消费者排列，并按插口顺序留出间距。真实节点碰撞或已放置分支约束仍可覆盖锚点；外部连线斜率不参与定位。已完成布局的终点成为下次相同锚点，不增加居中或迭代位移步骤。

结构布局因范围或几何约束失败时，尝试原范围内的局部坐标优化，仅接受降低内部线长/交叉代价且不增加重叠、反向连接、内部遮挡的移动。最多 16 轮、5000 次候选检查，必须收敛才接受；超预算的连接块保留原位。一个块失败不会丢弃其他块的结果。`partial_results` 记录节点集合、`structured/local/preserved` 方法、原因和移动数。局部回退不声称满足结构对齐规则，因此不生成虚假的对齐满足记录。

Internal-wire scope applies to effective selection, including selected-Frame followers. External wires are excluded from partial-layout costs and warning diagnostics, while all ordinary node bodies remain obstacles. Connected blocks succeed or fall back independently. Compact local fallback accepts monotonic improvements within the original extent, or preserves the affected block if it cannot converge within its budget. Geometry and wire paths remain estimates; this is not a zero-obstruction guarantee.

## Frame 一致性与自动转接点 / Frame consistency and routing

局部策略同时适用于选中 Frame 内的普通节点范围，不再仅允许无选中父框架的根范围。若外层只有一个容器，且已单独排列其内容，则不再按包含整个 Frame 的外框锚点平移一次。选中 Frame 现在包含全部后代；多 Frame 仍遵循邻域约束，未选 Frame 内的未选兄弟保持固定。

选中转接点直接连接一个选中来源节点，且全部下游也是选中的普通节点时，可贴到来源输出插口所在的水平行。这样的点不再作为原位置的固定障碍或额外列，避免卡片绕着旧分叉点排列。来源右边缘与最近目标之间至少留 32 单位，转接点距来源不超过 30；点本身需避开其他节点实体。连接外部的边界点不移动。

`layout_routing.py` 在最终位置上检查两端明确选中的普通有效连线，排除静音、隐藏、多输入及保护节点。对受阻且前向水平空间至少 56 单位的线尝试有限折点路径；已有分叉点可直接承担折弯，重复或同轴的多余候选点合并。需要复用手动点的畅通路径也参与定位。候选最多 12 个 X 位置、16 个 Y 通道，纵向扩展限制在端点范围外 240 单位以内；优先减少新建点数，再减少总点数和长度，只接受全部估算线段不穿节点的路径。一次最多处理 24 条线，每条最多新增 4 点，最多复用 16 个手动串联点，计算上限 100000 次几何检查。无法找到路径时保留原连线并继续诊断，不承诺零遮挡。

`layout_route_adapter.py` 将完整自动路径和已选中的内部单入单出手动点压缩为逻辑边。优先复用手动点，再复用自动点，仅补充缺少的点、删除多余自动点。手动点的身份、parent、标签和自定义数据保留；自动点被用户添加标签、颜色或自定义属性后同样不再可删除。分叉、断路、环、范围外、静音和多输入路径受到保护。路径及坐标相同时不写入，已有连接不重复重连。所有变化处于同一个 UNDO 操作内，保存原位置和物理连接，失败时恢复。新点优先继承两端共同父 Frame。保守保留的局部块不生成新路径；检测到循环或未验证区域时跳过本次自动绕行。

报告 `metadata.wire_routes` 记录原端点、插口序号和折点坐标，`metadata.routing_search` 给出检查数与完整性，`metrics.generated_reroutes` 给出本次新建点数。遮挡诊断按实际规划的分段估算，每条逻辑线与同一障碍最多计一次；端点弦交叉指标仍按原端点计算，不代表绕行后的真实曲线交叉数。

Local scopes inside a selected Frame use the same strategy as the equivalent child-only selection. A sole enclosing container is not translated again after its selected contents have been arranged. Internal one-source junctions follow source socket rows. Bounded routing reuses existing points before adding missing bends; external, muted and multi-input paths are retained. Routing shares the layout undo transaction and supports rollback after partial or completed writes. Search completeness and planned points appear in diagnostics; socket and curve geometry remain estimates.

## 转接点复用与减少重复计算 / Reuse and repeated work

内部手动串联点同样压缩成逻辑边，优先复用，并保留原节点及其数据。已有分叉点直接承担折弯，减少相邻重复点。相同路径再次执行时不创建、删除或重连节点。

重绘后先比对端口信息、绝对目标和实际边界。几何相符时沿用求解结果，变化时仍完整求解，保留最多四次重绘的收敛保护。未选中 Frame 自动调整原点不单独触发重算，其所有子节点的绝对目标仍逐个验证。

快照一次遍历物理连线建立入/出边索引，避免逐个调用会扫描整树的 socket.links。写回只处理有位移的节点；纯位置变化不调用 tree.update_tag() 强制更新整棵树。近似曲线按端点坐标缓存 31 个采样点，最多保存 4096 条曲线。局部搜索限制在原选区范围内，因此事先排除原范围加最大控制柄范围也无法触及的固定障碍。节点诊断保持原配对顺序和预算，跳过固定节点之间的配对遍历。

metadata.solve_calls / solve_total_ms、verification_reused_plan、location_writes、routing_link_writes 记录实际工作量；metrics.reused_reroutes / removed_auto_reroutes 区分复用与删除。

节点与连线写入属于同一轮主线程事件：先根据目标边界规划路径，再写节点和转接点，最后请求重绘。原先节点先移动、等待 80 ms 复核后才在 finish 中修改连线的顺序已移除。重绘复核仅在几何变化时校正；每次校正重新规划并一起写回。多轮路由事务按逆序恢复后，再恢复初始绝对位置，保留取消与异常恢复。物理连接列表顺序改变但逻辑边多重集合相同时，不触发额外求解。报告新增 routing_applied_before_redraw、routing_passes、routing_plan_ms。

偏好设置 layout_horizontal_gap 传给 LayoutSettings.horizontal_gap，默认 100、限制 24–400 个画布单位；仅影响下一次自动布局。完整列布局使用目标间距，局部布局仍可因原范围或边界锚点缩小间距。实时移动吸附网格与此设置独立。报告 horizontal_gap 记录本次请求值。

Selected internal manual chains also collapse to logical edges and are reused before generated points. Existing junctions serve as bends; unchanged routes need no mutations. Unchanged redraw geometry reuses the existing solution, while changed geometry still triggers bounded re-solving. Link indexes, cached curve samples and conservative obstacle filtering reduce repeated work. Position-only edits do not explicitly invalidate the whole tree. Reports expose actual solve calls, location/link writes, reused points and removed automatic points.


## 自动缩放 Frame 的重绘取整

多 Frame 的位置保护见后面的范围规则；绘制容差本身不会修改首次求解目标。

Blender 重绘可能对自动缩放 Frame 的边界、原点按绘制单位取整，同时重设子节点局部坐标，但子节点绝对坐标不变。复核中只有选中的自动缩放 Frame 使用 `max(0.1, 1 / geometry_scale)` 个画布单位的容差，比例来自当前快照的实测值；缺失或无效比例退回 0.1。普通节点、子节点和手动 Frame 仍逐个按 0.1 校验绝对位置和边界；连线端口及重数仍须一致。超过容差的真实变化保留重算及四次后回退。通过时保存重绘后的实际几何，报告记录 `frame_redraw_tolerance`。这不增加每次布局的求解次数。

## 多 Frame 的范围与位置保护

全局 selected 不参与当前 scope 的 has_boundary 判断；representative 之外的端点就是范围外连接。若一个 scope 内至少两个同层 Frame 各自拥有选中内容，将其列入 anchored_frames，内部照常求解，外层 units 排除这些容器。选中祖先也加入其上一级的锚定集合。仍根据实测边距预测自动尺寸，原点重设只影响 Frame 自身，不增加子节点位移。

这些分组及周边 scope 使用有限局部策略。候选包围盒中心相对原中心的变化不得超过 X=max(2×horizontal_gap,0.35×原宽)、Y=max(2×component_gap,0.5×原高)；宽高增长沿用局部布局的 1.35/1.5 或两个间隔上限。Frame 内容还需通过预测外框与无亲子关系节点的重叠面积检查，不得增加覆盖。拒绝结构候选后尝试紧凑局部方案，再失败则保留；原因记录 displacement_limit 或 frame_clearance。报告 metrics.anchored_frames 给出受到位置保护的框。


## v1.0.1：锚定 Frame 分组的结构保护 / Anchored Frame alignment protection

对保持原位的多个 Frame 及其选中祖先，结构候选和紧凑回退不能仅凭连线变短就打散既有节点行、同级列和连续等间距。只检查同一父级下、未折叠、互不覆盖的普通节点边界；列约束要求相同下游深度，避免把待整理的纵向串链误当成必须固定的列。边缘误差容许 1 个画布单位，左/右或顶/底之间允许自适应选择。

结构候选若破坏这些关系，记录 `alignment_regression` 并采用受约束的局部回退。回退保留原左上范围，逐个候选验证对齐和等间距，并允许邻接节点使用已有行的边缘对齐候选。未受此锚定策略约束的自由布局与转接点流程保持原行为。

For anchored sibling Frames and their selected ancestors, structural candidates and compact fallback must retain existing card rows, peer columns and consecutive equal gaps. Only separated, expanded ordinary cards sharing a parent participate. X constraints additionally require equal downstream depth, so serial stacks can still become left-to-right flow. The tolerance is one canvas unit; either card edge may represent the alignment.

Reject structural regressions with `alignment_regression` and use constrained local fallback. Preserve its original top-left envelope, validate alignment and spacing for each candidate, and allow adjacent cards to join an existing row via adaptive edge alignment. Other free-layout and reroute paths retain their previous behavior.
