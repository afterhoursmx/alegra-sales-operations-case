"""Atención comercial simulada. Sin conexiones a canales ni calendarios reales."""
import json
import re
import urllib.request
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
from catalogo import recommended_plan, SOURCE

MODEL = 'gemini-3.5-flash-lite'
FACT_LABELS = {
    'segmento_inferido': {'Contador', 'Pyme', 'Desconocido'},
    'necesidad': {'Ventas e inventarios', 'Facturación', 'Migración / asesoría', 'Asesoría para elegir solución', 'Por determinar'},
    'horizonte': {'Inmediato', 'Este mes', 'Próximo mes', 'Futuro / exploración', 'No declarado'},
    'asistencia': {'Sí', 'No declarada'},
}

# El catálogo es estrictamente conceptual: nunca incluye tarifas ni supuestos de funcionalidades oficiales.
DEMO_KNOWLEDGE = (
    'BASE DE CONOCIMIENTO LIMITADA PARA DEMOSTRACIÓN, NO CATÁLOGO OFICIAL: '
    'El prospecto puede necesitar facturación, control de ventas/inventarios o ayuda de migración. '
    'La selección del producto, compatibilidad, precios y disponibilidad de funcionalidades deben '
    'verificarse en el catálogo oficial vigente antes de afirmarse. '
    'Puedes orientar sobre preguntas de diagnóstico, próximos pasos y ofrecer un asesor. '
    'No inventes precio, descuentos, planes específicos, promociones, plazos de implementación ni enlaces.'
)

ADVISOR_POOLS = {
    'México': ['Juan López (asesor ficticio)', 'María Pérez (asesora ficticia)'],
    'Colombia': ['Asesor CO A', 'Asesor CO B'],
    'Perú': ['Asesor PE A', 'Asesor PE B'],
    'República Dominicana': ['Asesor RD A', 'Asesor RD B'],
}
TZ = {'México':'America/Mexico_City','Colombia':'America/Bogota','Perú':'America/Lima','República Dominicana':'America/Santo_Domingo'}


def explicit_human_request(text):
    """Solo solicitudes humanas; no confundir migración/urgencia con asesor requerido."""
    t = (text or '').lower()
    if re.search(r'\b(?:no|sin)\s+(?:necesito|quiero|ocupo|requiero)?\s*(?:un\s+|una\s+)?(?:asesor|persona|agente|vendedor|ayuda humana)\b',t):
        return False
    patterns = [
        r'\b(?:asesor(?:a|ía)?|vendedor|ejecutivo|especialista|persona real)\b',
        r'\b(?:hablar|contactar|comunicarme|reunirme)\s+con\s+(?:alguien|una persona|un asesor|un vendedor|soporte|un experto)\b',
        r'\b(?:quiero|necesito|podemos|puedo|agendar|programar)\b.{0,40}\b(?:videollamada|reuni[oó]n|cita|demo en vivo)\b',
        r'\b(?:necesito|quiero|requiero)\s+(?:que me )?(?:ayud(?:e|en)|orient(?:e|en)|acompañ(?:e|en))\b',
    ]
    return any(re.search(p,t) for p in patterns)


def human_declined(text):
    t=(text or '').lower()
    return bool(re.search(r'(?:no necesito|no quiero|sin|prefiero sin)\s+(?:hablar con\s+|contactar\s+)?(?:un\s+|una\s+)?(?:asesor|vendedor|ayuda|persona)|(?:por mi cuenta|yo sol[oa]|autoservicio|sin hablar con)',t))


def normalized_facts(raw, fallback):
    out = dict(fallback)
    for key, allowed in FACT_LABELS.items():
        if raw.get(key) in allowed:
            out[key] = raw[key]
    return out


def business_needs_from_history(history):
    """Evidence tags for dashboard; multiple needs may coexist."""
    text = ' '.join(x.get('texto', '') for x in history if x.get('rol') == 'prospecto').lower()
    tags = []
    if re.search(r'factur|cfdi|comprobante fiscal', text): tags.append('Facturación')
    if re.search(r'inventari|existencias|stock|control de ventas|\bpos\b|punto de venta|terminal de venta', text): tags.append('Inventarios / ventas')
    if re.search(r'migraci[oó]n|migrar|cambiar de sistema', text): tags.append('Migración')
    return tags


