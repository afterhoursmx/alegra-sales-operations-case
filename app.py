"""Alegra Smart Lead Intelligence - synthetic demo / not an official Alegra product."""
import csv
import json
import os
import tempfile
import urllib.request
import urllib.error
from pathlib import Path
from manager_views import operational, executive

import streamlit as st
from engine import assess, text_facts
from contactos import extract_contact, deduplicate, conservative_enrichment
from atencion import gemini_reply, deterministic_fallback, route_case, demo_slots, DEMO_KNOWLEDGE, human_declined, explicit_human_request, business_needs_from_history, conversation_stage, grounded_recommendation, contact_confirmation, appointment_preference, requested_demo_slot, advisor_reply

ROOT = Path(__file__).parent
st.set_page_config(page_title='Smart Lead Intelligence | Prototipo Alegra', page_icon='📊', layout='wide')
st.markdown('''<style>
.block-container{padding-top:1.4rem;max-width:1250px}h1,h2,h3{color:#192a47}div[data-testid="stMetric"]{border:1px solid #e0e8f0;padding:14px;border-radius:12px;background:#f8fbff}
.smalltext{color:#667487;font-size:13px}.apphead{border-bottom:3px solid #19a9dd;padding-bottom:12px;margin-bottom:20px}
.al-kpi{padding:13px 14px;border:1px solid #dce6ed;border-radius:12px;background:#f6fafc;min-height:92px}
.al-kpi span{display:block;font-size:12px;color:#52667d}.al-kpi strong{display:block;font-size:29px;color:#10294d;margin-top:8px}
.al-kpi.positive{border-left:5px solid #008f49}.al-kpi.positive strong{color:#008f49}
.al-kpi.negative{border-left:5px solid #de3346}.al-kpi.negative strong{color:#de3346}
.al-kpi.warning{border-left:5px solid #e1a400}.al-kpi.warning strong{color:#ac7800}
</style>''',unsafe_allow_html=True)

@st.cache_data
def load_leads():
    with open(ROOT/'data'/'leads.csv',encoding='utf-8',newline='') as f: return list(csv.DictReader(f))


# Almacenamiento LOCAL para leads de prueba. No guardar claves ni datos reales.
SAVED_LEADS = ROOT / 'data' / 'leads_manuales.json'
SAVED_CASES = ROOT / 'data' / 'conversaciones_demo.json'
SAVED_UPDATES = ROOT / 'data' / 'enriquecimientos_crm_demo.json'

def load_saved_leads():
    """El disco es la fuente de verdad, incluso tras cerrar Chrome o Streamlit."""
    if not SAVED_LEADS.exists():
        return []
    try:
        with SAVED_LEADS.open('r', encoding='utf-8') as handle:
            records = json.load(handle)
        if not isinstance(records, list) or not all(isinstance(v, dict) for v in records):
            raise ValueError('Estructura de leads incorrecta')
        return records
    except (OSError, ValueError) as exc:
        raise RuntimeError(f'No se pudo leer {SAVED_LEADS.name}. No sobrescribas el archivo: {exc}') from exc

def save_saved_leads(records):
    """Escritura atómica para evitar archivos JSON a medio guardar."""
    SAVED_LEADS.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=SAVED_LEADS.parent,
                                         suffix='.tmp', delete=False) as handle:
            tmp_path = Path(handle.name)
            json.dump(records, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(tmp_path, SAVED_LEADS)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()

def next_manual_id(records):
    nums = [int(m.group(1)) for r in records
            if (m := __import__('re').fullmatch(r'L-(\d+)', str(r.get('id', ''))))]
    return f'L-{max([100] + nums) + 1}'

def load_cases():
    if not SAVED_CASES.exists():
        return {}
    try:
        with SAVED_CASES.open('r', encoding='utf-8') as handle:
            value = json.load(handle)
        if not isinstance(value, dict):
            raise ValueError('El registro debe ser un objeto')
        return value
    except (OSError, ValueError) as exc:
        raise RuntimeError(f'Error leyendo {SAVED_CASES.name}; no sobrescribas el archivo: {exc}') from exc


def save_cases(cases):
    SAVED_CASES.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=SAVED_CASES.parent,
                                         suffix='.tmp', delete=False) as handle:
            tmp_path = Path(handle.name)
            json.dump(cases, handle, ensure_ascii=False, indent=2)
            handle.write('\n')
        os.replace(tmp_path, SAVED_CASES)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink()


