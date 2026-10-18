"""Identificación y deduplicación estrictamente LOCAL para simulación comercial."""
import re

EMAIL = re.compile(r'(?<![\w.+-])[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}(?![\w.-])')
PHONE = re.compile(r'(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)')


def extract_contact(text):
    """Extrae correo y número probable sin fabricar identificadores."""
    email = EMAIL.search(text or '')
    phone = None
    for match in PHONE.finditer(text or ''):
        digits = re.sub(r'\D', '', match.group())
        if 10 <= len(digits) <= 15:
            phone = match.group().strip()
            break
    return {'correo': email.group().lower() if email else '', 'telefono': phone or ''}


def normalize_phone(value, country=''):
    digits = re.sub(r'\D', '', str(value or ''))
    if not digits:
        return ''
    # Para México admitimos formato local de 10 dígitos o +52, sin equiparar otros países.
    if country == 'México' and len(digits) == 10:
        return '52' + digits
    return digits


def deduplicate(correo, telefono, country, records, exclude_id=None):
    """Coincidencia exacta correo/teléfono; ante divergencias bloquear la fusión."""
    email = (correo or '').strip().casefold()
    phone = normalize_phone(telefono, country)
    if not email and not phone:
        return {'estado':'sin_identificador','matches':[]}
    email_hits=[]; phone_hits=[]
    for record in records:
        if str(record.get('id')) == str(exclude_id):
            continue
        if record.get('estado_crm') == 'Pre-registro sin CRM':
            continue
        if email and (record.get('correo') or (record.get('contacto') if '@' in str(record.get('contacto','')) else '') or '').strip().casefold() == email:
            email_hits.append(record)
        if phone and normalize_phone(record.get('telefono') or (record.get('contacto') if '@' not in str(record.get('contacto','')) else ''), record.get('pais','')) == phone:
            phone_hits.append(record)
    ids={str(x['id']):x for x in email_hits+phone_hits}
    if len(ids)>1:
        return {'estado':'revision','matches':list(ids.values()),'razon':'Correo y teléfono apuntan a distintos registros, o hay duplicados existentes.'}
    if not ids:
        return {'estado':'nuevo','matches':[]}
    match=next(iter(ids.values()))
    existing_email=(match.get('correo') or (match.get('contacto') if '@' in str(match.get('contacto','')) else '') or '').strip().casefold()
    existing_phone=normalize_phone(match.get('telefono') or (match.get('contacto') if '@' not in str(match.get('contacto','')) else ''),match.get('pais',''))
    if email and existing_email and email != existing_email:
        return {'estado':'revision','matches':[match],'razon':'El teléfono coincide pero el correo es diferente.'}
    if phone and existing_phone and phone != existing_phone:
        return {'estado':'revision','matches':[match],'razon':'El correo coincide pero el teléfono es diferente.'}
    return {'estado':'existente','matches':[match]}


def conservative_enrichment(existing, source, message):
    """Solo completa vacíos; jamás pisa datos ni cambios de etapa existentes."""
    updated=dict(existing)
    for field in ('correo','telefono','contacto'):
        if not str(updated.get(field,'')).strip() and str(source.get(field,'')).strip():
            updated[field]=source[field]
    updated['ultima_consulta_demo']=(message or '')[:500]
    return updated
