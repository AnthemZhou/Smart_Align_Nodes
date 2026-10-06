"""Catch untranslated UI labels/tooltips and format placeholder mismatches."""
import ast
from pathlib import Path
from string import Formatter
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'smart_align_nodes'
TRANSLATIONS = ast.parse((ROOT / 'translations.py').read_text())
ZH = next(ast.literal_eval(n.value) for n in TRANSLATIONS.body
          if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_ZH' for t in n.targets))


class TranslationCoverageTests(unittest.TestCase):
    def test_all_visible_labels_descriptions_and_reports_have_chinese(self):
        # Product/author names and Blender's built-in keymap name are stable IDs.
        names = {'smart_align_nodes', 'Smart Align Nodes', 'Smart Align', 'Node Editor',
                 'GitHub: Smart Align Nodes v1.0.1'}
        for filename in ('preferences.py', 'ui.py', 'operators.py', 'layout_operator.py'):
            for n in ast.walk(ast.parse((ROOT / filename).read_text())):
                value = None
                if isinstance(n, ast.keyword) and n.arg in {'text', 'name', 'description'}:
                    value = n.value
                elif isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {'bl_label', 'bl_description'} for t in n.targets):
                    value = n.value
                elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'translate':
                    value = n.args[0]
                if isinstance(value, ast.Constant) and isinstance(value.value, str) and value.value not in names:
                    self.assertIn(value.value, ZH, (filename, value.value))

    def test_translated_messages_preserve_format_fields(self):
        def fields(text):
            return {field for _, field, _, _ in Formatter().parse(text) if field is not None}
        for source, target in ZH.items():
            self.assertTrue(target)
            self.assertEqual(fields(source), fields(target), source)


if __name__ == '__main__':
    unittest.main()
