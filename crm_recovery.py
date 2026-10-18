"""CRM recovery audit for synthetic CSV files. Read-only relative to any external CRM.

All approvals persist locally, with a review trail. This is NOT authentication or
production authorization; the demo manager selector never grants real permissions.
"""
import csv
import io
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

STORE = Path(__file__).parent / 'data' / 'crm_recovery_reviews_demo.json'
FIELDS = ['id','nombre','pais','telefono','correo','segmento','mensaje','etapa','responsable','ultimo_intento','respondio']
MANAGERS = {'Sales Manager 1': {'México'}, 'Sales Manager 2': {'Colombia'}, 'Sales Manager 3': {'Perú','República Dominicana'}}
ALIASES = {'mexico':'México','méxico':'México','colombia':'Colombia','peru':'Perú','perú':'Perú','república dominicana':'República Dominicana','republica dominicana':'República Dominicana'}
CODE_COUNTRY = {'52':'México','57':'Colombia','51':'Perú','1':'República Dominicana / otros países NANP'}


def parse_csv(content):
    """Limit size and rows; preserve raw synthetic row values for transparent comparisons."""
    if len(content) > 2_000_000: raise ValueError('El archivo supera 2 MB. Usa una muestra de prueba.')
    try: text=content.decode('utf-8-sig')
    except UnicodeDecodeError as exc: raise ValueError('El CSV debe estar en UTF-8.') from exc
    reader=csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or 'id' not in reader.fieldnames: raise ValueError('El CSV debe incluir una columna id.')
    if not ('correo' in reader.fieldnames or 'telefono' in reader.fieldnames): raise ValueError('Incluye correo o telefono.')
    rows=[]; ids=set()
    for item in reader:
        if len(rows)>=5000: raise ValueError('Máximo 5,000 registros por auditoría de prueba.')
        if None in item: raise ValueError('CSV mal formado: revisa comas y comillas.')
        row={k:str(item.get(k) or '').strip()[:3000] for k in FIELDS}
        if not row['id'] or row['id'] in ids: raise ValueError('Todos los ID deben ser únicos y no vacíos.')
        ids.add(row['id']); rows.append(row)
    if not rows: raise ValueError('El archivo está vacío.')
    return rows


def manager_for(country):
    country=ALIASES.get(str(country).strip().casefold(), '')
    return next((manager for manager, countries in MANAGERS.items() if country in countries), 'RevOps / sin país comercial')


def audit(rows):
    emails=Counter(x['correo'].lower() for x in rows if x['correo'])
    phones=Counter(re.sub(r'\D','',x['telefono']) for x in rows if len(re.sub(r'\D','',x['telefono']))>=9)
    proposals=[]
    for r in rows:
        rid=r['id']; owner=manager_for(r['pais']); country=r['pais']
        def add(field, current, proposed, reason, risk='medio', action='Revisar', suggested_owner=None):
            proposals.append({'key':hashlib.sha256((rid+'|'+r['correo']+'|'+r['telefono']+'|'+field+'|'+current+'|'+reason).encode()).hexdigest()[:20],
              'id':rid,'cliente':r['nombre'] or rid,'pais':country or 'Sin país','manager':owner,
              'campo':field,'actual':current,'propuesto':proposed,'evidencia':reason,
              'riesgo':risk,'accion':action,'responsable_sugerido':suggested_owner or owner})
        if not r['nombre']: add('nombre','', '', 'No consta el nombre; no se puede inferir.', 'alto','Solicitar información')
        if r['correo']:
            lower=r['correo'].lower()
            if r['correo']!=lower and re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+', lower):
                add('correo',r['correo'],lower,'Normalización reversible de mayúsculas a minúsculas.', 'bajo','Corregir formato')
            if emails[lower]>1: add('posible_duplicado',r['correo'],'','Correo compartido por varios ID. Revisar antes de fusionar.','alto','Escalar a RevOps','RevOps')
        if r['telefono']:
            digits=re.sub(r'\D','',r['telefono'])
            if 10<=len(digits)<=15 and r['telefono'].startswith('+') and r['telefono']!='+'+digits:
                add('telefono',r['telefono'],'+'+digits,'Normalización de puntuación, sin cambiar dígitos.','bajo','Corregir formato')
            if len(digits)>=9 and phones[digits]>1:
                add('posible_duplicado',r['telefono'],'','Teléfono compartido por varios ID. Confirmar antes de fusionar.','alto','Escalar a RevOps','RevOps')
            if not country:
                if r['telefono'].startswith('+') and digits.startswith('52'):
                    add('pais_telefono','','México','El prefijo +52 identifica el país del número, NO el país donde opera el negocio.','medio','Verificar país comercial','RevOps')
                elif r['telefono'].startswith('+') and digits.startswith('57'):
                    add('pais_telefono','','Colombia','Prefijo telefónico +57; no prueba ubicación del negocio.','medio','Verificar país comercial','RevOps')
                elif r['telefono'].startswith('+') and digits.startswith('51'):
                    add('pais_telefono','','Perú','Prefijo telefónico +51; no prueba ubicación del negocio.','medio','Verificar país comercial','RevOps')
        if not r['correo'] and not r['telefono']:
            add('contacto','','','Sin correo ni teléfono; requiere revisión de fuentes autorizadas.', 'alto','Solicitar información')
        if not r['pais'] and not any(p['id']==rid and p['campo']=='pais_telefono' for p in proposals):
            add('pais_comercial','','','No existe evidencia suficiente del país de operación.', 'alto','Solicitar información','RevOps')
        if not r['segmento'] or r['segmento'].casefold() in ('sin determinar','desconocido'):
            msg=r['mensaje'].casefold()
            contador=bool(re.search(r'\b(contador(?:a|es)?|despacho contable|clientes contables)\b',msg))
            pyme=bool(re.search(r'\b(tienda|cafeter[ií]a|ferreter[ií]a|restaurante|mi negocio|negocio de ropa)\b',msg))
            if contador != pyme:
                add('segmento',r['segmento'],'Contador' if contador else 'PyME',
                    'Palabras explícitas en el mensaje: '+r['mensaje'][:140], 'medio','Validar segmento')
            else:
                add('segmento',r['segmento'],'','Historial insuficiente o ambiguo; no clasificar sin evidencia.', 'alto','Solicitar información')
        if r['etapa'].casefold() in ('mql','sql') and not r['responsable']:
            add('responsable','','','Oportunidad sin responsable registrado. Revisar asignación del país y equipo.', 'alto','Asignar responsable')
        if r['ultimo_intento'] and str(r['respondio']).casefold() in ('no','false','0'):
            add('seguimiento',r['ultimo_intento'],'','Existe intento sin respuesta; comprobar antigüedad, autorización y próximos pasos.', 'medio','Revisar seguimiento')
    return proposals


