"""Deterministic commercial decision engine. No paid API required.
AI is optional and must be clearly labelled when activated in app.py.
All records are synthetic. Commercial thresholds are demo hypotheses.
"""
import re
import calendar
from datetime import datetime, date, timedelta
from typing import Dict, Any

HELP = ('asesor', 'asesorí', 'ayuda', 'hablar con', 'demo', 'demostraci', 'migrar', 'migraci', 'implementaci', 'personaliza', 'orienta', 'orientación', 'aconsej', 'guíame', 'guia')
NOW = ('hoy', 'ya quiero', 'inmediato', 'urgente', 'cuanto antes', 'lo antes posible', 'esta semana', 'mañana', 'pasado mañana')
THIS_MONTH = ('este mes', 'antes de que termine este mes', 'antes que termine este mes', 'antes de acabar el mes', 'antes de noviembre')
SOON = ('próximo mes', 'proximo mes', 'en un mes', 'el siguiente mes', 'siguiente mes', 'mes que viene', '30 días', '30 dias')
FUTURE = ('tres meses', '3 meses', 'dos meses', '2 meses', 'más adelante', 'mas adelante', 'explorando', 'comparando')
ACCOUNTANT = ('contador', 'contable', 'despacho', 'clientes contables', 'contadores')
INVENTORY = ('inventario', 'existencias', 'stock', 'ventas', 'punto de venta', 'tienda', 'pos')
INVOICING = ('factur', 'cfdi', 'comprobante fiscal')


def contains(text, words):
    return any(word in text for word in words)


def text_facts(message: str) -> Dict[str, str]:
    t = (message or '').lower()
    segment = 'Contador' if contains(t, ACCOUNTANT) else ('Pyme' if contains(t, INVENTORY + INVOICING + ('negocio', 'empresa', 'cafetería', 'restaurante')) else 'Desconocido')
    need = 'Ventas e inventarios' if contains(t, INVENTORY) else ('Facturación' if contains(t, INVOICING) else ('Migración / asesoría' if contains(t, ('migrar', 'migraci')) else 'Por determinar'))
    if contains(t, NOW): horizon = 'Inmediato'
    elif contains(t, THIS_MONTH): horizon = 'Este mes'
    elif contains(t, SOON): horizon = 'Próximo mes'
    elif contains(t, FUTURE): horizon = 'Futuro / exploración'
    else: horizon = 'No declarado'
    assistance = 'Sí' if contains(t, HELP) else ('No declarada')
    return {'segmento_inferido': segment, 'necesidad': need, 'horizonte': horizon, 'asistencia': assistance}


def parse_date(value: str):
    try:
        return datetime.strptime(str(value)[:10], '%Y-%m-%d').date() if value else None
    except (ValueError, TypeError):
        return None


MONTH_NAMES = {'enero':1, 'febrero':2, 'marzo':3, 'abril':4, 'mayo':5,
               'junio':6, 'julio':7, 'agosto':8, 'septiembre':9, 'setiembre':9,
               'octubre':10, 'noviembre':11, 'diciembre':12}

def _end_of_month(year, month):
    return date(year, month, calendar.monthrange(year, month)[1])

def purchase_deadline(message, received_date, horizon):
    """Best-effort deadline anchored to the lead's original entry date, not viewing date.
    Only return a deadline when the phrase explicitly supports one; never infer a sale.
    """
    if not received_date:
        return None
    text = (message or '').lower()
    # A specifically named month takes precedence over the relative category.
    month_words = '|'.join(MONTH_NAMES)
    match = re.search(r'\b(' + month_words + r')\b', text)
    if match:
        month = MONTH_NAMES[match.group(1)]
        year = received_date.year + (month < received_date.month)
        prefix = text[max(0, match.start()-38):match.start()]
        if re.search(r'antes de\s+(?:que\s+)?(?:empiece|inicie)\s*$', prefix) or re.search(r'antes de\s*$',prefix):
            return date(year,month,1) - timedelta(days=1)
        return _end_of_month(year,month)
    # Plazos cortos se calculan desde la fecha de registro, nunca desde hoy.
    if re.search(r'\bpasado mañana\b', text):
        return received_date + timedelta(days=2)
    if re.search(r'\bmañana\b', text):
        return received_date + timedelta(days=1)
    # El plazo 'esta semana' se ancla al cierre de semana del registro, NO al fin de mes.
    if re.search(r'\besta semana\b', text):
        return received_date + timedelta(days=6-received_date.weekday())
    if horizon == 'Este mes':
        return _end_of_month(received_date.year,received_date.month)
    if horizon == 'Próximo mes':
        y = received_date.year + (received_date.month == 12)
        m = received_date.month % 12 + 1
        return _end_of_month(y,m)
    if horizon == 'Inmediato':
        return received_date
    return None

