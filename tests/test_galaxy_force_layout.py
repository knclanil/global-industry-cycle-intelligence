import ast
from pathlib import Path

def test_force_layout_is_seeded_and_collision_aware():
    source = Path(__file__).resolve().parents[1].joinpath('capital_network.py').read_text()
    tree = ast.parse(source)
    func = next(x for x in tree.body if isinstance(x, ast.FunctionDef) and x.name == 'galaxy_layout')
    body = ast.get_source_segment(source, func)
    assert 'nx.spring_layout' in body
    assert 'seed=29' in body
    assert 'gap-dist' in body
    assert "'global:assets'" in body

def test_no_path_selection_in_network_page():
    source = Path(__file__).resolve().parents[1].joinpath('capital_network.py').read_text()
    render = source.split('def render_capital_network():',1)[1]
    assert 'Exploration Path' not in render
    assert 'RELATIVE TIME' in render
    assert 'FROM DATE → TO DATE' in render
