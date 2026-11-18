import ast
from pathlib import Path


def test_group_order_and_all_pages():
    source = Path(__file__).resolve().parents[1].joinpath('app.py').read_text()
    tree = ast.parse(source)
    assignment = next(node for node in tree.body if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'NAV_GROUPS' for t in node.targets))
    groups = ast.literal_eval(assignment.value)
    assert list(groups) == ['🌐 GLOBAL INTELLIGENCE',
        '🌎 COUNTRY ANALYSIS', '💰 ASSET CLASS ANALYSIS',
        '📊 SECTOR ANALYSIS', '🧩 FACTOR ANALYSIS', '📚 DATA & RESEARCH'
    ]
    pages = [page for items in groups.values() for page in items]
    assert len(pages) == len(set(pages)) == 15
    assert 'Factor Holdings Comparison' in pages
    assert pages[-2:] == ['Data Table', 'Wiki']
