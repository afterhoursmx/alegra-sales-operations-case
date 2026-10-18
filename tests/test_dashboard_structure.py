from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_navigation_order_and_ai_last():
    src=(ROOT/'app.py').read_text(encoding='utf-8')
    line=next(x for x in src.splitlines() if x.startswith("st.segmented_control('Vista'"))
    assert line.index("'Overview gerencial'") < line.index("'Impacto en revenue'") < line.index("'Atención comercial con IA'")

def test_operational_revenue_no_roadmap():
    src=(ROOT/'revenue_view.py').read_text(encoding='utf-8')
    assert 'Revenue comercial' in src
    assert 'Resultado del mes' in src
    assert 'Alertas y próximas decisiones' in src
    assert 'Proyección ilustrativa de impacto · 3, 6 y 12 meses' not in src

def test_three_manager_comparison():
    src=(ROOT/'manager_views.py').read_text(encoding='utf-8')
    assert 'Comparativo de Sales Managers · misma vista' in src
