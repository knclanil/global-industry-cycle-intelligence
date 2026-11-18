"""Lightweight checks that work even without optional Streamlit dependencies."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_galaxy_builder_and_layout_are_present():
    tree = ast.parse((ROOT / 'capital_network.py').read_text())
    funcs = {n.name for n in tree.body if isinstance(n, ast.FunctionDef)}
    assert {'build_unified_graph', 'galaxy_layout', 'make_figure'} <= funcs

def test_global_layers_are_requested():
    src = (ROOT / 'capital_network.py').read_text()
    assert "requested=['Countries','Global Assets','Global Factors'" in src
    assert "add(node(fg,'FACTORS','factor_group'),aid)" in src
    assert "group='global:assets'" in src