def sync_contact(case, new_message, all_known, lead):
    """CRM is simulated; create a verified record only after deduplication."""
    extracted=extract_contact(new_message)
    if extracted['correo']:
        case['correo_preferido']=extracted['correo']
        case['canal_contacto_preferido']='Correo'
    if extracted['telefono']:
        case['telefono_preferido']=extracted['telefono']
        if not case.get('canal_contacto_preferido'):
            case['canal_contacto_preferido']='Teléfono (sin canal de envío confirmado)'
    email=case.get('correo_preferido','') or lead.get('correo','')
    phone=case.get('telefono_preferido','') or lead.get('telefono','')
    if not email and not phone:
        case['identificacion']='Contacto por solicitar'
        case['crm_resultado']='Pre-registro; no se crea contacto en CRM.'
        return case
    outcome=deduplicate(email,phone,lead.get('pais',''),all_known,exclude_id=case['lead_id'])
    case['crm_resultado']=outcome['estado']
    case['identificacion']='Verificada para simulación' if outcome['estado'] in ('nuevo','existente') else 'Revisión humana de coincidencia'
    case['crm_vinculado']=outcome['matches'][0]['id'] if outcome['estado']=='existente' else ''
    case['crm_coincidencias']=[x['id'] for x in outcome['matches']]
    if outcome.get('razon'): case['crm_razon']=outcome['razon']
    return case


def extract_declared_name(message, awaiting_name=False):
    """Extrae un nombre explícito o una respuesta breve a «¿con quién tengo el gusto?»."""
    import re
    text = (message or '').strip().strip('.,!¡?¿')
    word = r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+'
    match = re.search(r'\b(?:me llamo|mi nombre es|soy)\s+(' + word + r'(?:\s+' + word + r'){0,2})', text, re.I)
    if match:
        value = match.group(1)
    elif awaiting_name:
        # Puede contestar nombre y teléfono/correo en un solo mensaje.
        # El número se procesa por separado mediante extract_contact; nunca se guarda como nombre.
        cleaned = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', ' ', text)
        cleaned = re.sub(r'(?<!\w)(?:\+?\d[\d\s().-]{8,}\d)(?!\w)', ' ', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' ,;.-')
        if re.fullmatch(word + r'(?:\s+' + word + r'){0,2}', cleaned):
            value = cleaned
        else:
            return ''
    else:
        return ''
    stop = {'si','sí','no','hola','gracias','correo','telefono','teléfono',
            'whatsapp','whats','mañana','hoy','facturacion','facturación',
            'asesor','ayuda','quiero','necesito','prefiero','tengo','tortilleria',
            'tortillería','ferreteria','ferretería','pasteleria','pastelería',
            'facturar','informacion','información','listo','ok','vale'}
    words = value.split()
    if any(w.casefold() in stop for w in words):
        return ''
    return ' '.join(w[0].upper() + w[1:] for w in words)


def has_known_name(case, lead):
    value = (case.get('nombre_prospecto') or lead.get('nombre') or '').strip().casefold()
    return bool(value and value not in ('prospecto sin identificar', 'prospecto ficticio', 'nueva oportunidad', 'sin nombre'))


def request_contact_reply(case, lead):
    needs=', '.join(case.get('necesidades_detectadas',[])) or 'lo que necesitas'
    greeting = ('¡Hola, ' + case['nombre_prospecto'].split()[0] + '! Mucho gusto.') if case.get('nombre_prospecto') else '¡Hola!'
    intro = greeting + ' Claro, con gusto te ayudo con ' + needs.lower() + '.'
    if not has_known_name(case,lead):
        return (intro + ' Primero, ¿con quién tengo el gusto? '
                '¿Me compartes también un correo o número de WhatsApp para enviarte la información y dar seguimiento?')
    return (intro + ' ¿Me compartes un correo o número de WhatsApp '
            'para enviarte la información y dar seguimiento?')


def load_crm_updates():
    if not SAVED_UPDATES.exists(): return {}
    with SAVED_UPDATES.open('r',encoding='utf-8') as f: value=json.load(f)
    if not isinstance(value,dict): raise ValueError('Actualizaciones CRM simuladas inválidas')
    return value


def save_crm_updates(data):
    SAVED_UPDATES.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile('w',encoding='utf-8',dir=SAVED_UPDATES.parent,suffix='.tmp',delete=False) as f:
        tmp=Path(f.name)
        json.dump(data,f,indent=2,ensure_ascii=False)
    os.replace(tmp,SAVED_UPDATES)


def known_leads():
    updates=load_crm_updates()
    return [{**row,**updates.get(row['id'],{})} for row in load_leads()] + load_saved_leads()

