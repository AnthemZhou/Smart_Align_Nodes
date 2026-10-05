import bpy
import sys


def draw_arrange_hint(layout, compact=False):
    box = layout.box()
    row = box.row()
    row.scale_y = 1.5
    row.label(text="Arrange: Command + O" if sys.platform == "darwin" else "Arrange: Ctrl + O", icon="NODETREE")
    if not compact:
        box.label(text="Selected Frames include all contained nodes.")
        box.label(text="Change shortcut in Preferences > Keymap > Node Editor.")


def draw_snap_settings(layout, preferences):
    layout.prop(preferences, "snap_distance")
    row = layout.row(align=True)
    row.prop(preferences, "grid_size")
    row.prop(preferences, "grid_snap")
    layout.prop(preferences, "show_guides")


def draw_layout_settings(layout, preferences, compact=False):
    row = layout.row(align=True)
    if compact:
        row.prop(preferences, "layout_horizontal_gap", text="Horizontal Gap")
        row.prop(preferences, "layout_avoid_fixed", text="Avoid Unselected")
    else:
        row.prop(preferences, "layout_horizontal_gap")
        row.prop(preferences, "layout_avoid_fixed")


class SMART_ALIGN_NODES_Preferences(bpy.types.AddonPreferences):
    bl_idname = "smart_align_nodes"

    snap_distance: bpy.props.IntProperty(
        name="Snap Distance",
        description="Screen-space distance used to activate Smart Align snapping",
        default=12,
        min=2,
        max=40,
        subtype="PIXEL",
    )
    grid_snap: bpy.props.BoolProperty(
        name="Grid Snap",
        description="Snap nodes to a coarse occupancy-aware canvas grid",
        default=True,
    )
    grid_size: bpy.props.IntProperty(
        name="Grid Size",
        description="Grid interval measured in stable node canvas units",
        default=50,
        min=10,
        max=400,
    )
    show_guides: bpy.props.BoolProperty(
        name="Show Guides",
        description="Draw alignment and spacing guides while moving nodes",
        default=True,
    )
    layout_avoid_fixed: bpy.props.BoolProperty(
        name="Avoid Unselected Nodes",
        description="Avoid unselected nodes while arranging; keep local layouts near their original positions",
        default=True,
    )
    layout_horizontal_gap: bpy.props.IntProperty(
        name="Layout Horizontal Gap",
        description="Target gap between node columns in canvas units; local layouts may use less to preserve boundaries",
        default=100,
        min=24,
        max=400,
    )

    def draw(self, context):
        layout = self.layout
        links_box = layout.box()
        links = links_box.split(factor=0.5, align=False)
        left = links.column(align=True)
        right = links.column(align=True)

        def url_button(column, title, url="", enabled=True):
            row = column.row(align=True)
            row.enabled = enabled
            operator = row.operator(
                "wm.url_open",
                text=title,
                icon="URL",
            )
            operator.url = url

        url_button(
            left,
            "Bilibili: 周圣宇_Anthem",
            "https://space.bilibili.com/25142156",
        )
        url_button(
            left,
            "Xiaohongshu: 一周不剩",
            "https://xhslink.com/m/6zzQ97wiPAI",
        )
        url_button(right, "Feishu: Technical Dictionary", enabled=False)
        url_button(
            right,
            "GitHub: Smart Align Nodes v1.0.0",
            "https://github.com/AnthemZhou/Smart_Align_Nodes",
        )

        draw_arrange_hint(layout)
        settings = layout.box().column(align=True)
        draw_snap_settings(settings, self)
        arrangement = layout.box().column(align=True)
        arrangement.label(text="Automatic Layout")
        draw_layout_settings(arrangement, self)


classes = (SMART_ALIGN_NODES_Preferences,)


def get_preferences(context):
    addon = context.preferences.addons.get("smart_align_nodes")
    return addon.preferences if addon is not None else None


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