def load_reviews():
    if not STORE.exists(): return {}
    with STORE.open(encoding='utf-8') as f: value=json.load(f)
    if not isinstance(value,dict): raise ValueError('Registro local de revisiones inválido.')
    return value


def save_reviews(reviews):
    STORE.parent.mkdir(exist_ok=True, parents=True)
    tmp=None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=STORE.parent, suffix='.tmp', delete=False) as f:
            tmp=f.name; json.dump(reviews,f,ensure_ascii=False,indent=2)
        os.replace(tmp,STORE)
    finally:
        if tmp and os.path.exists(tmp): os.unlink(tmp)


def review(proposal, actor, decision, new_value=None):
    """Enforce DEMO scope in Python, not only the UI. Not suitable as real authorization."""
    if actor not in MANAGERS: raise ValueError('El perfil simulado debe ser un Sales Manager.')
    if proposal['manager'] != actor: raise PermissionError('Este registro no pertenece al territorio del manager seleccionado.')
    if decision not in ('Aprobado (simulado)','Modificado (simulado)','Escalado a RevOps','Rechazado'):
        raise ValueError('Decisión no permitida.')
    if decision=='Aprobado (simulado)' and (proposal['riesgo']=='alto' or not proposal['propuesto'] or proposal['campo']=='pais_telefono'):
        raise ValueError('Este cambio requiere validación humana adicional; no se puede aplicar tal cual.')
    if decision=='Modificado (simulado)' and not str(new_value or '').strip():
        raise ValueError('Indica el valor corregido y su evidencia en el CRM antes de aprobarlo.')
    if decision=='Modificado (simulado)' and proposal['campo'] in ('posible_duplicado','contacto','seguimiento','responsable'):
        raise ValueError('Este caso requiere un flujo de CRM; no es una corrección de campo automática.')
    reviews=load_reviews()
    reviews[proposal['key']]={'estado':decision,'actor':actor,'fecha_utc':datetime.now(timezone.utc).isoformat(),
       'anterior':proposal['actual'],'propuesto':proposal['propuesto'],
       'final':str(new_value).strip() if decision=='Modificado (simulado)' else proposal['propuesto'],
       'evidencia':proposal['evidencia'],'cliente_id':proposal['id'],'campo':proposal['campo']}
    save_reviews(reviews)
    return reviews[proposal['key']]


def to_csv(rows):
    stream=io.StringIO(); fieldnames=['id','cliente','pais','manager','campo','actual','propuesto','evidencia','riesgo','accion','estado','responsable_sugerido']
    writer=csv.DictWriter(stream,fieldnames=fieldnames);writer.writeheader()
    for r in rows: writer.writerow({k:r.get(k,'') for k in fieldnames})
    return '\ufeff'+stream.getvalue()
