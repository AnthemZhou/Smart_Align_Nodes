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
    show_guides: bpy.props.BoolProperty(
        name="Show Guides",
        description="Draw alignment and spacing guides while moving nodes",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "snap_distance")
        layout.prop(self, "equal_spacing")
        layout.prop(self, "show_guides")


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
