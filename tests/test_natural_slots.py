from datetime import datetime
from atencion import requested_demo_slot, advisor_reply

SLOTS=['2026-10-19T10:00:00-06:00','2026-10-19T12:30:00-06:00','2026-10-19T14:00:00-06:00','2026-10-19T16:00:00-06:00']

def test_time_only_as_colloquial():
    for message in ['a las 1230','12:30','a las 12:30','1230','lunes a las 12:30']:
        slot,asked=requested_demo_slot(message,SLOTS)
        assert asked and slot==SLOTS[1], (message,slot)

def test_no_telephone_as_time():
    assert requested_demo_slot('4771134566',SLOTS)==(None,False)

def test_time_not_offered_is_not_accepted():
    assert requested_demo_slot('13:45',SLOTS)==(None,True)


def test_4pm_with_monday():
    for message in ['lunes a las 4', 'lunes a las 4pm', 'lunes a las 4 pm', 'lunes a las 16:00', 'a las 4 de la tarde']:
        slot,asked=requested_demo_slot(message,SLOTS)
        assert asked and slot==SLOTS[3], (message,slot)

def test_am_pm_and_literal_slot_priority():
    slots=['2026-10-19T04:00:00-06:00','2026-10-19T16:00:00-06:00']
    assert requested_demo_slot('lunes a las 4am',slots)[0]==slots[0]
    assert requested_demo_slot('lunes a las 4',slots)[0]==slots[0]
    assert requested_demo_slot('lunes a las 4pm',slots)[0]==slots[1]


def test_weekday_with_hour_without_a_las():
    for message in ['lunes 4pm', 'lunes 4 pm', 'lunes 4', 'el lunes 4pm', 'lunes 16:00']:
        slot,asked=requested_demo_slot(message,SLOTS)
        assert asked and slot==SLOTS[3], (message,slot)

def test_weekday_with_time_does_not_infer_wrong_day():
    assert requested_demo_slot('martes 4pm',SLOTS)==(None,True)

def test_weekday_other_text_is_not_time():
    assert requested_demo_slot('lunes me interesa facturar',SLOTS)==(None,False)