def process_turn(case, cases, lead, text, key):
    """Local simulation: append prospect, ask Gemini once, route, persist separately."""
    case['mensajes'].append({'rol':'prospecto','texto':text})
    from engine import text_facts
    fallback = text_facts(' '.join(m['texto'] for m in case['mensajes'] if m['rol']=='prospecto'))
    # Migración y urgencia por sí mismas NO solicitan contacto humano.
    if not any(explicit_human_request(m['texto']) for m in case['mensajes'] if m['rol']=='prospecto'):
        fallback['asistencia']='No declarada'
    if human_declined(text):
        fallback['asistencia']='No declarada'
    import re as _re
    if _re.search(r'\b(?:no me contacten|no me escriban|no me llamen|no quiero que me contacten|no vuelvan a contactarme|no deseo recibir mensajes)\b',text, _re.I):
        case['no_contactar']=True
        case['seguimiento_recomendado']='No contactar; respetar oposición expresa.'
    elif human_declined(text):
        case['asesoria_rechazada']=True
        case['seguimiento_recomendado']='Orientación en este canal; valorar seguimiento humano solo si procede y está autorizado.'

    if key:
        try:
            facts,reply=gemini_reply(case['mensajes'],fallback,key)
            case['motor']='Gemini + reglas'
            case['error_ia']=''
        except Exception as err:
            facts,reply=fallback,deterministic_fallback(text,fallback,case['mensajes'])
            case['motor']='Reglas locales (Gemini no disponible)'
            case['error_ia']=f'{type(err).__name__}: {str(err)[:160]}'
    else:
        facts,reply=fallback,deterministic_fallback(text,fallback,case['mensajes'])
        case['motor']='Reglas locales (sin clave Gemini)'
        case['error_ia']=''
    case['necesidades_detectadas']=business_needs_from_history(case['mensajes'])
    # Aceptar respuestas cortas a una oferta de asesor ya presentada.
    prior_assistant = next((m['texto'] for m in reversed(case['mensajes'][:-1]) if m['rol']=='asistente'), '')
    # Las respuestas afirmativas coloquiales pueden contener la modalidad y palabras
    # adicionales: «sí por llamada está bien», «claro, mejor videollamada».
    # Solo implican asesoría si el asistente acababa de ofrecerla.
    norm = text.casefold().strip()
    offer_previous = any(marker in prior_assistant.casefold() for marker in (
        'te gustaría que un asesor', 'te gustaria que un asesor',
        'prefieres videollamada o llamada', 'te gustaría hablar con un asesor',
        'te gustaria hablar con un asesor', 'te gustaría que revisemos horarios',
    ))
    positive_reply = bool(_re.search(r'^(?:s[ií]|claro|vale|ok|de acuerdo|perfecto|me parece|por supuesto)\b', norm))
    negative_reply = bool(_re.search(r'\b(?:no|sin|tampoco|nunca)\s+(?:quiero|necesito|prefiero|deseo|asesor|llamada|videollamada)\b', norm))
    # «sí por llamada está bien» => aceptación; «no quiero llamada» => rechazo.
    short_accept = positive_reply and not negative_reply and len(norm.split()) <= 12
    # Un canal elegido después de que ofrecimos asesoría también es aceptación.
    # No usar menciones incidentales de 'llamada' fuera de este contexto.
    selected_mode=appointment_preference(text)
    # Mencionar únicamente la modalidad es una petición explícita para coordinarla.
    mode_direct=bool(_re.fullmatch(r'(?:por\s+|una?\s+|prefiero\s+|mejor\s+una?\s+)*(?:video\s*llamada|llamada|llamada telef[oó]nica)(?:\s+(?:por favor|esta bien))?[.!?]*',norm))
    mode_context=bool(offer_previous or case.get('solicitud_asesoria') or mode_direct)
    mode_accept=bool(selected_mode and mode_context and not negative_reply and
                     not _re.search(r'\b(?:no|sin)\s+(?:quiero|prefiero|necesito)\s+(?:una?\s+)?(?:video)?llamada\b',norm))
    if explicit_human_request(text) or (short_accept and offer_previous) or mode_accept:
        case['solicitud_asesoria']=True
    if human_declined(text):
        case['solicitud_asesoria']=False
    # También reconocer «Ale Lopez» cuando el asistente acaba de preguntar el nombre.
    previous_assistant = next((m['texto'] for m in reversed(case['mensajes'][:-1])
                               if m['rol']=='asistente'), '')
    awaiting_name = ('con quién tengo el gusto' in previous_assistant.casefold()
                     or 'con quien tengo el gusto' in previous_assistant.casefold())
    stated_name=extract_declared_name(text, awaiting_name=awaiting_name)
    if stated_name: case['nombre_prospecto']=stated_name
    sync_contact(case,text,known_leads(),lead)
    # Captura mínima antes de recomendaciones detalladas, sin bloquear orientación si se rechaza.
    declined_contact = bool(__import__('re').search(r'\b(?:no quiero dar|prefiero no dar|no compartir|no tengo correo|no tengo tel[eé]fono)\b', text.lower()))
    if declined_contact: case['contacto_rechazado']=True
    if case.get('identificacion') == 'Contacto por solicitar' and not declined_contact and not case.get('contacto_rechazado'):
        reply=request_contact_reply(case,lead)
        case['control_calidad']='Solicitar un identificador para deduplicar antes de registrar CRM'
        # Regla de calidad: una respuesta no debe mandar a agenda si no pidió persona.
    # Si ya tiene contacto, pero no conocemos el nombre, pedirlo antes de crear seguimiento.
    # Esto es una propuesta de calidad de datos, no un campo confirmado de Alegra.
    if (case.get('identificacion') != 'Contacto por solicitar' and
            not has_known_name(case, lead) and
            not case.get('nombre_rechazado')):
        if __import__('re').search(r'\b(?:prefiero no decir mi nombre|no quiero dar mi nombre)\b', text.lower()):
            case['nombre_rechazado']=True
        else:
            reply='¡Gracias! Ya tengo un medio para dar seguimiento. ¿Con quién tengo el gusto?'
            case['control_calidad']='Solicitar nombre sin bloquear atención'
    # La necesidad puede ser múltiple aunque el campo legacy sea de una sola etiqueta.
    detected_needs = business_needs_from_history(case['mensajes'])
    case['necesidades_detectadas'] = detected_needs
    if 'Inventarios / ventas' in detected_needs:
        facts['necesidad'] = 'Ventas e inventarios'
    elif 'Facturación' in detected_needs and facts.get('necesidad') == 'Por determinar':
        facts['necesidad'] = 'Facturación'
    human_latest = (case.get('solicitud_asesoria') or any(explicit_human_request(m['texto']) for m in case['mensajes'] if m['rol']=='prospecto')) and not human_declined(text)
    if not human_latest and __import__('re').search(r'\b(?:agend|videollamada|cita|asesor|reuni[oó]n|diagn[oó]stico)\b', reply.lower()):
        # Si Gemini desobedece la política, entregamos una respuesta segura y útil.
        reply = deterministic_fallback(text, facts, case['mensajes'])
        case['control_calidad'] = 'Respuesta reenfocada a orientación sin agenda no solicitada'
    # Protección comercial: una conversación madura debe recomendar, no perpetuar preguntas.
    stage = conversation_stage(case['mensajes'])
    case['fase_comercial'] = stage
    if case.get('identificacion') == 'Contacto por solicitar' and not declined_contact and not case.get('contacto_rechazado'):
        pass
    elif (case.get('identificacion') != 'Contacto por solicitar' and not has_known_name(case, lead) and not case.get('nombre_rechazado')):
        pass
    elif stage == 'contacto' and not human_latest:
        reply = contact_confirmation(case['mensajes'],lead.get('pais',''), (case.get('nombre_prospecto') or '').split(' ')[0])
        case['control_calidad'] = 'Canal de contacto registrado como preferencia; sin envío real'
    elif stage == 'recomendacion' and not human_latest:
        # Respuesta fiable sin inventar planes ni depender de que el modelo respete el prompt.
        reply = grounded_recommendation(case['mensajes'],lead.get('pais',''), (case.get('nombre_prospecto') or '').split(' ')[0])
        case['control_calidad'] = 'Orientación concreta entregada; evitar cuestionarios repetitivos'
    # Un algoritmo generativo no puede inventar la solicitud explícita de asesor.
    # Registrar preferencia expresada, sin imponer videollamada ni llamada.
    pref=appointment_preference(text)
    # La preferencia se registra solo cuando se está coordinando asesoría.
    if pref and case.get('solicitud_asesoria') and not negative_reply:
        case['modalidad_cita']=pref
    human_requested=case.get('solicitud_asesoria') or any(explicit_human_request(m['texto']) for m in case['mensajes'] if m['rol']=='prospecto')
    facts['asistencia']='Sí' if human_requested and not human_declined(text) else 'No declarada'
    case['facts']=facts
    if case.get('no_contactar'):
        reply='Entendido. No programaremos contactos adicionales. Si más adelante necesitas información, puedes escribirnos por este canal.'
    elif case.get('asesoria_rechazada') and not human_latest:
        reply='Claro, puedes revisar la información sin agendar una llamada. Si te surge alguna duda, aquí podemos orientarte.'
    case['mensajes'].append({'rol':'asistente','texto':reply})
    if case.get('crm_resultado') in ('nuevo','existente'):
        route_case(case,cases,lead.get('pais',''))
        if case.get('asesor') and not case.get('reserva') and not case.get('no_contactar') and not case.get('asesoria_rechazada'):
            # No afirmar que se contactará ni que la cita está confirmada.
            reply=advisor_reply(case,text,lead.get('pais','México'))
            case['mensajes'][-1]['texto']=reply
            if case.get('modalidad_cita'):
                slot,asked=requested_demo_slot(text,demo_slots(lead.get('pais','México')))
                # Aceptar solo confirmación clara después de ofrecer un horario exacto.
                last_offer=case.get('horario_ofrecido')
                if last_offer and __import__('re').search(r'\b(s[ií]|confirmo|confirmar|perfecto|de acuerdo)\b',text.lower()) and not asked:
                    case['reserva']=__import__('datetime').datetime.fromisoformat(last_offer).strftime('%d/%m/%Y · %H:%M')+' ('+lead.get('pais','México')+')'
                    case['estado']='Cita simulada reservada'
                    case['tipo_cita']=case['modalidad_cita']
                    case['notificacion']='[SIMULACIÓN] '+case['asesor']+' · '+case['modalidad_cita']+' · '+case['reserva']+'. Contexto registrado en la conversación; aviso no enviado.'
                    case['mensajes'][-1]['texto']=advisor_reply(case,text,lead.get('pais','México'))
                elif slot:
                    case['horario_ofrecido']=slot
                elif asked:
                    case['horario_ofrecido']=''

    else:
        case['estado']='Identificación pendiente'
        case['asesor']=''
        case['notificacion']=''
        case['reserva']=''
    return case


