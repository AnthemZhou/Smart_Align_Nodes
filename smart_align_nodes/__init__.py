import importlib
import sys


bl_info = {
    "name": "Smart Align Nodes",
    "author": "Anthem_周圣宇",
    "version": (1, 0, 1),
    "blender": (4, 0, 0),
    "location": "Node Editor > Sidebar > Smart Align",
    "description": "智能排列与吸附 / Smart node layout and snapping",
    "category": "Node",
}


MODULE_NAMES = (
    "translations",
    "context",
    "debug",
    "geometry",
    "snapping",
    "preferences",
    "layout",
    "layout_routing",
    "layout_route_adapter",
    "layout_adapter",
    "layout_operator",
    "operators",
    "ui",
)


def _load_modules(reload_existing):
    modules = {}
    for name in MODULE_NAMES:
        qualified_name = f"{__package__}.{name}"
        if qualified_name in sys.modules:
            module = sys.modules[qualified_name]
            if reload_existing:
                module = importlib.reload(module)
        else:
            module = importlib.import_module(qualified_name)
        modules[name] = module
    return modules


def register():
    modules = _load_modules(reload_existing=True)
    modules["translations"].register()
    modules["preferences"].register()
    modules["operators"].register()
    modules["ui"].register()


def unregister():
    modules = _load_modules(reload_existing=False)
    modules["ui"].unregister()
    modules["operators"].unregister()
    modules["preferences"].unregister()
    modules["translations"].unregister()
