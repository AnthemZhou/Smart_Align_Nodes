import bpy


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
    equal_spacing: bpy.props.BoolProperty(
        name="Equal Spacing",
        description="Snap to positions that create equal gaps between neighboring nodes",
        default=True,
    )
    vertical_gap: bpy.props.IntProperty(
        name="Vertical Gap",
        description="Default boundary gap when nodes are arranged vertically",
        default=30,
        min=0,
        max=200,
    )
    show_guides: bpy.props.BoolProperty(
        name="Show Guides",
        description="Draw alignment and spacing guides while moving nodes",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        links_box = layout.box()
        links = links_box.split(factor=0.5, align=False)
        left = links.column(align=True)
        right = links.column(align=True)

        def url_button(column, prefix, title, url="", enabled=True):
            row = column.row(align=True)
            row.enabled = enabled
            operator = row.operator(
                "wm.url_open",
                text=f"{prefix:<8}{title}",
                icon="URL",
            )
            operator.url = url

        url_button(
            left,
            "B站:",
            "周圣宇_Anthem",
            "https://space.bilibili.com/25142156",
        )
        url_button(
            left,
            "小红书:",
            "一周不剩",
            "https://xhslink.com/m/6zzQ97wiPAI",
        )
        url_button(right, "飞书:", "飞书技术字典", enabled=False)
        url_button(
            right,
            "GitHub:",
            "Smart Align Nodes v0.4.2",
            "https://github.com/AnthemZhou/Smart_Align_Nodes",
        )

        settings = layout.box().column(align=True)
        settings.prop(self, "snap_distance")
        settings.prop(self, "vertical_gap")
        settings.prop(self, "equal_spacing")
        settings.prop(self, "show_guides")


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
