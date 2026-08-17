from pathlib import Path

p = Path('tools/golden/editor-screens-core.py')
s = p.read_text(encoding='utf-8')
old = '''        "units": " && document.querySelector('[data-sprite-preview-animated=\\\"1\\\"]'"
                 " '[data-sprite-preview-ready=\\\"1\\\"]')",
'''
new = '''        "units": " && document.querySelector('[data-sprite-preview-animated=\\\"1\\\"][data-sprite-preview-ready=\\\"1\\\"]')",
'''
assert s.count(old) == 1, 'malformed Units predicate anchor drifted'
p.write_text(s.replace(old, new, 1), encoding='utf-8')

t = Path('tools/golden/test-g6-harness-boundaries.py')
s = t.read_text(encoding='utf-8')
old = '''assert "data-sprite-preview-animated" in g6 and "data-sprite-preview-ready" in g6
assert '"units":' in g6
'''
new = '''assert "data-sprite-preview-animated" in g6 and "data-sprite-preview-ready" in g6
assert r''' + "'''" + '''[data-sprite-preview-animated=\\"1\\"][data-sprite-preview-ready=\\"1\\"]''' + "'''" + ''' in g6
assert '"units":' in g6
'''
assert s.count(old) == 1, 'boundary predicate anchor drifted'
t.write_text(s.replace(old, new, 1), encoding='utf-8')
