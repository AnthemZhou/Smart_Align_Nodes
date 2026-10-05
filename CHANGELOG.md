# Changelog

## v1.0.0 — 2026-10-06

### 中文

- 选中 Frame 时自动递归排列框内全部节点和嵌套 Frame，即使未选中或只选中部分子节点；保留界面选择状态，并复用框内现有转接点。
- 补齐偏好设置、侧栏、操作按钮、提示与工具提示的简体中文翻译；突出显示排列快捷键，并将网格设置、布局间距与避让选项分别合并为同一行。
- 修复同时选中多个 Frame 及其内部节点时的巨大偏移：按当前分组识别跨框连接，内部整理后不再整体重排这些框及其选中祖先；限制局部位移和扩张，避免自动外框吞入相邻内容，空间不足时紧凑整理或保留原位。
- 自动缩放 Frame 的重绘复核按实测绘制比例容许一个绘制单位的取整误差，避免微小边界变化导致四次重算后误回退；普通节点、手动 Frame 和连线仍严格校验。
- 局部主链以终点节点原始高度为锚点，修复底部辅助输入节点通过高度中位数把主干和后续分支整体拉低的问题；保留碰撞避让、Frame 一致性和重复执行稳定性。
- 节点与转接路径在首次重绘前一并更新，消除先移动节点、复核后才重排连线的分阶段显示；多次校正的路由事务按逆序回滚。
- 偏好设置新增“自动布局横向间距”，默认 100，范围 24–400，下次 Command/Ctrl + O 生效，支持中文界面。
- 优先复用选区内部的串联转接点，保留节点身份、标签和自定义数据；已有分叉点直接承担折弯，减少重复点，仅清理多余自动点。
- 相同路径不再删建或重连；只写入变化的位置，取消纯位置调整对整棵树的强制更新。
- 重绘几何未变化时跳过第二次完整求解；缓存曲线采样、索引连接并排除局部候选无法碰到的远处障碍。报告新增实际求解次数、位置写入数和转接点复用数。
- 修复额外选中唯一外层 Frame 时跳过局部策略、打散内部排列的问题。
- 选区内部的分叉转接点跟随来源插口水平对齐；受阻普通连线按需增加标记转接点，限量绕行。重复整理复用自动点，保留逻辑连接，支持单次撤销和异常回滚。
- 自动绕行不处理选区外、静音、隐藏、无效或多输入连线；保留范围外及被手动改成分叉的自动点，报告绕行方案与计算预算。
- 避线评分与遮挡提示只处理选区内部连线；外部连线不再影响局部布局，未选节点实体仍是障碍。
- 局部选择按连接块独立求解；结构布局超出范围时尝试原范围内的局部优化，受限连接块不再取消其他块的结果。报告增加连线检查范围与连接块回退原因。
- 主链内部的跨级连线允许局部放松边缘对齐以避让中间节点；尊重选中边界转接点的输入优先级。
- 自动布局采用混合对齐：相近高度的展开节点优先顶边、下部插口适合时底边、折叠和高度差大的连接保留插口对齐；共同汇入下游的并行节点右边缘对齐，其余列左对齐。
- 局部布局调试报告记录每个节点的对齐选择、剩余偏差与是否满足，区分规则选择和分支避让后的实际结果。
- 局部布局改为结构优先：从下游反推列，短分支靠近消费者；按输入顺序分支，主链整体对齐和避让。
- 允许有限扩展选区，固定外部节点与边界转接点；遇到安全约束、循环或预算限制时保守回退。重复执行保持稳定。
- 自动布局独立校正折叠节点的多个插口，以及常见展开节点底部输入行；未知面板/多行控件仍使用估算，不改动手动吸附。
- 自动布局警告、完成提示及已知错误提示跟随 Blender 界面语言，增加简体中文翻译。
- 增加自动布局试用功能：Command/Ctrl + O、Socket 排序、连接块与孤立区、Frame 分层和已有 Reroute 串链。
- 分离快照、纯 Python 求解和绝对坐标写回；最多四次绘制刷新复核，取消或失败恢复原始布局。
- 增加可关闭的未选中节点避让、有限近似曲线避线，以及明确检查预算和完整性的诊断。
- 将此前的 0.5.0 开发快照统一发布为 1.0.0，安装包为 `Smart_Align_Nodes_v1.0.0.zip`。
- 已知问题：局部紧凑回退可能压缩已有中间走线通道，产生多余的顶部绕行，并丢失整列边缘对齐；本次发布保留当前算法，未包含此问题的修复。

