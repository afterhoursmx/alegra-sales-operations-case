import pytest
from revenue_model import decision_forecast

ROWS=[{'country':'México','segment':'PyME','new_leads':1000,'mql_share':.7,'historical_candidates':100,'arpa_local':400},
      {'country':'Colombia','segment':'PyME','new_leads':1000,'mql_share':.7,'historical_candidates':100,'arpa_local':100000}]


def test_no_change_means_no_incremental_revenue():
    cp={m:{'mql_lift_pp':0,'reach':.05,'no_response':.38,'crm_complete':.61} for m in (0,3,6,12)}
    out=decision_forecast(ROWS,checkpoints=cp)
    assert all(x['incremental_mrr']==pytest.approx(0) for x in out)


def test_immediate_ai_response_does_not_create_revenue_by_itself():
    cp={m:{'mql_lift_pp':0,'reach':.05,'no_response':.38,'crm_complete':.61} for m in (0,3,6,12)}
    out=decision_forecast(ROWS,checkpoints=cp)
    assert all(x['ai_response_minutes'] == pytest.approx(1.0) for x in out)
    assert all(x['hours'] == pytest.approx(5.2) for x in out)
    assert all(x['incremental_mrr']==pytest.approx(0) for x in out)


def test_historical_cohort_not_repeated_monthly():
    cp={m:{'mql_lift_pp':0,'reach':.15 if m else .05,'no_response':.38,'crm_complete':.61} for m in (0,3,6,12)}
    out=decision_forecast(ROWS,checkpoints=cp)
    assert out[2]['incremental_mrr']==pytest.approx(out[-1]['incremental_mrr'])
    assert out[-1]['historical_incremental_mrr']==pytest.approx(100*.10*.3*.21*400)


def test_country_separate_currency_not_mixed():
    out=decision_forecast(ROWS)
    out_col=decision_forecast(ROWS,country='Colombia')
    assert out[-1]['incremental_mrr']>0
    assert out_col[-1]['incremental_mrr']>out[-1]['incremental_mrr']


def test_reject_invalid_checkpoint():
    cp={m:{'mql_lift_pp':0,'reach':1.2,'no_response':.38,'crm_complete':.61} for m in (0,3,6,12)}
    with pytest.raises(ValueError): decision_forecast(ROWS,checkpoints=cp)
