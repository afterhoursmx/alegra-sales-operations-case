import pytest
from revenue_model import revenue_scenarios

def test_baseline_identical_yields_zero_incremental():
    x=revenue_scenarios(base_reach=.15,pilot_reach=.15,pilot_mql_to_sql=.34)
    assert x['incremental_mrr_total']==pytest.approx(0)

def test_two_streams_no_historical_14000_assumption():
    x=revenue_scenarios(historical_candidates=1000,base_reach=.05,pilot_reach=.15,historical_to_sql=.30,historical_sql_to_won=.21,mql_share=.70,pilot_mql_to_sql=.42,new_sql_to_won=.21,monthly_value=432)
    assert x['historical']['incremental_wins']==pytest.approx(6.3)
    assert x['inbound']['incremental_wins']==pytest.approx(164.64)
    assert x['incremental_mrr_total']==pytest.approx((6.3+164.64)*432)

def test_not_all_monthly_leads_mql():
    x=revenue_scenarios(mql_share=.5)
    assert x['inbound']['mql']==7000

def test_negative_improvement_shows_negative_impact():
    x=revenue_scenarios(base_reach=.2,pilot_reach=.05,pilot_mql_to_sql=.30)
    assert x['incremental_mrr_total']<0

def test_invalid_rates_rejected():
    with pytest.raises(ValueError): revenue_scenarios(pilot_reach=1.2)

from revenue_model import trajectory_scenarios

def test_trajectory_one_country_and_no_double_count_historical():
    rows=[{'country':'México','segment':'PyME','new_leads':4900,'mql_share':.7,'historical_candidates':350,'arpa_local':400},
          {'country':'Colombia','segment':'PyME','new_leads':4200,'mql_share':.7,'historical_candidates':300,'arpa_local':60000}]
    result=trajectory_scenarios(rows)
    assert [r['month'] for r in result]==[3,6,12]
    assert result[-1]['incremental_run_rate_mrr']>result[0]['incremental_run_rate_mrr']
    assert result[0]['historical_incremental_mrr']==pytest.approx(350*(.10-.05)*.30*.21*400)
    assert result[-1]['inbound_accumulated_mrr']>result[-1]['inbound_cohort_incremental_mrr']

def test_trajectory_rejects_invalid_checkpoints():
    with pytest.raises(ValueError):
        trajectory_scenarios([],checkpoints={0:{'reach':.05,'mql_sql':.34},3:{'reach':2,'mql_sql':.37},6:{'reach':.1,'mql_sql':.4},12:{'reach':.2,'mql_sql':.43}})
