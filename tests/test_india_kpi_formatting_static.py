"""Static validation of page removal and navigation references, without Streamlit dependency."""
import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_navigation_replacement():
    app = (ROOT / 'app.py').read_text()
    assert "'USA Company Financial KPI Intelligence'" in app
    assert "'India Company Financial KPI Intelligence'" in app
    assert "'India Company Financial KPIs'" not in app


def test_old_page_removed_but_sector_analysis_retained():
    tree = ast.parse((ROOT / 'india_financial_ui.py').read_text())
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert 'render_india_company_kpis' not in functions
    assert 'render_india_sector_factor_financials' in functions
    assert 'render_india_kpi_intelligence' in {
        node.name for node in ast.parse((ROOT / 'india_kpi_intelligence.py').read_text()).body
        if isinstance(node, ast.FunctionDef)
    }


def test_all_drilldown_routes_updated():
    for filename in ['india_rankings_ui.py', 'india_constituents_ui.py', 'india_financial_ui.py']:
        assert "selected_page = 'India Company Financial KPIs'" not in (ROOT / filename).read_text()

if __name__ == '__main__':
    test_navigation_replacement()
    test_old_page_removed_but_sector_analysis_retained()
    test_all_drilldown_routes_updated()
    print('3 static regression tests passed')