def assess(lead: Dict[str, Any], facts=None, reference_date=None) -> Dict[str, Any]:
    facts = facts or text_facts(lead.get('mensaje', ''))
    missing = []
    for name, field in [('país', 'pais'), ('correo o teléfono', 'contacto')]:
        if not str(lead.get(field, '')).strip(): missing.append(name)
    segment = str(lead.get('segmento') or facts.get('segmento_inferido') or 'Desconocido')
    if segment.lower() in ('desconocido', 'no declarado', ''): missing.append('segmento')
    horizon = facts.get('horizonte', 'No declarado')
    assistance = facts.get('asistencia', 'No declarada')
    if assistance == 'No declarada': missing.append('preferencia de asistencia')
    contact = bool(str(lead.get('contacto', '')).strip())
    urgent = horizon == 'Inmediato'
    assisted = assistance == 'Sí'
    stage = str(lead.get('etapa','MQL')).upper()
    last = parse_date(lead.get('ultimo_intento',''))
    entered = parse_date(lead.get('fecha_ingreso',''))
    today = parse_date(reference_date) if reference_date else date.today()
    deadline = purchase_deadline(lead.get('mensaje',''), entered, horizon)
    # Evidence grounded in the original message takes precedence over an ambiguous
    # AI label. Advice to choose a plan is assistance, not the underlying business need.
    declared_text = (lead.get('mensaje') or '').lower()
    if facts.get('necesidad') == 'Asesoría para elegir solución' and contains(declared_text, ('inventario', 'existencias', 'stock', 'ventas')):
        facts = {**facts, 'necesidad': 'Ventas e inventarios'}
    # Si el mensaje solicita orientación, no permitimos que la IA borre esa evidencia.
    if contains(declared_text, ('orienta', 'asesor', 'hablar con', 'necesito ayuda')) and assistance != 'Sí':
        assistance = 'Sí'
        assisted = True
        missing = [field for field in missing if field != 'preferencia de asistencia']
    # Una solicitud genérica de información no es una necesidad funcional confirmada.
    if segment == 'Desconocido' and not contains(declared_text, INVENTORY + INVOICING + ('migrar', 'migraci', 'contabilidad', 'nómina', 'nomina')):
        facts = {**facts, 'necesidad': 'Por determinar'}
    # A structured model label must not override a concrete date in the original text.
    if deadline and entered and horizon != 'Inmediato' and not contains(declared_text, ('esta semana',)):
        horizon = ('Este mes' if (deadline.year, deadline.month) == (entered.year, entered.month) else 'Próximo mes' if deadline <= _end_of_month(entered.year + (entered.month==12), entered.month%12+1) else horizon)
    # A concrete deadline is usable purchase timing even if keyword extraction
    # or the AI initially said 'No declarado'. Do not report it as missing.
    if horizon == 'No declarado' and not deadline:
        missing.append('tiempo estimado de compra')
    expired = bool(deadline and today and deadline < today)
    purchase_status = ('Fecha por confirmar' if not deadline else 'Fecha vencida · reconfirmar interés' if expired else 'Fecha vigente')
    display_deadline = deadline.strftime('%d/%m/%Y') if deadline else 'No especificada'
    attempts = int(lead.get('intentos') or 0)
    days_since = (today-last).days if last and today else None
    days_wait = (today-entered).days if entered and today else None
    # A follow-up alert is not a diagnosis of *why* the prospect did not reply.
    review = (stage not in ('GANADO','PERDIDO') and ((attempts > 0 and str(lead.get('respondio','')).lower() in ('no','false','0') and days_since is not None and days_since >= 2) or (attempts == 0 and days_wait is not None and days_wait >= 1)))
    sql_candidate = not expired and stage == 'MQL' and contact and facts.get('necesidad') != 'Por determinar' and horizon in ('Inmediato', 'Este mes', 'Próximo mes')
    if facts.get('necesidad') == 'Por determinar': route = 'Revisión / aclaración'
    elif assisted: route = 'Venta asistida'
    elif urgent and facts.get('necesidad') != 'Por determinar': route = 'Autoservicio guiado'
    elif horizon == 'Futuro / exploración': route = 'Nutrición'
    elif facts.get('necesidad') == 'Por determinar': route = 'Revisión / aclaración'
    else: route = 'Autoservicio con opción de asesoría'
    priority = 'Alta' if (urgent or horizon == 'Este mes') and assisted else ('Media' if horizon in ('Inmediato','Este mes','Próximo mes') or assisted else 'Baja')
    if review and priority == 'Baja': priority = 'Media'
    if expired: priority = 'Media' if assisted else 'Baja'
    reasons = []
    if expired: reasons.append('Fecha prevista vencida; no asumir compra ni pérdida de interés')
    elif urgent: reasons.append('Compra inmediata declarada')
    elif horizon == 'Este mes': reasons.append('Compra prevista durante este mes')
    elif horizon == 'Próximo mes': reasons.append('Compra prevista el próximo mes')
    if assisted: reasons.append('Solicita intervención humana')
    if review: reasons.append('Historial indica seguimiento pendiente de revisión; la causa no está comprobada')
    if sql_candidate: reasons.append('Cumple criterios preliminares para revisión MQL → SQL, no es conversión confirmada')
    if not reasons: reasons.append('Información insuficiente para asignar prioridad alta')
    action = ('Confirmar vigencia de necesidad y nueva fecha de compra; revisar responsable, canal y seguimiento pendiente' if expired and review else 'Confirmar vigencia de necesidad y nueva fecha de compra' if expired else 'Revisar responsable y canal de contacto; atender seguimiento pendiente' if review else 'Ofrecer asesoría / agendamiento' if assisted else 'Enviar recursos y opción de prueba' if route.startswith('Autoservicio') else 'Seguimiento según interés' if route == 'Nutrición' else 'Solicitar datos faltantes')
    return {**facts, 'segmento': segment, 'prioridad':priority, 'ruta':route, 'revision_seguimiento':review,'candidato_sql':sql_candidate,'faltantes':missing,'motivos':reasons,'accion':action,'origen_analisis':'Reglas locales', 'fecha_limite_compra':display_deadline,'estado_fecha_compra':purchase_status, 'horizonte':horizon, 'asistencia':assistance}
