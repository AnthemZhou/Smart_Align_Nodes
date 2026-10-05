# Smart Align Nodes

![Blender](https://img.shields.io/badge/Blender-4.0%2B-f5792a?logo=blender&logoColor=white)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Category](https://img.shields.io/badge/category-Node%20Editor-555)
![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-lightgrey)
![License](https://img.shields.io/badge/license-GPL--3.0-green)

维护者：Anthem_周圣宇<br>
版本：1.0.0 · [下载 / Download](https://github.com/AnthemZhou/Smart_Align_Nodes/releases/tag/v1.0.0)

## 中文

Smart Align Nodes 是一个 Blender 节点编辑器对齐插件。启用插件后，移动、创建或复制节点时会自动检测可见节点边界和大尺度画布网格，并显示类似演示文稿软件的吸附参考线。插件不依赖 Blender 的原生网格量化吸附。

### 自动布局

选中节点或 Frame 后按 **Command + O（macOS）/ Ctrl + O（Windows、Linux）**，或点击侧栏 **排列选中节点**。选中 Frame 会递归包含框内全部节点和嵌套 Frame，无需逐个选中，部分选中时也按全部内容处理；不改变界面上的选中状态。按连接从左到右排列，参考 Socket 顺序整理分支，将孤立内容放在下方；画面外的选择也会参与。

自动选择插口或节点边缘对齐：相近高度的展开节点优先顶边，适合的下部连接采用底边，折叠节点优先插口；汇入同一节点的并行分支优先右边缘，其他列采用左边缘。分支间距和避让优先，多个输入不强求同时拉平。

避线与遮挡提示只检查两端都在选区内的连线；跨出选区或路过选区的外部连线不再牵动布局。未选节点保持固定，其实体仍参与避让。局部连接块无法整体整理时，尝试原范围内的小幅优化，保留其他连接块已成功的结果。选中 Frame 时，随 Frame 移动的后代计入选区。

局部布局优先保留主链终点的原始高度，其他分支围绕它排列。远处的辅助输入节点不会通过高度中位数把整个主干拉走；实际节点碰撞及分支间距约束仍可调整位置。

选中 Frame 时先排列框内全部节点，再计算外框；只选框、框内部分选中、框内全部选中，排列范围一致。只选内部节点而不选 Frame 时，仍仅排列明确选中的节点，未选中兄弟节点保持固定。唯一的外层 Frame 不会将整理后的内容再次整体平移。

选区内部的分叉转接点优先与来源插口水平对齐。优先复用参与排列的串联转接点（包含所选 Frame 内的转接点），再复用自动点，只补缺少的折点并清理多余自动点。带标签或自定义数据的原点保留，相同路径再次执行不删建、不重连。只处理两端都在排列范围内的普通连线，保留逻辑连接、参数和已有节点的 parent。一次撤销恢复布局及新增点，短暂刷新期间可以按 Esc 取消。

节点位置、转接点和连线在同一轮写入后一起重绘，不再先显示节点、等待复核后才修改路径。重绘后的几何未变化时跳过完整重算；只写入有位移的节点，纯位置调整不强制更新整棵节点树。

自动缩放 Frame 的边界允许实测绘制精度内的取整误差，避免误报“四次重绘仍未稳定”。普通节点的绝对位置、尺寸及连线仍严格校验；真实变化仍触发校正或回退。

同时选中多个同层 Frame 时，各框在原位置附近整理，完成后不再参与外层整体重排；选中的祖先框同样保留分组位置。跨框连线按当前分组识别边界。自动扩框若会与相邻内容重叠，则回退到紧凑整理，避免整组远距离避让。

默认间距为水平 100、垂直 50、连接块之间 100 个画布单位，保留选择左上锚点。在 `偏好设置 > 插件 > Smart Align Nodes > 自动布局` 调整“自动布局横向间距”（24–400），下次 Command/Ctrl + O 生效；局部布局受原范围和避让约束影响，实际间距可能缩小。默认开启“避开未选中节点”，可在侧栏或偏好设置关闭。这些设置独立于实时移动网格。偏好设置顶部突出显示排列快捷键；网格大小和网格吸附同排，横向间距和避让选项同排。设置、按钮、工具提示和操作通知随 Blender 的中英文界面切换。

Socket 坐标与曲线路径仍是估算，不保证零交叉、完全无遮挡。复杂环和未验证的 Simulation / Repeat / Foreach 连接块保留内部布局并提示。诊断写入 `Smart Align Layout Debug`，验证范围见 [布局说明与验证记录](docs/LAYOUT_PREVIEW.md)。快捷键可在 `Preferences > Keymap > Node Editor` 改绑。

### 功能

- 按 `G` 移动节点时自动吸附。
- 从 `Shift + A` 菜单创建节点并移动时自动吸附。
- 兼容 Node Console 创建节点后的移动流程。
- 按 `Shift + D` 复制节点并移动时自动吸附。
- 使用鼠标左键拖动节点标题或主体区域时自动吸附。
- 只使用左、右、上三条节点边界吸附，不再计算下边界对齐。
- 只计算当前 Node Editor 视口和少量边缘缓冲范围内的节点候选。
- 使用可配置的大尺度画布网格替代实时相等间距组合计算，默认网格尺寸为 50。
- 网格只检查移动节点附近的少量候选位置，并跳过会与可见节点重叠的位置。
- 边界吸附同样会拒绝导致节点矩形重叠的结果。
- 多选节点作为一个整体移动，不改变内部相对位置。
- 支持展开节点、折叠节点、Frame 和 Reroute 的独立几何规则。
- Frame 内外的节点可以互相作为边界和 socket 吸附目标。
- 子节点靠近 Frame 边界并触发 Frame 自动缩放时，会维持稳定的绝对移动位置。
- Reroute 在纵向移动时可以吸附到普通节点的 socket 高度候选。
- 青色参考线表示边界吸附，橙色测量线表示相等间距，线段首尾带有渐隐效果。
- 提供 `Debug Selected Nodes`，用于输出节点几何、Frame、Reroute、socket 和 link 数据。

### 安装

1. 从 [v1.0.0 Release](https://github.com/AnthemZhou/Smart_Align_Nodes/releases/tag/v1.0.0) 下载 `Smart_Align_Nodes_v1.0.0.zip`（选择插件附件，而非 GitHub 自动生成的源代码 ZIP）。
2. 在 Blender 中打开 `编辑 > 偏好设置 > 插件`。
3. 点击 `安装...`，选择下载的 zip 文件。
4. 启用 `Smart Align Nodes`。

### 使用

1. 打开任意节点编辑器。
2. 选择一个或多个节点。
3. 按 `G`、使用 `Shift + A` 创建节点、按 `Shift + D` 复制节点，或直接用鼠标左键拖动节点。
4. 移动鼠标。进入吸附距离后，节点会自动对齐并显示参考线。
5. 点击鼠标左键或按 Enter 确认位置。

移动时按 `X` 或 `Y` 可以限制轴向。按住 `Alt/Option` 可以临时跳过吸附。

### 设置

- `吸附距离`（Snap Distance）：边界或间距候选在屏幕上的触发距离，单位为 px。默认值是 12 px，不是网格间距或节点间隔。
- `Grid Snap`：启用带占用检测的大尺度画布网格。
- `Grid Size`：网格在节点画布坐标中的间隔，默认值为 50，不随视图缩放改变。
- `Show Guides`：显示吸附参考线。
- `自动布局横向间距`（Layout Horizontal Gap）：相邻节点列的目标留白，默认 100，范围 24–400；调小可使自动布局更紧凑。
- `Debug Selected Nodes`：将选中节点的诊断信息写入 Blender 文本块 `Smart Align Debug`，并输出到系统控制台。

### 说明

- 已知布局问题：局部压缩可能挤掉已有的中间走线通道，导致不必要的顶部绕行；结构布局回退后，也可能丢失整列边缘对齐。此问题尚未修复，详见 [1.0.0 发布说明](docs/releases/v1.0.0.md)。
- Smart Snap 会在插件启用时接管节点编辑器中的普通 `G` 移动。禁用插件后会恢复 Blender 原生行为。
- Blender 的公开 Python API 不提供 socket 的最终画布绘制坐标。Reroute 到 socket 的吸附位置目前根据节点边界、socket 顺序和显示状态估算，不同自定义节点可能仍需继续校准。
- 鼠标拖动会覆盖节点内部的大部分区域。为避免影响连线操作，节点左右两侧靠近 socket 的窄区域不会启动拖动。
- 插件以普通 Blender 插件 zip 格式发布，开源协议为 GPL-3.0-only。

## English

Smart Align Nodes is an alignment add-on for the Blender Node Editor. Once enabled, it detects visible node boundaries and a coarse canvas grid while nodes are moved, created, or duplicated, then displays presentation-style snapping guides. Blender native grid quantization is not required.

### Automatic layout

Select nodes and press **Command + O (macOS) / Ctrl + O (Windows, Linux)** or use **Arrange Selected Nodes** in the sidebar. Arrange flow left to right using socket order, with disconnected content below and offscreen selections included.

Selecting a Frame recursively includes all its nodes and nested Frames, even when none or only some of its children are explicitly selected. Visible selection stays unchanged. Selecting children without their Frame still arranges only those children. A sole enclosing Frame does not translate the completed internal arrangement again. Internal junctions align to their source socket row. Internal serial reroutes, including implicitly included Frame contents, are reused before adding points; surplus generated points are removed, while labels, custom data and existing parents are preserved. Unchanged paths need no node/link mutations. Unchanged redraw geometry skips the second full solve. One undo restores the layout and routing; Esc cancels during its brief redraw phase.

Alignment adapts to card geometry: top or compatible bottom edges for expanded cards, sockets for collapsed or mismatched cards, right edges for shared-consumer siblings and left edges elsewhere. Branch spacing and obstacle clearance take precedence.

Local layouts anchor each terminal chain at its consumer's original height. Distant helper inputs no longer shift the main flow through median-based centering; collisions and branch clearance may still override that anchor.

Defaults are 100/50/100 canvas units for horizontal, vertical and component gaps, preserving the top-left anchor. Set `Layout Horizontal Gap` (24–400) under the add-on's `Automatic Layout` preferences; the next Command/Ctrl + O uses it. Local layouts may compress the target gap to respect existing bounds and clearance. `Avoid Unselected Nodes` defaults to enabled and shifts conflicting selections downward; disable it in the sidebar or preferences. These defaults are separate from live grid snapping.

Apply node positions and reroute paths together before the first redraw. Verification checks the resulting geometry and only makes corrections when needed; it no longer defers initial routing until after cards become visible.

Auto-sized Frame bounds allow rounding within the measured draw precision, avoiding false four-redraw rollback. Ordinary node positions, dimensions and links remain strictly checked; real changes still trigger correction or rollback.

When multiple sibling Frames are selected, arrange their contents nearby without subsequently repacking those groups or their selected ancestors. Detect boundaries per scope, even when the other endpoint is selected. Expansion into neighboring content uses a compact fallback.

Preferences emphasize the platform's Arrange shortcut above Snap Distance. Grid Size shares a row with Grid Snap; Layout Horizontal Gap shares a row with Avoid Unselected Nodes. Settings, buttons, tooltips and operation reports support English and Simplified Chinese through Blender's language settings.

Socket coordinates and wire paths remain estimates; zero crossings and exact clearance are not guaranteed. Cyclic and unverified Simulation / Repeat / Foreach components retain their internal arrangement with warnings. Diagnostics go to `Smart Align Layout Debug`. See [layout notes and validation history](docs/LAYOUT_PREVIEW.md) for validation limits. Rebind under `Preferences > Keymap > Node Editor`.

### Features

- Automatically snaps nodes during ordinary `G` movement.
- Automatically snaps newly created nodes while placing them from the `Shift + A` menu.
- Supports post-creation movement initiated by Node Console.
- Automatically snaps duplicated nodes during `Shift + D` placement.
- Automatically snaps while dragging a node by its title or body with the left mouse button.
- Uses only left, right, and top node-boundary snapping. Bottom-edge alignment is no longer evaluated.
- Evaluates targets only inside the current Node Editor viewport plus a small edge margin.
- Replaces live equal-spacing combinations with a configurable coarse canvas grid, defaulting to 50 units.
- Checks only a small set of nearby grid candidates and skips positions that overlap visible nodes.
- Rejects boundary snap results that would overlap node rectangles.
- Moves a multi-node selection as one group without changing its internal layout.
- Uses separate geometry rules for expanded nodes, collapsed nodes, Frames, and Reroutes.
- Allows nodes inside and outside Frames to act as boundary and socket snap targets for each other.
- Keeps child movement stable when approaching a Frame boundary causes the Frame to auto-resize.
- Lets a vertically moving Reroute snap to estimated socket-height candidates on normal nodes.
- Uses cyan boundary guides and orange spacing measurements with faded ends.
- Includes `Debug Selected Nodes` for node geometry, Frame, Reroute, socket, and link diagnostics.

### Install

1. Download `Smart_Align_Nodes_v1.0.0.zip` from the [v1.0.0 Release](https://github.com/AnthemZhou/Smart_Align_Nodes/releases/tag/v1.0.0). Choose the add-on asset, not GitHub's automatically generated source-code ZIP.
2. In Blender, open `Edit > Preferences > Add-ons`.
3. Click `Install...`, then choose the downloaded zip file.
4. Enable `Smart Align Nodes`.

### Usage

1. Open any node editor.
2. Select one or more nodes.
3. Press `G`, create a node with `Shift + A`, duplicate with `Shift + D`, or drag a node directly with the left mouse button.
4. Move the pointer. The node snaps and displays a guide when a candidate enters the snap distance.
5. Click the left mouse button or press Enter to confirm.

Press `X` or `Y` during movement to constrain an axis. Hold `Alt/Option` to bypass snapping temporarily.

### Settings

- `Snap Distance`: the screen-space activation distance for boundary and spacing candidates, measured in px. The default 12 px is not a grid interval or node gap.
- `Grid Snap`: enables the coarse occupancy-aware canvas grid.
- `Grid Size`: controls the grid interval in stable node-canvas units. The default is 50 and does not change with view zoom.
- `Show Guides`: displays snapping guides.
- `Debug Selected Nodes`: writes selected-node diagnostics to the Blender text block `Smart Align Debug` and prints the same report to the system console.

### Notes

- Known layout issue: compact fallback can close an existing central wire corridor, introduce an unnecessary overhead detour and lose shared column-edge alignment. This remains unresolved in 1.0.0; see the [release notes](docs/releases/v1.0.0.md).
- Smart Snap replaces ordinary `G` movement in the Node Editor while the add-on is enabled. Disabling the add-on restores Blender native behavior.
- Blender's public Python API does not expose final canvas coordinates for sockets. Reroute-to-socket snapping currently estimates positions from node bounds, socket order, and visibility, so custom node types may still require calibration.
- Mouse dragging covers most of the node interior. Narrow strips near the left and right socket edges remain available for link interaction.
- The add-on is released as a regular Blender add-on zip under GPL-3.0-only.

See [LICENSE](LICENSE).
