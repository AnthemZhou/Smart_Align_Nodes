"""Render both preference languages and verify registered UI/report translations."""
import json
from pathlib import Path
import sys
import traceback
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import smart_align_nodes
smart_align_nodes.register()
from smart_align_nodes.translations import _ZH, translate

addon = bpy.context.preferences.addons.new(); addon.module = 'smart_align_nodes'
bpy.context.preferences.view.show_splash = False
bpy.context.preferences.view.use_translate_interface = True
bpy.context.preferences.view.use_translate_tooltips = True
bpy.context.preferences.use_preferences_save = False
area = next(a for a in bpy.context.screen.areas if a.type == 'VIEW_3D')
area.type = 'PREFERENCES'
bpy.ops.preferences.addon_show(module='smart_align_nodes')
state = {'phase': 0}
results = []
output = Path('/private/tmp/san_preferences_localization_results.json')


def tick():
    try:
        with bpy.context.temp_override(window=bpy.context.window, area=area,
                                      region=next(r for r in area.regions if r.type == 'WINDOW')):
            phase = state['phase']
            if phase in (0, 2):
                bpy.context.preferences.view.language = 'en_US' if phase == 0 else 'zh_HANS'
                # Blender may toggle these when changing the locale.
                bpy.context.preferences.view.use_translate_interface = True
                bpy.context.preferences.view.use_translate_tooltips = True
                area.type = 'CONSOLE'
                area.type = 'PREFERENCES'
                bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)
                area.tag_redraw(); state['phase'] += 1; return .5
            lang = 'en_US' if phase == 1 else 'zh_HANS'
            for source, target in _ZH.items():
                def check(actual):
                    # Blender's own catalog takes precedence for shared phrases
                    # such as Remove on Cancel. Accept its Chinese wording too.
                    assert (actual == source if lang == 'en_US' else
                            actual != source and any('\u4e00' <= c <= '\u9fff' for c in actual)), (lang, source, actual)
                for context in ('*', 'Operator'):
                    actual = bpy.app.translations.pgettext_iface(source, context)
                    check(actual)
                check(bpy.app.translations.pgettext_tip(source))
            assert translate('Node geometry is not ready: Example') == (
                'Node geometry is not ready: Example' if lang == 'en_US' else '以下节点的几何信息尚未就绪：Example')
            bpy.ops.screen.screenshot(filepath=f'/private/tmp/san_preferences_{lang}.png')
            results.append({'language': lang, 'messages': len(_ZH), 'interface_operator_tooltip': True})
            if phase == 1:
                state['phase'] = 2; return .2
            output.write_text(json.dumps(results, indent=2))
            print('SAN_LOCALIZATION_PASS', flush=True); bpy.ops.wm.quit_blender(); return None
    except Exception:
        results.append({'failure': traceback.format_exc()}); output.write_text(json.dumps(results, indent=2))
        traceback.print_exc(); bpy.ops.wm.quit_blender(); return None


bpy.app.timers.register(tick, first_interval=1.5)