def deterministic_fallback(message, facts, history=None):
    """Offline help: one focused question, not an appointment-first template."""
    history = history or [{'rol': 'prospecto', 'texto': message}]
    needs = business_needs_from_history(history)
    latest = (message or '').lower()
    if explicit_human_request(latest) and not human_declined(latest):
        return ('Claro. Voy a preparar una asignación simulada a un asesor y mostrar horarios de ejemplo. '
                'Te compartiremos el contexto de tu necesidad para que no tengas que repetirlo.')
    if 'Facturación' in needs and 'Inventarios / ventas' in needs:
        if re.search(r'(?:solo|solamente|únicamente).{0,25}factur', latest):
            return ('Perfecto, entonces priorizamos la emisión de facturas. Podemos revisar los pasos iniciales '
                    'y después valorar el control de inventario. ¿Ya emites facturas con algún sistema?')
        return ('Entiendo que quieres facturar y también gestionar las ventas de tu negocio con POS. '
                'La primera decisión es si quieres gestionar solo facturas o también ventas e inventarios en un mismo flujo; '
                'habría que verificar qué ofrece el catálogo vigente. ¿Quieres integrar ambos procesos o comenzar solo con facturación?')
    if 'Facturación' in needs:
        return ('Entiendo que quieres comenzar con facturación. Podemos revisar qué datos fiscales y tipo de comprobantes '
                'necesitas, y verificar las funciones y planes vigentes antes de elegir. '
                '¿Actualmente facturas con otro sistema o empezarías desde cero?')
    if 'Inventarios / ventas' in needs:
        return ('Entiendo que quieres organizar ventas o inventarios. Para orientar la elección sin asumir funcionalidades, '
                'necesito saber algo: ¿vendes desde una tienda física, en línea o por ambos canales?')
    if 'Migración' in needs:
        return ('Entiendo que quieres cambiar de sistema. Antes de recomendarte un camino concreto habría que verificar '
                'compatibilidad y opciones oficiales de migración. ¿De qué sistema vienes?')
    return ('Con gusto te oriento. Para darte una respuesta útil sin inventar planes ni precios, '
            '¿qué necesitas resolver primero: facturación, ventas/inventarios o migración?')


def conversation_stage(history):
    """Small commercial state machine, independent from generative text."""
    messages = [x.get('texto', '') for x in history if x.get('rol') == 'prospecto']
    joined = ' '.join(messages).lower()
    last = messages[-1].lower() if messages else ''
    needs = business_needs_from_history(history)
    if explicit_human_request(last) and not human_declined(last):
        return 'escalamiento'
    if re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|\b(?:correo|whatsapp|whats)\b',last) and len(messages) >= 2:
        return 'contacto'
    if re.search(r'\b(?:solo quiero saber qu[eé] hacer|dime qu[eé] hacer|ya dime|no m[aá]s preguntas|solo dame|qu[eé] me recomiendas|cu[aá]l (?:plan|membres[ií]a))\b',last):
        return 'recomendacion'
    # Two substantive answers (or more than 3 prospect turns) normally suffice.
    if needs and len(messages) >= 3:
        return 'recomendacion'
    if needs and len(messages) >= 2 and re.search(r'no tengo ni idea|no s[eé]|me quita mucho tiempo|es manual|manualmente', joined):
        return 'recomendacion'
    return 'descubrimiento'


def grounded_recommendation(history, country="México", first_name=""):
    """Respuesta corta y legible; precio solo desde instantánea catalogada."""
    needs = business_needs_from_history(history)
    greeting = f"¡Mucho gusto, {first_name}!" if first_name else "¡Claro, con gusto te ayudo!"
    if 'Facturación' in needs and 'Inventarios / ventas' in needs:
        intro = "Por lo que me cuentas, buscas simplificar la facturación y gestionar ventas o inventarios."
    elif 'Facturación' in needs:
        intro = "Por lo que me cuentas, buscas emitir facturas más fácilmente y ahorrar tiempo."
    elif 'Inventarios / ventas' in needs:
        intro = "Por lo que me cuentas, necesitas organizar tus ventas e inventarios."
    elif 'Migración' in needs:
        intro = "Por lo que me cuentas, necesitas cambiar de sistema; conviene revisar el proceso de migración."
    else:
        return greeting + "\n\nPara orientarte bien, ¿qué es lo principal que buscas resolver: facturación, ventas o inventarios?"
    plan = recommended_plan(needs, country)
    if plan:
        # La fuente ya vive en catalogo.py; no crear promesas de envío o reservas.
        body = plan
    else:
        body = "Podemos revisar las opciones vigentes del catálogo oficial para tu país y elegir la que cubra esa necesidad."
    return (f"{greeting}\n\n{intro}\n\n**Una opción para ti:**\n\n{body}\n\n"
            "Dejé preparada la información para tu correo o WhatsApp; el envío se realizará cuando el canal esté conectado. "
            "¿Te gustaría que un asesor te explique cómo comenzar? Podemos revisar horarios para videollamada o llamada telefónica.")