def gemini_classify(messages, key):
    """One batch inference call. Interpret free text only; decisions remain deterministic."""
    instructions = '''Eres un extractor de señales comerciales en español. Solo usa evidencia explícita de los textos.
Devuelve únicamente JSON con objeto {"items":[{"id":id,"segmento_inferido":"Contador|Pyme|Desconocido","necesidad":"Ventas e inventarios|Facturación|Migración / asesoría|Asesoría para elegir solución|Por determinar","horizonte":"Inmediato|Este mes|Próximo mes|Futuro / exploración|No declarado","asistencia":"Sí|No declarada"}]}.
No inventes datos. "Este mes" si dice este mes, antes de que acabe este mes o una fecha límite dentro del mes actual. "Próximo mes" solo para el mes siguiente. "Antes de noviembre" en octubre significa "Este mes". Necesidad de negocio y asistencia son campos diferentes. Si menciona ventas o inventarios, la necesidad es "Ventas e inventarios" aunque pida asesoría para elegir plan; en ese caso asistencia es "Sí". No confundas Excel con migración técnica: si solo busca elegir un software y no declara una necesidad funcional, devuelve "Asesoría para elegir solución". "Sí" en asistencia si solicita ayuda humana, asesoría u orientación. Solicitar información genérica sin explicar la necesidad NO es asesoría para elegir software. Nunca sustituyas la necesidad funcional por asistencia. Valores exactos.
Textos: '''+json.dumps(messages,ensure_ascii=False)
    payload={'contents':[{'parts':[{'text':instructions}]}], 'generationConfig':{'responseMimeType':'application/json','temperature':0}}
    request=urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','x-goog-api-key':key},method='POST')
    with urllib.request.urlopen(request,timeout=40) as r: data=json.load(r)
    raw=data['candidates'][0]['content']['parts'][0]['text']
    arr=json.loads(raw)['items']
    valid={'segmento_inferido':{'Contador','Pyme','Desconocido'},'necesidad':{'Ventas e inventarios','Facturación','Migración / asesoría','Asesoría para elegir solución','Por determinar'},'horizonte':{'Inmediato','Este mes','Próximo mes','Futuro / exploración','No declarado'},'asistencia':{'Sí','No declarada'}}
    result={}
    for entry in arr:
        if not all(entry.get(k) in opts for k,opts in valid.items()): raise ValueError('La IA devolvió etiquetas no válidas')
        result[str(entry['id'])]={k:entry[k] for k in valid}
    if any(str(item['id']) not in result for item in messages): raise ValueError('La IA omitió leads')
    return result

