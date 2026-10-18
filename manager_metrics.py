"""Deterministic dashboard calculations for SYNTHETIC leads only."""
from datetime import datetime, date, timedelta
import re

BASELINE = {
    'Leads mensuales': '14,000',
    'MQL → SQL': '34%',
    'SQL → Won': '21%',
    'Primer contacto · base anterior': '5.2 h',
    'Pérdidas «No responde»': '38%',
    'Completitud CRM': '61%',
    'Error forecast': '27%',
}


def team_of(record, case=None):
    """Return team for reporting; no guessed team when segment is unknown."""
    case = case or {}
    segment = str(case.get('facts', {}).get('segmento_inferido') or record.get('segmento') or '').casefold()
    if 'contad' in segment: return 'Contador'
    if 'pyme' in segment: return 'PyME'
    return 'Sin determinar'


def contact_complete(record, case=None):
    case = case or {}
    return bool((record.get('nombre') or case.get('nombre_prospecto')) and
                (record.get('contacto') or record.get('correo') or record.get('telefono') or
                 case.get('correo_preferido') or case.get('telefono_preferido')))


def parse_appointment(value):
    if not value: return None
    match = re.search(r'(\d{2}/\d{2}/\d{4})\s*[·-]\s*(\d{2}:\d{2})', str(value))
    if not match: return None
    try: return datetime.strptime(' '.join(match.groups()), '%d/%m/%Y %H:%M')
    except ValueError: return None


def alerts_for(record, case, update, now=None):
    """Only label no-show when explicitly marked; overdue ≠ proved absence."""
    now = now or datetime.now()
    alerts=[]
    lead_id=record.get('id','')
    closed=str(update.get('resultado_comercial') or record.get('etapa') or '').casefold() in ('ganado','perdido')
    owner=update.get('responsable') or case.get('asesor') or record.get('responsable') or ''
    active=bool(case.get('asesor') or record.get('asignacion') == 'Ya asignado a vendedor' or record.get('etapa') == 'SQL')
    if active and not owner and not closed:
        alerts.append(('Rojo','Sin responsable'))
    if record.get('revision_seguimiento') and not closed and update.get('seguimiento_estado') != 'Realizado':
        alerts.append(('Rojo','Seguimiento vencido'))
    appointment=parse_appointment(case.get('reserva') or update.get('cita'))
    appointment_status=update.get('estado_cita','Pendiente')
    if update.get('solicitud_reasignacion') == 'Pendiente':
        alerts.append(('Amarillo','Reasignación solicitada'))
    if appointment_status == 'No asistió':
        alerts.append(('Rojo','No asistió (registrado)'))
    elif appointment and appointment < now and appointment_status == 'Pendiente':
        if appointment + timedelta(hours=24) < now:
            alerts.append(('Rojo','Resultado de cita vencido (>24 h)'))
        else:
            alerts.append(('Amarillo','Cita vencida sin resultado'))
    if case.get('crm_resultado') == 'revision':
        alerts.append(('Amarillo','Duplicado por revisar'))
    if closed and str(update.get('resultado_comercial')) == 'Ganado' and update.get('onboarding','No iniciado') in ('Pendiente','No iniciado'):
        alerts.append(('Amarillo','Onboarding pendiente'))
    return alerts


def scoped_rows(results, cases, updates, country='Todos', team='Todos', seller='Todos'):
    out=[]
    for record in results:
        lid=record['id']; case=cases.get(lid,{}) or {}; update=updates.get(lid,{}) or {}
        team_name=team_of(record,case)
        owner=update.get('responsable') or case.get('asesor') or record.get('responsable') or ''
        if country != 'Todos' and record.get('pais') != country: continue
        if team != 'Todos' and team_name != team: continue
        if seller != 'Todos' and (owner or 'Sin asignar') != seller: continue
        out.append({'lead':record,'case':case,'update':update,'equipo':team_name,'responsable':owner,
                    'alertas':alerts_for(record,case,update)})
    return out


def sample_summary(rows):
    n=len(rows)
    return {
        'leads':n,
        'con_contacto':sum(contact_complete(x['lead'],x['case']) for x in rows),
        'asignados':sum(bool(x['responsable']) for x in rows),
        'citas':sum(bool(x['case'].get('reserva') or x['update'].get('cita')) for x in rows),
        'alertas':sum(bool(x['alertas']) for x in rows),
        'sin_respuesta':sum(bool(x['lead'].get('revision_seguimiento')) for x in rows),
        'sql_candidatos':sum(bool(x['lead'].get('candidato_sql')) for x in rows),
        'ganados':sum(x['update'].get('resultado_comercial')=='Ganado' for x in rows),
    }


def forecast_delta(forecast, actual):
    return None if forecast <= 0 else round((forecast-actual)/forecast*100,1)