- 边界吸附仅保留左、右、上对齐，移除下边界对齐。
- 只让当前节点编辑器视口及少量边缘缓冲内的节点参与实时吸附。
- 缓存目标节点边界，只有视口平移或缩放时才重新筛选可见目标。
- 使用默认尺寸为 50 的大尺度画布网格替代实时相等间距和固定纵向 gap 计算。
- 每次移动只检查附近最多九个网格组合位置，不生成整张画布的占用网格。
- 网格和边界吸附都会跳过导致节点矩形重叠的结果。
- Frame 可作为对齐目标，但 Frame 内部不会整体视为被占用区域。

### English

- Selecting a Frame recursively arranges all contained nodes and nested Frames, even with no or partial child selection; preserve visible selection and reuse existing internal reroutes.
- Complete Simplified Chinese coverage for preferences, sidebar, operators, reports and tooltips; emphasize the Arrange shortcut and pair grid settings and layout spacing/avoidance controls on shared rows.
- Fix large displacement when editing multiple selected Frames and their children: detect scope boundaries independently of global selection, keep edited groups and their selected ancestors out of outer repacking, bound local movement and growth, and reject Frame expansion into neighboring content with compact fallback.
- Allow one measured draw unit of rounding for auto-sized Frame bounds during redraw verification, preventing false four-pass rollback; retain strict checks for ordinary nodes, manual Frames and links.
- Anchor local terminal chains at the consumer's original height, preventing distant helper inputs from pulling the main flow and following lanes downward through median-based centering; retain collision clearance, Frame consistency and repeat stability.
- Apply cards and routed wires together before the first redraw; roll back correction-pass routing transactions in reverse order.
- Add a translated Layout Horizontal Gap preference (24–400, default 100), used by the next Command/Ctrl + O invocation.
- Reuse selected internal serial reroutes while preserving identity and metadata; let existing junctions serve as bends and remove only surplus generated points.
- Avoid mutations for unchanged paths and locations; skip whole-tree evaluation tags for position-only edits.
- Verify unchanged redraw geometry without a second full solve; cache wire samples, index links and prune unreachable fixed obstacles. Report solve calls, position writes and reuse counts.
- Fix an extra enclosing-Frame selection bypassing the local strategy and scattering its selected contents.
- Align internal junctions with source socket rows and add bounded, tagged reroutes for obstructed ordinary wires. Reuse generated routes without accumulation, preserve logical connections, and include routing in undo and failure rollback.
- Leave external, muted, hidden, invalid and multi-input wires unchanged; preserve out-of-scope and manually branched generated points. Report routing plans and search budgets.
- Score and report only wires internal to the effective selection; retain fixed node bodies as obstacles.
- Solve partial connected components independently, try compact local improvements after structural rejection, and record per-component fallback reasons without discarding other successes.
- Relax an intermediate card's alignment for internal bypass wires and respect selected boundary-reroute input priority.
- Blend card-edge and socket alignment: top edges for similarly sized expanded cards, bottom edges for compatible lower ports, sockets for collapsed or mismatched cards; align shared-consumer siblings on the right and other columns on the left.
- Record local alignment choices, residual errors and satisfaction in layout diagnostics.
- Prioritize structure for partial selections: consumer-relative columns, ordered branch lanes and aligned main chains that move together around obstacles.
- Permit bounded expansion, retain external nodes and boundary reroutes, and fall back on safety/search limits or cycles. Repeated arrangement stays stable.
- Improve layout-only socket estimates for collapsed nodes and common single-row inputs; keep manual snapping calibration unchanged.
- Translate layout warnings, completion messages and known errors into Simplified Chinese using Blender's interface language.
- Add auto-layout preview: Command/Ctrl + O, socket ordering, connected components, isolated content, hierarchical Frames and existing Reroute chains.
- Separate snapshots, the pure Python solver and absolute-coordinate writeback; verify over at most four redraws and restore on cancellation or failure.
- Add optional fixed-node avoidance, bounded approximate wire avoidance and diagnostics with explicit budget-completeness flags.
- Release the former 0.5.0 development snapshot as 1.0.0, packaged as `Smart_Align_Nodes_v1.0.0.zip`.
- Known issue: compact fallback may close an existing central wire corridor, introduce unnecessary overhead routing and lose column-edge alignment. This release preserves the current solver and does not include a fix for that issue.

- Keep left, right, and top boundary alignment while removing bottom-edge alignment.
- Evaluate live snap targets only in the current Node Editor viewport plus a small edge margin.
- Cache target geometry and refresh visible targets only after viewport pan or zoom changes.
- Replace live equal-spacing and fixed vertical-gap calculations with a coarse canvas grid whose default size is 50.
- Check at most nine nearby grid combinations per movement update instead of building an infinite occupancy grid.
- Reject grid and boundary snap results that overlap node rectangles.
- Keep Frames available as alignment targets without treating their entire interior as occupied.

