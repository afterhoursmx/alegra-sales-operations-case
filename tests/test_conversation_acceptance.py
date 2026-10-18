"""Regression: accepting advisor offered by bot must not repeat the plan forever."""
import ast
from pathlib import Path
import re
import datetime
import atencion, engine, contactos

source=ast.parse((Path(__file__).resolve().parents[1]/'app.py').read_text())
functions={n.name:n for n in source.body if isinstance(n,ast.FunctionDef)}
namespace={'__builtins__':__builtins__, 'text_facts':engine.text_facts,'extract_contact':contactos.extract_contact,
           'deduplicate':contactos.deduplicate,'conservative_enrichment':contactos.conservative_enrichment,
           'gemini_reply':atencion.gemini_reply,'deterministic_fallback':atencion.deterministic_fallback,
           'route_case':atencion.route_case,'demo_slots':atencion.demo_slots,'human_declined':atencion.human_declined,
           'explicit_human_request':atencion.explicit_human_request,'business_needs_from_history':atencion.business_needs_from_history,
           'conversation_stage':atencion.conversation_stage,'grounded_recommendation':atencion.grounded_recommendation,
           'contact_confirmation':atencion.contact_confirmation,'appointment_preference':atencion.appointment_preference,
           'requested_demo_slot':atencion.requested_demo_slot,'advisor_reply':atencion.advisor_reply,
           'known_leads':lambda:[],'__name__':'app_isolated'}
code=compile(ast.Module(body=[functions[n] for n in ('sync_contact','extract_declared_name','has_known_name','request_contact_reply','process_turn')],type_ignores=[]),'app_isolated','exec')
exec(code,namespace)

def test_yes_call_phone_and_booking():
    proc=namespace['process_turn']; lead={'id':'L-900','nombre':'Prospecto sin identificar','pais':'México','correo':'','telefono':'','segmento':''}
    case={'lead_id':'L-900','mensajes':[],'facts':{},'asesor':'','reserva':''}
    cases={}
    def turn(text):
        proc(case,cases,lead,text,'')
        return case['mensajes'][-1]['texto']
    assert 'con quién' in turn('Hola tengo una tienda de ropa quiero facturar este mes')
    assert 'Una opción para ti' in turn('Jorge Ramos, ramos57@example.com')
    txt=turn('si por llamada esta bien')
    assert 'teléfono' in txt.lower(),txt
    assert case['facts']['asistencia']=='Sí'
    txt=turn('477 155 6734')
    assert 'espacios disponibles' in txt,txt
    d=datetime.datetime.fromisoformat(atencion.demo_slots('México')[0]);
    phrase=['lunes','martes','miércoles','jueves','viernes','sábado','domingo'][d.weekday()] + f' a las {d.hour}:00'
    # choose exact slot including minutes
    if d.minute:phrase=['lunes','martes','miércoles','jueves','viernes','sábado','domingo'][d.weekday()] + f' a las {d.hour}:{d.minute:02d}'
    txt=turn(phrase)
    assert '¿Confirmamos' in txt,txt
    txt=turn('sí')
    assert 'Tu cita quedó registrada' in txt,txt
    assert case.get('reserva')


def test_acceptance_does_not_require_exact_phrase():
    proc=namespace['process_turn']
    lead={'id':'L-999','nombre':'Prospecto sin identificar','pais':'México','correo':'','telefono':'','segmento':''}
    case={'lead_id':'L-999','mensajes':[],'facts':{},'asesor':'','reserva':''}
    cases={}
    def turn(msg):
        proc(case,cases,lead,msg,'')
        return case['mensajes'][-1]['texto']
    turn('Tengo una tienda de ropa y quiero empezar a facturar este mes')
    turn('Juan Magan, 4771134566')
    turn('desde cero')
    txt=turn('si por llamada esta bien')
    assert case.get('solicitud_asesoria') is True
    assert case.get('modalidad_cita')=='Llamada telefónica'
    assert 'espacios disponibles' in txt or '¿Prefieres' in txt, txt
    assert 'Una opción para ti' not in txt, txt