from crm_recovery_view import view as recovery_view

if 'ai_cache' not in st.session_state: st.session_state.ai_cache={}
if 'chat_selected' not in st.session_state: st.session_state.chat_selected=None
if 'vista_actual' not in st.session_state: st.session_state.vista_actual='Overview gerencial'
if 'lead_preferido' not in st.session_state: st.session_state.lead_preferido=None

st.markdown('<div class="apphead"><h1>Smart Lead Intelligence</h1><div class="smalltext">Propuesta conceptual para Alegra · Prototipo interno con datos 100% sintéticos · No es un producto oficial</div></div>',unsafe_allow_html=True)
with st.sidebar:
    st.subheader('Herramientas')
    with st.expander('Configuración técnica · Gemini', expanded=False):
        api_key=st.text_input('Clave Gemini (opcional)',type='password',value=os.getenv('GEMINI_API_KEY',''),help='No se almacena en el CSV ni en el código.')
    st.caption('Motor conversacional y clasificación de prueba. La clave no forma parte del dashboard gerencial.')
    if st.button('Analizar todos con IA',disabled=not api_key,use_container_width=True):
        all_leads=known_leads()
        try:
            with st.spinner('Interpretando mensajes con IA real...'):
                st.session_state.ai_cache=gemini_classify([{'id':a['id'],'mensaje':a['mensaje']} for a in all_leads],api_key)
            st.success('Extracción realizada con Gemini')
        except Exception as e:
            st.error('La API no respondió o rechazó la solicitud. Seguimos con reglas locales.')
            st.caption(f'Detalle técnico: {str(e)[:240]}')
    if st.button('Limpiar resultados de IA',use_container_width=True): st.session_state.ai_cache={}
    st.divider()
    st.caption('Reglas de demo: alertar por inactividad de 1 día sin intento o 2 días desde el último intento sin respuesta. Son umbrales ilustrativos, NO SLAs reales de Alegra.')