## v0.4.2

### 中文

- 将维护者改为 `Anthem_周圣宇`。
- 在插件偏好设置中增加 B站、小红书、飞书和 GitHub 按钮。
- 校准 Reroute 到 socket 的首行中心高度。
- 等待新建节点生成有效渲染尺寸后再进行吸附计算。
- 增加 Node Console 创建后移动流程的兼容桥接。
- 增加默认值为 30 的可配置纵向节点间距。
- 改用局部 `location` 写入节点位移，修复 Frame 无法移动的问题。
- 允许 Frame 内外节点互相作为边界和 socket 吸附目标。
- 排除移动节点自己的祖先 Frame，避免子节点被父 Frame 边界干扰。
- 根据父 Frame 的实时绝对坐标换算子节点局部位置，修复 Frame 自动缩放时的累积漂移。

### English

- Change the maintainer to `Anthem_周圣宇`.
- Add Bilibili, Xiaohongshu, Feishu, and GitHub buttons to add-on preferences.
- Calibrate the first-row center used for Reroute-to-socket snapping.
- Wait for valid rendered dimensions before snapping a newly created node.
- Add a compatibility bridge for Node Console post-creation movement.
- Add a configurable default vertical node gap of 30.
- Write movement through local `location` coordinates to fix Frame movement.
- Allow nodes inside and outside Frames to act as boundary and socket snap targets for each other.
- Exclude a moving node's own ancestor Frames from snap targets.
- Convert child positions against the parent Frame's live absolute position to prevent cumulative drift while the Frame auto-resizes.

## v0.4.1

### 中文

- 将鼠标拖动吸附范围从节点标题扩展到节点主体区域，并保留 socket 两侧的连线操作空间。
- 修正折叠节点在画布上的整体绘制偏移，提高上边界和下边界吸附精度。
- 增加 Reroute 到普通节点 socket 高度候选的纵向吸附。
- 将 README 和 release note 改为中英文双语结构。
- 保留 `G`、`Shift + A`、`Shift + D`、四边界吸附、相等间距和调试报告功能。

### English

- Extend mouse-drag snapping from node titles to node body areas while keeping narrow socket-edge regions available for link interaction.
- Correct the canvas render offset of collapsed nodes to improve top and bottom boundary snapping.
- Add vertical Reroute snapping to estimated socket-height candidates on normal nodes.
- Use bilingual Chinese and English structures for the README and release notes.
- Preserve `G`, `Shift + A`, `Shift + D`, four-boundary snapping, equal spacing, and debug reports.

## v0.4.0

- Integrate Smart Snap into ordinary `G` movement and new-node placement.
- Add left, right, top, and bottom boundary snapping.
- Add Smart Snap when dragging nodes from their title area.
- Add Smart Snap after `Shift + D` duplication.
- Re-register Blender's Python node-add operators so `Shift + A` placement enters Smart Snap.
- Add equal-spacing snapping for insertion and sequence extension.
- Require real orthogonal overlap before activating equal-spacing snapping.
- Place spacing guides inside the common overlap region.
- Add screen-space thresholds and alignment or spacing guides with faded ends.
- Normalize mouse movement and guide drawing against Blender's measured UI scale.
- Normalize expanded and collapsed nodes from their live rendered dimensions.
- Remove Node Wrangler highlight-outline offsets from snap geometry.
- Extend alignment guides across every node on the same snapped boundary.
- Move multi-node selections as one group.
- Add Frame-aware movement roots and Reroute center snapping.
- Add axis constraints and temporary snap bypass.
- Add add-on submodule reloading after an overwrite update.
- Keep the `v0.3.1` debug report available.

## v0.3.1

- Add Blender version, display scale, editor region, and View2D diagnostics.
- Add observed geometry scale ratios and normalized node box candidates.
- Report Reroute nodes as center anchors with candidate collision boxes.
- Add Frame ancestry and selected movement roots.
- Expand Socket visibility and display-state diagnostics.
- Fix node-level link matching for Blender RNA wrapper objects.
- Keep all debug geometry read-only and label inferred values explicitly.

## v0.3.0

- Start the new Smart Align Nodes implementation from a clean design.
- Add a node editor sidebar panel.
- Add selected-node debug output.
- Add raw geometry, socket, link, Frame, and Reroute diagnostics.
- Add GPL-3.0 license.
- Add initial algorithm planning document.
