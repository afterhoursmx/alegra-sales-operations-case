"""Regresiones de flujo mixto y dashboard gerencial."""
import ast
from pathlib import Path
from atencion import business_needs_from_history
ROOT=Path(__file__).resolve().parents[1]

def extract_function(name):
    module=ast.parse((ROOT/'app.py').read_text(encoding='utf-8'))
    fn=next(n for n in module.body if isinstance(n,ast.FunctionDef) and n.name==name)
    namespace={}
    exec(compile(ast.Module(body=[fn],type_ignores=[]),'app.py','exec'),namespace)
    return namespace[name]

def test_nombre_y_pos_en_el_mismo_mensaje():
    extract=extract_function('extract_declared_name')
    assert extract('Raul villanueva, tambien quiero poder tener un POS',True)=='Raul Villanueva'
    assert extract('Raúl Villanueva, también quiero un POS',True)=='Raúl Villanueva'
    history=[{'rol':'prospecto','texto':'Tengo una tienda de ropa y quiero facturar este mes'},
             {'rol':'prospecto','texto':'Raul villanueva, tambien quiero poder tener un POS'}]
    assert set(business_needs_from_history(history))=={'Facturación','Inventarios / ventas'}

def test_comparativo_gerencial_respeta_filtros():
    src=(ROOT/'manager_views.py').read_text(encoding='utf-8')
    assert "selected_manager=st.session_state.get('exe_manager','Todos')" in src
    assert "if selected_manager!='Todos' and mgr!=selected_manager:" in src
    assert 'country=selected_country,team=selected_team,seller=selected_seller' in src

def test_recuperacion_muestra_semaforo_por_registro():
    src=(ROOT/'crm_recovery_view.py').read_text(encoding='utf-8')
    assert "'Prioridad': ('🔴 Alta'" in src
    assert "st.markdown('#### Plan de mitigación')" not in src

def test_revenue_no_ofrece_consejo_vacio():
    src=(ROOT/'revenue_view.py').read_text(encoding='utf-8')
    assert 'Siguiente decisión: comparar la mezcla de productos' not in src
