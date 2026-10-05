"""Translate user-facing layout reports with Blender's interface language."""
import bpy


_ZH = {
    "Snap Distance": "吸附距离",
    "Screen-space distance used to activate Smart Align snapping": "触发智能对齐吸附的屏幕距离",
    "Grid Snap": "网格吸附",
    "Snap nodes to a coarse occupancy-aware canvas grid": "将节点吸附到画布网格，并考虑已有节点占用的位置",
    "Grid Size": "网格大小",
    "Grid interval measured in stable node canvas units": "网格间隔，单位为节点画布单位，不随视图缩放变化",
    "Show Guides": "显示辅助线",
    "Draw alignment and spacing guides while moving nodes": "移动节点时显示对齐和间距辅助线",
    "Arrange: Command + O": "自动排列：Command + O",
    "Arrange: Ctrl + O": "自动排列：Ctrl + O",
    "Selected Frames include all contained nodes.": "选中框架时，会排列框内全部节点。",
    "Change shortcut in Preferences > Keymap > Node Editor.": "可在偏好设置 > 键位映射 > 节点编辑器中修改快捷键。",
    "Bilibili: 周圣宇_Anthem": "B站：周圣宇_Anthem",
    "Xiaohongshu: 一周不剩": "小红书：一周不剩",
    "Feishu: Technical Dictionary": "飞书：飞书技术字典",
    "Arrange Selected Nodes": "排列选中节点",
    "Arrange selected nodes and all contents of selected Frames using socket and boundary alignment": "使用接口和节点边界对齐排列选中节点；选中框架时包含框内全部节点",
    "Debug Selected Nodes": "生成选中节点调试报告",
    "Write selected node geometry, sockets, and links to Smart Align Debug": "将选中节点的几何信息、接口和连线写入 Smart Align Debug 调试报告",
    "Debugged {count} selected node(s).": "已生成 {count} 个选中节点的调试信息。",
    "Copied to clipboard.": "已复制到剪贴板。",
    "No node tree found.": "未找到节点树。",
    "Smart Snap requires selected nodes in a node editor.": "使用智能吸附前，请先在节点编辑器中选中节点。",
    "Selected node geometry is not ready.": "选中节点的几何信息尚未就绪。",
    "Move with Smart Snap": "智能吸附移动",
    "Move selected nodes with boundary and grid snapping": "移动选中节点时使用边界和网格吸附",
    "Drag with Smart Snap": "智能吸附拖动",
    "Drag a node with boundary and grid snapping": "拖动节点时使用边界和网格吸附",
    "Duplicate with Smart Snap": "智能吸附复制",
    "Duplicate selected nodes and move them with Smart Snap": "复制选中节点，并使用智能吸附移动副本",
    "Remove on Cancel": "取消时移除",
    "Arrange selected nodes and snap movement to visible boundaries and a grid.": "排列选中节点，并在移动时吸附到可见边界和网格。",
    "Node Editor > Sidebar > Smart Align": "节点编辑器 > 侧栏 > Smart Align",
    "Avoid unselected nodes while arranging; keep local layouts near their original positions": "排列时避开未选中节点，并使局部布局保持在原位置附近",
    "Duplicate node identity": "检测到重复的节点标识",
    "Cyclic Frame hierarchy": "检测到循环嵌套的框架层级",
    "Node geometry is not ready: ": "以下节点的几何信息尚未就绪：",
    "Automatic Layout": "自动布局",
    "Layout Horizontal Gap": "自动布局横向间距",
    "Horizontal Gap": "横向间距",
    "Avoid Unselected": "避开未选中",
    "Target gap between node columns in canvas units; local layouts may use less to preserve boundaries": "相邻节点列之间的目标间距，单位为节点画布单位；局部布局可能缩小间距，以保留边界位置",
    "Avoid Unselected Nodes": "避开未选中节点",
    "Shift the arranged selection downward when it overlaps fixed nodes": "排列结果与固定节点重叠时，将选中节点整体下移避让",
    "Internal selection wires may still be obstructed; see Smart Align Layout Debug.": "选中节点之间的连线估算仍有遮挡，详见 Smart Align Layout Debug 调试报告。",
    "Local layout search limit reached; preserved affected components.": "局部布局已达到计算上限，受影响的连接块已保留原位。",
    "Some components could not fit within layout constraints; other results were kept.": "部分连接块未能满足节点避让或布局范围限制，已保留原位；其他整理结果已保留。",
    "Partial layout safety or search limit reached; preserved original positions.": "局部布局未能满足安全约束或已达到搜索上限，已保留原始位置。",
    "Layout checked; current positions were preserved.": "布局检查完成，已保留当前排列。",
    "Selection shifted downward to avoid fixed nodes.": "为避开未选中的固定节点，已将选中节点整体下移。",
    "Estimated wire obstructions remain; see Smart Align Layout Debug.": "估算仍有连线被节点遮挡，详见 Smart Align Layout Debug 调试报告。",
    "Residual node overlaps remain in preserved or fixed content; see debug report.": "保留原布局的区域或固定节点中仍存在节点重叠，详见调试报告。",
    "Cycle or unverified zone: preserved connected component internally.": "检测到循环连接或尚未验证的区域，已保留该连接块的内部布局。",
    "Curve avoidance budget reached; residual wire obstructions may remain.": "已达到连线避让计算上限，可能仍有连线被遮挡。",
    "Unverified zone nodes selected; connected components retain internal layout.": "选中了尚未验证的区域节点，相关连接块将保留内部布局。",
    "Frame layouts require interactive invocation for redraw verification.": "涉及框架的布局需要通过快捷键或界面按钮启动，以便在重绘后复核。",
    "Arranged {count} nodes; socket positions are estimates.": "已排列 {count} 个节点；接口位置使用估算值。",
    "An editable node tree is required.": "需要可编辑的节点树。",
    "Select nodes to arrange.": "请先选中需要排列的节点。",
    "Layout cancelled.": "已取消自动布局。",
    "Generated reroute cycle; layout cancelled.": "自动转接点中检测到循环连接，已取消布局。",
    "Frame geometry did not stabilize within 4 redraws; restored original layout.": "框架尺寸在 4 次重绘后仍未稳定，已恢复原始布局。",
    "Node dimensions are not ready. Draw the nodes before arranging.": "节点尺寸尚未就绪，请先让节点显示并完成绘制，再执行排列。",
    "Node dimensions are not ready: ": "以下节点的尺寸尚未就绪：",
    "Rollback incomplete: {error}": "未能完整恢复原始布局：{error}",
}


def translate(message):
    # Translate individual sentences before joining or formatting dynamic values.
    # Unknown exception details are kept intact for troubleshooting.
    for prefix in ("Node dimensions are not ready: ", "Node geometry is not ready: "):
        if message.startswith(prefix):
            return bpy.app.translations.pgettext_iface(prefix) + message[len(prefix):]
    return bpy.app.translations.pgettext_iface(message)


def register():
    messages = {(context, source): target for source, target in _ZH.items()
                for context in ("*", "Operator")}
    bpy.app.translations.register(__name__, {"zh_HANS": messages, "zh_CN": messages})


def unregister():
    bpy.app.translations.unregister(__name__)
