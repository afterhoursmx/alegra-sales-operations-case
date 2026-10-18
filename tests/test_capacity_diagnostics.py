import pytest
from route_analytics import capacity_diagnostics

def test_capacity():
    d=capacity_diagnostics(ai_opportunities=200,advisor_opportunities=400,ai_won=40,advisor_won=80,scheduled_meetings=120,advisor_count=5,meetings_capacity_per_advisor=20)
    assert d['ai_conversion']==.2
    assert d['advisor_conversion']==.2
    assert d['over_capacity']==20
    assert d['ai_share']==pytest.approx(1/3)

def test_no_denominator():
    d=capacity_diagnostics(ai_opportunities=0,advisor_opportunities=0,ai_won=0,advisor_won=0,scheduled_meetings=0,advisor_count=0,meetings_capacity_per_advisor=0)
    assert d['occupancy'] is None
    assert d['ai_share'] is None

def test_invalid_data():
    with pytest.raises(ValueError):
        capacity_diagnostics(ai_opportunities=2,advisor_opportunities=0,ai_won=3,advisor_won=0,scheduled_meetings=0,advisor_count=0,meetings_capacity_per_advisor=0)
