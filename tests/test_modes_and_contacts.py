"""Variantes coloquiales de la elección de modalidad y captura de contacto."""
from test_conversation_acceptance import namespace


def run(messages):
    lead={'id':'L-977','nombre':'Prospecto sin identificar','pais':'México','correo':'','telefono':'','segmento':''}
    case={'lead_id':'L-977','mensajes':[],'facts':{},'asesor':'','reserva':''}
    cases={}
    def turn(s):
        namespace['process_turn'](case,cases,lead,s,'')
        return case['mensajes'][-1]['texto']
    for s in messages: turn(s)
    return case,turn


def test_yes_without_mode_asks_choice():
    case,turn=run(['Tengo una tienda y quiero facturar este mes','Juan Magan, juan@ejemplo.com'])
    msg=turn('si esta bien')
    assert 'videollamada o llamada telefónica' in msg.lower(),msg
    assert not case.get('modalidad_cita')


def test_call_alone_uses_existing_phone():
    case,turn=run(['Tengo una tienda y quiero facturar este mes','Juan Magan, 4771134566'])
    msg=turn('llamada')
    assert case.get('modalidad_cita')=='Llamada telefónica'
    assert 'espacios disponibles' in msg,msg


def test_video_email_missing_asks_email():
    case,turn=run(['Tengo una tienda y quiero facturar este mes','Juan Magan, 4771134566'])
    msg=turn('videollamada')
    assert case.get('modalidad_cita')=='Videollamada'
    assert 'correo' in msg.lower(),msg
    msg=turn('juan@example.com')
    assert 'espacios disponibles' in msg,msg


def test_video_existing_email_shows_slots():
    case,turn=run(['Tengo una tienda y quiero facturar este mes','Juan Magan, juan@example.com'])
    msg=turn('mejor una videollamada')
    assert case.get('modalidad_cita')=='Videollamada'
    assert 'espacios disponibles' in msg,msg


def test_mention_call_in_negative_not_accepted():
    case,turn=run(['Tengo una tienda y quiero facturar este mes','Juan Magan, juan@example.com'])
    turn('no quiero llamada')
    assert not case.get('modalidad_cita')
