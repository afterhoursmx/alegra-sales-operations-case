import pytest
from route_analytics import summarize_routes, route_alerts

def test_routes_no_double_counting():
    data={'Anterior':{'AI':20,'Con asesor':60},'Actual':{'AI':42,'Con asesor':68}}
    both=summarize_routes(data,'Todos',400)
    ai=summarize_routes(data,'AI',400)
    advisor=summarize_routes(data,'Con asesor',400)
    assert both['Actual']['cierres']==110
    assert ai['Actual']['cierres']==42
    assert advisor['Actual']['cierres']==68
    assert both['Actual']['mrr']==ai['Actual']['mrr']+advisor['Actual']['mrr']

def test_comparison_deltas():
    data={'Anterior':{'AI':20,'Con asesor':60},'Actual':{'AI':42,'Con asesor':68}}
    totals=summarize_routes(data,'Todos',400)
    assert totals['Actual']['mrr']-totals['Anterior']['mrr']==12000

def test_alerts_actionable():
    a=route_alerts(reply_on_time=.97,unhandled=1,failed_handoffs=2,pending_results=4,ai_won=0,advisor_won=8)
    assert len(a)>=4
    assert all(action for _,action in a)

def test_invalid_route():
    with pytest.raises(ValueError):summarize_routes({'Actual':{}},'cualquiera',400)