def contact_confirmation(history, country="México", first_name=""):
    """Una dirección registrada no significa que se haya enviado ningún mensaje."""
    return grounded_recommendation(history, country, first_name)


def asks_for_information_delivery(text):
    return bool(re.search(r'\b(?:m[aá]ndame|envi[aá]me|comp[aá]rteme|quiero recibir|por correo|por whatsapp|por whats)\b',(text or '').lower()))


def gemini_reply(history, fallback_facts, key):
    """One Gemini call for extraction + natural-language response, never an external message."""
    schema_example = {'segmento_inferido':'Pyme','necesidad':'Facturación','horizonte':'Este mes','asistencia':'No declarada'}
    topics = business_needs_from_history(history)
    stage = conversation_stage(history)
    instruction = (
        'Eres un agente comercial de orientación de PRUEBA para Alegra, no un canal oficial. '
        'Devuelve respuesta en español mexicano, cálida, natural, 45 a 95 palabras. '
        'PRIORIDAD: responder útilmente al objetivo expresado ANTES de ofrecer una cita. '
        'No sugieras diagnóstico, reunión, videollamada, asesor ni agendamiento por iniciativa propia cuando '
        'el prospecto pide una recomendación, incluso si quiere comprar hoy o este mes. '
        'Solo cuando el prospecto solicita EXPLÍCITAMENTE atención humana puedes ofrecer derivación y horarios simulados. '
        'En descubrimiento puedes formular UNA pregunta si modifica la recomendación. '
        'Si ya hay suficiente información, recomienda directamente; NUNCA hagas preguntas por costumbre. '
        'En fase de recomendación da primero una solución concreta por categoría, explica por qué, '
        'aclara que el plan exacto requiere catálogo verificado y ofrece envío opcional por correo/WhatsApp '
        'o asesoría opcional, sin presionar ni afirmar que enviaste algo. '
        'Si el cliente expresa cansancio o dice solo quiero saber qué hacer, NO HAGAS MÁS PREGUNTAS DE DIAGNÓSTICO. '
        'Si existe más de una necesidad (por ejemplo, facturación E inventarios), reconoce ambas. '
        'Si ya respondió una pregunta antes, no repitas esa pregunta. '
        'Ante una respuesta posterior, sigue el hilo de la conversación sin recomenzar ni hacer la misma pregunta. '
        'Distingue urgencia de COMPRA y solicitud de contacto HUMANO. '
        'No declares disponibilidad real, no inventes funciones, precios, planes, compatibilidad, enlaces, reservas ni envíos. '
        'Si el prospecto solicita directamente atención humana, acepta y explica que se simulará la asignación. '
        'Si solo pide información, NO sugieras ni reserves una cita. '
        'Puedes mencionar que se verificará el catálogo oficial vigente, pero no uses eso como excusa para no orientar. '
        'Base autorizada: '+DEMO_KNOWLEDGE+'\n'
        'Necesidades detectadas por evidencia textual: '+json.dumps(topics,ensure_ascii=False)+'\n'
        'FASE COMERCIAL OBLIGATORIA: '+stage+'; respeta esta fase en tu respuesta.\n'
        'Tu salida debe ser SOLO JSON con facts y respuesta. facts usa este esquema: '
        +json.dumps(schema_example,ensure_ascii=False)+'. Valores permitidos: '
        +json.dumps({k:sorted(v) for k,v in FACT_LABELS.items()},ensure_ascii=False)+'. '
        'Historial completo: '+json.dumps(history,ensure_ascii=False)
    )
    payload={'contents':[{'parts':[{'text':instruction}]}],'generationConfig':{'responseMimeType':'application/json','temperature':0.2}}
    req=urllib.request.Request(f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','x-goog-api-key':key},method='POST')
    with urllib.request.urlopen(req,timeout=40) as response:
        data=json.load(response)
    obj=json.loads(data['candidates'][0]['content']['parts'][0]['text'])
    if not isinstance(obj.get('facts'),dict) or not isinstance(obj.get('respuesta'),str):
        raise ValueError('Respuesta de IA inválida')
    facts=normalized_facts(obj['facts'],fallback_facts)
    return facts,obj['respuesta'].strip()[:1200]


def assign_advisor(pais, cases, new_case_id):
    """Load balancing within a demo pool; stable existing assignments."""
    pool=ADVISOR_POOLS.get(pais, ['Asesor regional A', 'Asesor regional B'])
    counts={name:0 for name in pool}
    for cid,case in cases.items():
        if cid==new_case_id: continue
        if case.get('estado') in ('Pendiente de agenda','Cita simulada reservada') and case.get('asesor') in counts:
            counts[case['asesor']]+=1
    return min(pool,key=lambda name:(counts[name],pool.index(name)))


def demo_slots(pais, today=None):
    """Fictional free slots, country-local calendar. No calendar API."""
    tz=ZoneInfo(TZ.get(pais,'America/Mexico_City'))
    now=datetime.now(tz) if today is None else today
    out=[]
    for day_delta in range(0,11):
        d=(now+timedelta(days=day_delta)).date()
        if d.weekday()>=5: continue
        for hour,minute in [(10,0),(12,30),(14,0),(16,0)]:
            candidate=datetime(d.year,d.month,d.day,hour,minute,tzinfo=tz)
            if candidate <= now+timedelta(minutes=30): continue
            out.append(candidate.isoformat())
            if len(out)>=30: return out
    return out


def route_case(case, cases, pais):
    """Only triggers human routing when explicitly requested, regardless of model ambiguity."""
    history=case.get('mensajes',[])
    texts=[x.get('texto','') for x in history if x.get('rol')=='prospecto']
    latest=texts[-1] if texts else ''
    if human_declined(latest):
        if not case.get('reserva'): case['estado']='Atención con IA'; case['asesor']=''
        return case
    if case.get('solicitud_asesoria') or any(explicit_human_request(t) for t in texts):
        if not case.get('asesor'):
            case['asesor']=assign_advisor(pais,cases,case['lead_id'])
        if not case.get('reserva'):
            case['estado']='Pendiente de agenda'
        case['notificacion']=f"[SIMULACIÓN] Nuevo lead {case['lead_id']} para {case['asesor']}. Revisar contexto y disponibilidad; no se ha enviado aviso externo."
    else:
        case['estado']='Atención con IA'
    return case


WEEKDAYS = {'lunes':0,'martes':1,'miercoles':2,'miércoles':2,'jueves':3,'viernes':4,'sabado':5,'sábado':5,'domingo':6}

def appointment_preference(message):
    """Canal preferido; no asumir teléfono disponible para llamada."""
    t=(message or '').lower()
    if 'videollamada' in t or 'video llamada' in t or 'meet' in t: return 'Videollamada'
    if 'llamada' in t or 'por teléfono' in t or 'por telefono' in t: return 'Llamada telefónica'
    return ''

def requested_demo_slot(text, slots):
    """Acepta horario solo (12:30, 1230, a las 1230) y día opcional.

    Si hay varios días con la misma hora, escoge el primer día OFRECIDO,
    sin exigir que el prospecto repita lunes.
    """
    t=(text or '').lower().strip()
    # Evitar aceptar números telefónicos largos como horas.
    match=re.search(r'(?<!\d)(?:a\s+las\s+|las\s+)?(\d{1,2})[:.](\d{2})(?!\d)',t)
    if not match:
        match=re.search(r'(?<!\d)(?:a\s+las\s+|las\s+)?(\d{1,2})([0-5]\d)(?!\d)',t)
    if match:
        hour,minute=int(match.group(1)),int(match.group(2))
    else:
        match=re.search(r'\b(?:a\s+las\s+|las\s+)(\d{1,2})(?!\d)',t)
        if not match:
            # "a las 12", "12 pm", "12" cuando se piden horarios.
            match=re.fullmatch(r'(\d{1,2})\s*(am|pm)?',t)
            if not match:return None,False
        hour,minute=int(match.group(1)),0
    if hour>23 or minute>59:return None,True
    suffix=re.search(r'(?:\b(?:de la\s+)?(mañana|tarde|noche)\b|(?<![a-z])(am|pm)\b)',t)
    suffix=(suffix.group(1) or suffix.group(2)) if suffix else ''
    if suffix in ('tarde','noche','pm') and hour<12:hour+=12
    if suffix in ('mañana','am') and hour==12:hour=0
    wd=next((num for name,num in WEEKDAYS.items() if re.search(r'\b'+name+r'\b',t)),None)
    relative='pasado mañana' if 'pasado mañana' in t else 'mañana' if 'mañana' in t and suffix!='mañana' else 'hoy' if 'hoy' in t else ''
    # Si dice 'a las 4' sin AM/PM y solo ofrecimos 16:00, tomar 16:00.
    # La coincidencia literal tiene prioridad si también existe 04:00.
    possible_hours=[hour]
    if not suffix and 1 <= hour <= 11:
        possible_hours.append(hour+12)
    for possible_hour in possible_hours:
        for slot in slots:
            d=datetime.fromisoformat(slot)
            if (d.hour,d.minute)!=(possible_hour,minute):continue
            if wd is not None and d.weekday()!=wd:continue
            if relative:
                now=datetime.now(d.tzinfo).date()
                offset=2 if relative=='pasado mañana' else 1 if relative=='mañana' else 0
                if d.date()!=now+timedelta(days=offset):continue
            return slot,True
    return None,True

def advisor_reply(case, incoming, pais):
    """User-facing phrasing separate from internal simulation / log."""
    name=(case.get('nombre_prospecto') or '').split(' ')[0]
    hello=f'¡Claro, {name}!' if name else '¡Claro!'
    mode=case.get('modalidad_cita','')
    slots=demo_slots(pais)
    if case.get('reserva'):
        return f'{hello} Tu cita quedó registrada para {case["reserva"]} con {case.get("asesor", "un asesor").replace(" (asesor ficticio)", "").replace(" (asesora ficticia)", "")}. En una integración real recibirías la invitación y el enlace correspondientes.'
    if not mode:
        return f'{hello} Te puedo poner en contacto con un asesor que ya tendrá el resumen de lo que necesitas. ¿Prefieres videollamada o llamada telefónica?'
    if mode=='Llamada telefónica' and not case.get('telefono_preferido'):
        return f'{hello} Perfecto, por llamada telefónica. ¿Me compartes el número de teléfono al que deseas que te llame el asesor?'
    if mode=='Videollamada' and not case.get('correo_preferido'):
        return f'{hello} Perfecto, por videollamada. ¿A qué correo podemos enviar la invitación y el enlace cuando el calendario esté conectado?'
    slot,asked=requested_demo_slot(incoming,slots)
    if slot:
        d=datetime.fromisoformat(slot)
        when=['lunes','martes','miércoles','jueves','viernes','sábado','domingo'][d.weekday()]+d.strftime(' %d/%m a las %H:%M')
        return f'{hello} Revisé los horarios de nuestro calendario de demostración. {case.get("asesor","Un asesor").replace(" (asesor ficticio)", "").replace(" (asesora ficticia)", "")} tiene disponibilidad {when}. ¿Confirmamos ese horario para tu {mode.lower()}?'
    available=', '.join((['lun','mar','mié','jue','vie','sáb','dom'][datetime.fromisoformat(x).weekday()]+datetime.fromisoformat(x).strftime(' %d/%m %H:%M')) for x in slots[:4])
    intro='Ese horario no aparece disponible en el calendario de prueba. ' if asked else ''
    recipient = ('Llamaremos al número terminado en '+case['telefono_preferido'][-4:]+'. ') if mode=='Llamada telefónica' and case.get('telefono_preferido') else ('Usaremos el correo '+case['correo_preferido']+' para la invitación cuando conectemos los envíos. ') if mode=='Videollamada' and case.get('correo_preferido') else ''
    return f'{hello} {intro}{recipient}Estos son algunos espacios disponibles: {available} (hora local de {pais}). ¿Cuál te queda mejor para tu {mode.lower()}?'
