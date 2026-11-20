"""Run with pytest after installing the repository's requirements."""
import sys
import types
from pathlib import Path
import importlib.util
import pandas as pd

# Permit exercising pure graph logic without Streamlit installed locally.
try:
    import streamlit  # noqa
except ImportError:
    stub = types.ModuleType("streamlit")
    stub.cache_data = lambda **kwargs: (lambda func: func)
    sys.modules["streamlit"] = stub

spec = importlib.util.spec_from_file_location("cap_tested", Path(__file__).parent / "capital_network.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_memberships_and_country_scope(tmp_path):
    p = tmp_path
    for region in ("usa", "india", "global"):
        pd.DataFrame([
            dict(source_id="S1", kind="sector", label="Technology", quadrant="Leading"),
            dict(source_id="F1", kind="factor", label="Quality", quadrant="Weakening"),
        ]).to_csv(p / f"{region}_3m_signals.csv", index=False)
        pd.DataFrame([
            dict(source_id="S1", kind="sector", company_key="AAA", Company="Alpha", Ticker="AAA"),
            dict(source_id="F1", kind="factor", company_key="AAA", Company="Alpha", Ticker="AAA"),
        ]).to_csv(p / f"{region}_3m_edges.csv", index=False)
    nodes, edges, info = mod._graph_data("3m", p)
    assert ("root", "country:USA") in edges
    assert ("country:USA", "USA:sector:S1") in edges
    assert ("USA:sector:S1", "USA:company:AAA") in edges
    assert ("USA:company:AAA", "USA:factor:F1") in edges
    assert "country:Global" not in nodes
    assert ("root", "Global:sector:S1") in edges
    assert ("root", "Global:company:AAA") in edges
    assert ("root", "Global:factor:F1") in edges
    assert ("Global:sector:S1", "Global:company:AAA") in edges
    assert ("Global:company:AAA", "Global:factor:F1") in edges
    assert ("country:India", "India:sector:S1") in edges
    assert info["USA"]["memberships"] == 2
    selected, selected_edges, matches, total = mod._select(
        nodes, edges, chosen_countries=["USA"], chosen_rotations=["Leading"],
        match="All selected", limit=None)
    assert matches == {"USA:company:AAA"}
    assert total == 1
    selected, selected_edges, matches, total = mod._select(
        nodes, edges, chosen_sectors=["USA:sector:S1"],
        chosen_factors=["India:factor:F1"], match="All selected", limit=None)
    assert not matches


def test_empty_cache(tmp_path):
    nodes, edges, info = mod._graph_data("1m", tmp_path)
    assert nodes == {"root": {"label": "GLOBAL", "kind": "root", "country": None}}
    assert edges == []


def test_render_figure(tmp_path):
    pd.DataFrame([dict(source_id="S1", kind="sector", label="Tech", quadrant="Leading")]).to_csv(tmp_path / "usa_3m_signals.csv", index=False)
    pd.DataFrame([dict(source_id="S1", kind="sector", company_key="C", Company="Corp", Ticker="C")]).to_csv(tmp_path / "usa_3m_edges.csv", index=False)
    nodes, edges, _ = mod._graph_data("3m", tmp_path)
    visible, filtered, matched, count = mod._select(nodes, edges)
    fig = mod._plot(nodes, filtered, matched, visible)
    assert len(fig.data) > 0
    assert count == 1


def test_global_signals_without_company_memberships(tmp_path):
    pd.DataFrame([
        dict(source_id="S2", kind="sector", label="Industrials", quadrant="Improving"),
        dict(source_id="F2", kind="factor", label="Value", quadrant="Lagging"),
    ]).to_csv(tmp_path / "global_1m_signals.csv", index=False)
    nodes, edges, _ = mod._graph_data("1m", tmp_path)
    assert ("root", "Global:sector:S2") in edges
    assert ("root", "Global:factor:F2") in edges
    visible, graph_edges, companies, _ = mod._select(nodes, edges)
    assert ("root", "Global:sector:S2") in graph_edges
    assert ("root", "Global:factor:F2") in graph_edges
    assert not companies