all_leads=known_leads()
cases=load_cases()
results=[]
for lead in all_leads:
    chat_case=cases.get(lead['id'])
    facts=(chat_case or {}).get('facts') or st.session_state.ai_cache.get(lead['id'])
    result=assess(lead,facts=facts)
    if chat_case:
        result['ruta']='Venta asistida · agenda simulada' if chat_case.get('asesor') else 'Atención conversacional con IA'
        result['accion']='Videollamada simulada reservada' if chat_case.get('reserva') else 'Ofrecer horarios disponibles' if chat_case.get('asesor') else 'Continuar orientación y registrar respuesta'
        result['origen_analisis']=chat_case.get('motor','Reglas locales')
    if facts and not chat_case: result['origen_analisis']='IA Gemini (texto) + reglas comerciales'
    results.append({**lead,**result})

# Navegación gerencial: visión → alertas/cartera → demostración → recuperación histórica.
if st.session_state.pop('volver_al_panel', False):
    st.session_state['navegar_a'] = 'Cartera de oportunidades'
next_view=st.session_state.pop('navegar_a',None)
if next_view:
    st.session_state.vista_actual = next_view
if st.session_state.get('vista_actual') not in ('Overview gerencial','Cartera de oportunidades','Atención comercial con IA','Recuperación de oportunidades'):
    st.session_state.vista_actual='Overview gerencial'
st.segmented_control('Vista', ['Overview gerencial','Cartera de oportunidades','Atención comercial con IA','Recuperación de oportunidades'],key='vista_actual',label_visibility='collapsed')
if st.session_state.vista_actual == 'Overview gerencial':
    executive(results,cases)
if st.session_state.vista_actual == 'Cartera de oportunidades':
    operational(results,cases)
if st.session_state.vista_actual == 'Recuperación de oportunidades':
    recovery_view()
if st.session_state.vista_actual == 'Atención comercial con IA':
    st.markdown('### Bandeja omnicanal · simulación funcional')
    st.caption('Canales ficticios, sin envíos externos. La IA responde en la pantalla; el asesor y el calendario son simulados. No uses datos personales reales.')
    with st.expander('Iniciar una conversación de prueba', expanded=not bool(cases)):
        with st.form('alta_conversacion'):
            name=st.text_input('Nombre ficticio del prospecto (si se conoce)',value='Prospecto sin identificar')
            c1,c2=st.columns(2)
            with c1:
                country=st.selectbox('País de prueba',['México','Colombia','Perú','República Dominicana'])
                channel=st.selectbox('Canal donde llega el mensaje',['Instagram','WhatsApp','Web / chatbot','Google Ads → formulario','Correo'])
            with c2:
                email=st.text_input('Correo ficticio (opcional)')
                phone=st.text_input('Teléfono ficticio (opcional)')
            first=st.text_area('Mensaje libre del prospecto',value='Hola, tengo una tienda de ropa y quiero empezar a facturar este mes. ¿Qué me recomiendan?',height=100)
            start=st.form_submit_button('Recibir mensaje y responder con IA',use_container_width=True)
        if start:
            if not first.strip():
                st.warning('Necesitamos un mensaje para simular la atención.')
            else:
                try:
                    leads=load_saved_leads()
                    lid=next_manual_id(leads)
                    contact=email.strip() or phone.strip()
                    new={'id':lid,'nombre':name.strip() or 'Prospecto ficticio','pais':country,'segmento':'','contacto':contact,'correo':email.strip(),'telefono':phone.strip(),'origen_registro':'Conversación omnicanal simulada','estado_crm':'Pre-registro sin CRM','asignacion':'Sin asignar','responsable':'','fuente':channel,'etapa':'MQL','fecha_ingreso':__import__('datetime').date.today().isoformat(),'ultimo_intento':'','intentos':'0','respondio':'','mensaje':first.strip()}
                    case={'lead_id':lid,'canal':channel,'estado':'Atención con IA','asesor':'','reserva':'','notificacion':'','mensajes':[], 'facts':{}}
                    process_turn(case,cases,new,first.strip(),api_key)
                    if case.get('crm_resultado') == 'nuevo':
                        new['estado_crm']='Nuevo contacto simulado'
                    elif case.get('crm_resultado') == 'existente':
                        new['estado_crm']='Vinculado a contacto existente'
                    elif case.get('crm_resultado') == 'revision':
                        new['estado_crm']='Pendiente revisión de duplicados'
                    save_saved_leads(leads+[new])
                    cases[lid]=case
                    save_cases(cases)
                    st.session_state.chat_selected=lid
                    st.rerun()
                except Exception as exc:
                    st.error(f'No se pudo registrar la conversación: {exc}')
    if cases:
        ids=list(cases.keys())
        if st.session_state.chat_selected not in ids: st.session_state.chat_selected=ids[-1]
        chosen=st.selectbox('Conversación activa',ids,index=ids.index(st.session_state.chat_selected),format_func=lambda lid:lid+' · '+next((l['nombre'] for l in all_leads if l['id']==lid),lid)+' · '+cases[lid].get('canal',''))
        st.session_state.chat_selected=chosen
        case=cases[chosen]
        lead=next((l for l in all_leads if l['id']==chosen),None)
        if lead is None:
            st.warning('No encontramos los datos de este prospecto. Revisa los archivos locales.')
        else:
            st.markdown('#### Conversación')
            for item in case.get('mensajes',[]):
                with st.chat_message('user' if item['rol']=='prospecto' else 'assistant'):
                    st.write(item['texto'])
            if case.get('error_ia'):
                st.warning('Gemini no respondió en este turno: se utilizó una respuesta local de respaldo. '+case['error_ia'])
            if not api_key: st.info('Sin clave Gemini: las respuestas son plantillas locales; para mostrar conversación generativa, ingresa tu clave en la barra lateral.')
            with st.form('chat_turn_'+chosen,clear_on_submit=True):
                turn=st.text_area('Siguiente mensaje libre del prospecto',placeholder='Ej.: Sí, necesito hablar con un asesor mañana por videollamada',height=75)
                send=st.form_submit_button('Enviar mensaje de prueba',use_container_width=True)
            if send:
                if not turn.strip():
                    st.warning('Escribe un mensaje.')
                else:
                    process_turn(case,cases,lead,turn.strip(),api_key)
                    # Extraer correo explícitamente compartido durante la simulación.
                    import re as _re
                    email_match = _re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}', turn)
                    if email_match:
                        case['correo_preferido'] = email_match.group(0)
                        case['canal_contacto_preferido'] = 'Correo'
                    elif _re.search(r'\b(?:whatsapp|whats)\b', turn.lower()):
                        case['canal_contacto_preferido'] = 'WhatsApp'
                    saved=load_saved_leads()
                    for entry in saved:
                        if entry['id']==chosen:
                            if case.get('nombre_prospecto'):
                                entry['nombre']=case['nombre_prospecto']
                            entry['mensaje']=' '.join(m['texto'] for m in case['mensajes'] if m['rol']=='prospecto')
                            if case.get('correo_preferido'):
                                entry['correo']=case['correo_preferido']
                                entry['contacto']=case['correo_preferido']
                            if case.get('telefono_preferido'):
                                entry['telefono']=case['telefono_preferido']
                                if not entry.get('contacto'):
                                    entry['contacto']=case['telefono_preferido']
                            if case.get('asesor'):
                                entry['asignacion']='Ya asignado a vendedor'
                                entry['responsable']=case['asesor']
                            elif entry.get('origen_registro') == 'Conversación omnicanal simulada':
                                entry['asignacion']='Sin asignar'
                                entry['responsable']=''
                    status=case.get('crm_resultado')
                    if status == 'existente':
                        target_id=case.get('crm_vinculado')
                        if target_id and not any(r['id']==target_id for r in saved):
                            originals=load_leads()
                            original=next((row for row in originals if row['id']==target_id),None)
                            if original:
                                source=next(x for x in saved if x['id']==chosen)
                                updates=load_crm_updates()
                                amended=conservative_enrichment({**original,**updates.get(target_id,{})},source,turn.strip())
                                # Sólo los campos nuevos y el contexto; el CSV original permanece intacto.
                                updates[target_id]={k:v for k,v in amended.items() if original.get(k)!=v}
                                save_crm_updates(updates)
                        for i,entry in enumerate(saved):
                            if entry['id']==target_id:
                                source=next(x for x in saved if x['id']==chosen)
                                saved[i]=conservative_enrichment(entry,source,turn.strip())
                        for entry in saved:
                            if entry['id']==chosen: entry['estado_crm']='Vinculado a contacto existente'
                    elif status == 'nuevo':
                        for entry in saved:
                            if entry['id']==chosen: entry['estado_crm']='Nuevo contacto simulado'
                    elif status == 'revision':
                        for entry in saved:
                            if entry['id']==chosen: entry['estado_crm']='Pendiente revisión de duplicados'
                    save_saved_leads(saved)
                    cases[chosen]=case
                    save_cases(cases)
                    st.rerun()
            st.divider()
            st.markdown('#### Estado de la atención')
            st.write('**Estado:**',case.get('estado',''), ' · **Canal:**',case.get('canal',''))
            st.write('**Identificación:**', case.get('identificacion','Pendiente'), ' · **CRM simulado:**',case.get('crm_resultado','Sin búsqueda'))
            if case.get('crm_vinculado'): st.info('Contacto existente vinculado: '+case['crm_vinculado']+' · Se conserva la información original.')
            if case.get('crm_resultado')=='revision': st.warning('Coincidencia ambigua: no fusionar ni crear contacto hasta revisión humana. '+case.get('crm_razon',''))
            st.caption('Fase comercial: '+case.get('fase_comercial','descubrimiento')+' · Catálogo y envíos reales: pendientes de integración')
            if case.get('canal_contacto_preferido'):
                st.write('**Canal preferido registrado:**',case['canal_contacto_preferido'])
            st.write('**Necesidades detectadas:**',', '.join(case.get('necesidades_detectadas', [])) or case.get('facts',{}).get('necesidad','Por determinar'), ' · **Tiempo de compra:**',case.get('facts',{}).get('horizonte','No declarado'))
            if case.get('asesor'):
                st.success('Asignación simulada: '+case['asesor']+' · '+lead['pais'])
                st.info(case.get('notificacion',''))
                if case.get('reserva'):
                    st.success((case.get('tipo_cita') or 'Videollamada')+' SIMULADA reservada: '+case['reserva'])
                    st.caption('En producción: confirmar disponibilidad real, crear evento y enlace de videollamada, avisar al asesor y prospecto, y escribir en CRM.')
                else:
                    slots=demo_slots(lead['pais'])
                    if slots and (case.get('modalidad_cita') != 'Llamada telefónica' or case.get('telefono_preferido')):
                        from datetime import datetime
                        selected_slot=st.selectbox('Disponibilidad FICTICIA del asesor (horario local del país)',slots,format_func=lambda t:datetime.fromisoformat(t).strftime('%d/%m/%Y · %H:%M'))
                        if st.button('Confirmar cita de prueba',use_container_width=True):
                            case['reserva']=datetime.fromisoformat(selected_slot).strftime('%d/%m/%Y · %H:%M')+' ('+lead['pais']+')'
                            case['estado']='Cita simulada reservada'
                            case['tipo_cita']=case.get('modalidad_cita') or 'Videollamada'
                            case['notificacion']='[SIMULACIÓN] '+case['asesor']+' tiene una videollamada de prueba con '+lead['nombre']+' el '+case['reserva']+'. Preparar resumen. Sin avisos reales.'
                            cases[chosen]=case
                            save_cases(cases)
                            st.rerun()
                    else: st.warning('Se requiere número telefónico para la llamada, o no hay horarios ficticios próximos.')
            else:
                if case.get('estado') == 'Identificación pendiente':
                    st.info('Caso sin registro CRM confirmado: necesitamos un identificador antes de crear/asignar; la orientación puede continuar en este canal.')
                else:
                    st.success('Atención asistida por IA: todavía no se necesita un vendedor.')
                st.caption('Esto NO significa venta cerrada ni consulta definitivamente resuelta: se mantiene historial y siguiente paso para medir resultados.')
            if st.button('Ver este lead en el dashboard'):
                st.session_state.lead_preferido=chosen
                st.session_state.volver_al_panel=True
                st.rerun()

