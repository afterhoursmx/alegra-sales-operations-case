"""Manager dashboards. All operational data shown comes from local synthetic records."""
from pathlib import Path
from datetime import datetime
import json, os, tempfile
import streamlit as st
from manager_metrics import BASELINE, scoped_rows, sample_summary, parse_appointment, forecast_delta

PATH=Path(__file__).parent/'data'/'manager_updates_demo.json'


def load_updates():
    if not PATH.exists(): return {}
    with PATH.open(encoding='utf-8') as f:
        data=json.load(f)
    if not isinstance(data,dict): raise ValueError('Actualizaciones de managers inválidas: preservar el archivo original')
    return data


def save_updates(updates):
    PATH.parent.mkdir(parents=True,exist_ok=True)
    temp=None
    try:
        with tempfile.NamedTemporaryFile('w',dir=PATH.parent,encoding='utf-8',delete=False,suffix='.tmp') as f:
            temp=f.name
            json.dump(updates,f,ensure_ascii=False,indent=2)
        os.replace(temp,PATH)
    finally:
        if temp and os.path.exists(temp): os.unlink(temp)


def badge(level,message):
    return {'Rojo':'🔴','Amarillo':'🟡','Verde':'🟢'}.get(level,'⚪')+' '+message



MANAGER_COUNTRIES={
    'Sales Manager 1': {'México'},
    'Sales Manager 2': {'Colombia'},
    'Sales Manager 3': {'Perú','República Dominicana'},
}

def filters(results,cases,updates,prefix):
    a,b,c,d=st.columns(4)
    manager=a.selectbox('Sales Manager',['Todos']+list(MANAGER_COUNTRIES),key=prefix+'manager')
    eligible=MANAGER_COUNTRIES.get(manager)
    countries=['Todos']+sorted({str(x.get('pais')) for x in results if x.get('pais') and (eligible is None or x.get('pais') in eligible)})
    country=b.selectbox('País',countries,key=prefix+'country')
    team=c.selectbox('Equipo',['Todos','PyME','Contador','Sin determinar'],key=prefix+'team')
    sellers=['Todos']+sorted({(updates.get(x['id'],{}).get('responsable') or cases.get(x['id'],{}).get('asesor') or x.get('responsable') or 'Sin asignar') for x in results if eligible is None or x.get('pais') in eligible})
    seller=d.selectbox('Vendedor',sellers,key=prefix+'seller')
    scoped=scoped_rows(results,cases,updates,country,team,seller)
    return [x for x in scoped if eligible is None or x['lead'].get('pais') in eligible]


def issue_actions(x):
    issue_names=[v for _,v in x['alertas']]
    if 'Sin responsable' in issue_names:
        return 'Verificar equipo PyME/Contador y solicitar asignación en CRM al manager territorial.'
    if 'Seguimiento vencido' in issue_names:
        return 'Revisar último intento y contactar al vendedor para registrar respuesta o siguiente actividad en CRM.'
    if 'Resultado de cita vencido (>24 h)' in issue_names:
        return 'Solicitar al vendedor confirmar asistencia, resultado y siguiente paso en CRM. Notificación interna al manager si no se resuelve.'
    if 'Reasignación solicitada' in issue_names:
        return 'Revisar conflicto de agenda y reasignar con disponibilidad verificada en el CRM.'
    if 'No asistió (registrado)' in issue_names:
        return 'Verificar causa de inasistencia y ofrecer reagendamiento en el CRM.'
    if 'Cita vencida sin resultado' in issue_names:
        return 'Confirmar con el vendedor si se realizó la cita y registrar su resultado en CRM.'
    if 'Duplicado por revisar' in issue_names:
        return 'Validar coincidencia con RevOps antes de fusionar contactos.'
    if 'Onboarding pendiente' in issue_names:
        return 'Confirmar compra e iniciar bienvenida con responsable humano de la cuenta.'
    if x['equipo']=='Sin determinar':
        return 'Revisar el mensaje y el historial para validar PyME o Contador; si falta evidencia, pedirla.'
    if not x['responsable']:
        return 'Validar necesidad y cobertura, y asignar responsable en el CRM para atender o programar seguimiento autorizado.'
    return 'Revisar próxima actividad comercial y mantener historial actualizado en CRM.'


def lead_detail(x):
    r=x['lead']; case=x['case']; u=x['update']
    st.markdown('#### Diagnóstico del lead · '+r.get('nombre',''))
    a,b,c=st.columns(3)
    a.write('**País:** '+(r.get('pais') or 'Por determinar'))
    b.write('**Equipo:** '+x['equipo'])
    c.write('**Responsable:** '+(x['responsable'] or 'Sin asignar'))
    st.write('**Contexto recibido:**',r.get('mensaje') or 'Sin mensaje registrado')
    st.write('**Necesidad detectada:**',', '.join(case.get('necesidades_detectadas',[])) or r.get('necesidad') or 'Sin determinar')
    st.write('**Etapa:**',u.get('resultado_comercial') if u.get('resultado_comercial') not in (None,'Sin cambio') else r.get('etapa',''))
    st.write('**Último intento:**',r.get('ultimo_intento') or 'Sin registrar')
    st.write('**Motivos:**','; '.join(r.get('motivos',[])) if isinstance(r.get('motivos'),list) else r.get('motivos',''))
    for severity,note in x['alertas']:
        if severity=='Rojo':st.error('🔴 '+note)
        elif severity=='Amarillo':st.warning('🟡 '+note)
    if x['equipo']=='Sin determinar': st.warning('🟡 Segmento sin determinar. No asignar automáticamente sin evidencia.')
    st.info('**Siguiente acción recomendada:** '+issue_actions(x))
    if case.get('no_contactar'): st.warning('Oposición expresa a nuevos contactos. No agendar seguimiento saliente.')
    elif case.get('asesoria_rechazada'): st.info('No solicita asesoría ahora. Se conserva orientación; seguimiento solo si procede y está permitido.')
    if case.get('reserva'):st.write('**Cita simulada:**',case['reserva'])
    if case.get('mensajes'):
        with st.expander('Ver conversación'):
            for m in case['mensajes']:
                st.write(('Prospecto: ' if m['rol']=='prospecto' else 'IA: ')+m['texto'])
    if case.get('reserva') and x['responsable']:
        if u.get('solicitud_reasignacion')=='Pendiente':
            st.warning('Solicitud de reasignación simulada, pendiente de revisión en CRM.')
        elif st.button('Solicitar reasignación de cita (simulación)',key='reasig_'+r['id']):
            updates=load_updates();updates.setdefault(r['id'],{})['solicitud_reasignacion']='Pendiente'
            save_updates(updates);st.rerun()
    st.caption('La ejecución o modificación del contacto corresponde al CRM; esta vista es de consulta.')


def operational(results,cases):
    st.subheader('Cartera de oportunidades')
    st.caption('Leads sintéticos · selecciona una fila para abrir el diagnóstico y la siguiente acción comercial.')
    updates=load_updates(); rows=filters(results,cases,updates,'ops_')
    pending=st.session_state.pop('focus_alert',None)
    if pending: st.session_state['active_alert_filter']=pending
    categories=['Todas','Seguimiento vencido','Sin responsable','Cita vencida sin resultado','Resultado de cita vencido (>24 h)','Reasignación solicitada','No asistió (registrado)','Sin determinar','Duplicado por revisar','Onboarding pendiente']
    if st.session_state.get('active_alert_filter') not in categories: st.session_state['active_alert_filter']='Todas'
    choice=st.selectbox('Filtrar incidencias',categories,key='active_alert_filter')
    if choice!='Todas':
        rows=[x for x in rows if (x['equipo']=='Sin determinar' if choice=='Sin determinar' else any(note==choice for _,note in x['alertas']))]
    if not rows:
        st.info('No hay oportunidades con los filtros seleccionados.');return
    view=[]
    for x in rows:
        r=x['lead']
        issues=', '.join(t for _,t in x['alertas'])
        if x['equipo']=='Sin determinar': issues+=('; ' if issues else '')+'Segmento sin determinar'
        view.append({'ID':r['id'],'Lead':r.get('nombre'), 'País':r.get('pais',''),'Equipo':x['equipo'],'Prioridad':r.get('prioridad',''), 'Vendedor':x['responsable'] or 'Sin asignar','Etapa':r.get('etapa',''),'Situación':issues or 'Al día','Siguiente paso':issue_actions(x)})
    event=st.dataframe(view,hide_index=True,use_container_width=True,selection_mode='single-row',on_select='rerun',key='cartera_tabla')
    inds=list(event.selection.rows)
    chosen=rows[inds[0]] if inds else next((x for x in rows if x['lead']['id']==st.session_state.get('lead_preferido')),rows[0])
    with st.container(border=True):lead_detail(chosen)
    import csv,io
    out=io.StringIO();w=csv.DictWriter(out,fieldnames=list(view[0]));w.writeheader();w.writerows(view)
    st.download_button('Exportar cartera filtrada (CSV)',out.getvalue().encode('utf-8-sig'),file_name='cartera_sintetica.csv',mime='text/csv')


def executive(results,cases):
    st.subheader('Overview gerencial')
    st.caption('Indicadores globales del caso y demostración operativa con registros sintéticos. Los resultados filtrados no representan datos reales de Alegra.')
    st.markdown('#### Forecast vs. cierre real · escenario editable')
    ca,cb=st.columns(2)
    forecast=ca.number_input('Forecast hipotético · MXN',min_value=0,step=10000,value=100000,key='demo_fcst')
    actual=cb.number_input('Cierre hipotético · MXN',min_value=0,step=10000,value=73000,key='demo_real')
    delta=forecast_delta(forecast,actual)
    x,y=st.columns([1,2])
    with x:
        if delta is None:st.warning('Ingresa forecast mayor a cero.')
        else:
            st.metric('Desviación del escenario',f'{delta:+.1f}%')
            if abs(delta)>27:st.error('🔴 Fuera de referencia del caso')
            elif abs(delta)>15:st.warning('🟡 Desviación a investigar')
            else:st.success('🟢 Escenario favorable')
    with y:
        st.bar_chart(__import__('pandas').DataFrame({'MXN':{'Forecast':float(forecast),'Cierre simulado':float(actual)}}),horizontal=True,color='#14A9C8')
    st.markdown('#### Métricas prioritarias del caso · línea base')
    metrics=list(BASELINE.items())
    for group in [metrics[:4],metrics[4:]]:
        cols=st.columns(len(group))
        for col,(k,v) in zip(cols,group):col.metric(k,v)
    st.divider()
    updates=load_updates();rows=filters(results,cases,updates,'exe_');summary=sample_summary(rows)
    st.markdown('#### Gestión de la cartera sintética')
    cards=[('Leads visibles',summary['leads']),('Con contacto',summary['con_contacto']),('Con vendedor',summary['asignados']),('Citas registradas',summary['citas']),('Con alertas',summary['alertas'])]
    cols=st.columns(len(cards))
    for c,(k,v) in zip(cols,cards):c.metric(k,v)
    st.markdown('#### Ejecución y cumplimiento · datos sintéticos')
    today=datetime.now()
    overdue=sum(any(label=='Resultado de cita vencido (>24 h)' for _,label in x['alertas']) for x in rows)
    waiting=sum(any(label=='Cita vencida sin resultado' for _,label in x['alertas']) for x in rows)
    reassigned=sum(x['update'].get('solicitud_reasignacion')=='Pendiente' for x in rows)
    follow=sum(any(label=='Seguimiento vencido' for _,label in x['alertas']) for x in rows)
    ca,cb,cc,cd=st.columns(4)
    ca.metric('Citas sin resultado >24 h',overdue)
    cb.metric('Citas sin resultado <24 h',waiting)
    cc.metric('Reasignaciones solicitadas',reassigned)
    cd.metric('Seguimientos vencidos',follow)
    st.caption('Sin actividad documentada no equivale a inasistencia. Si se vence el plazo, el manager debe verificar el resultado en CRM. El aviso a Teams/Slack sería una integración posterior.')
    st.markdown('#### Riesgos que requieren decisión')
    types=[('Seguimiento vencido','🔴'),('Sin responsable','🔴'),('Resultado de cita vencido (>24 h)','🔴'),('Cita vencida sin resultado','🟡'),('Reasignación solicitada','🟡'),('Sin determinar','🟡')]
    cs=st.columns(3)
    for idx,(label,emoji) in enumerate(types):
        n=sum(x['equipo']=='Sin determinar' if label=='Sin determinar' else any(note==label for _,note in x['alertas']) for x in rows)
        with cs[idx%3]:
            if st.button(f'{emoji} {label} · {n}',key='alert_go_'+str(idx),use_container_width=True):
                st.session_state['focus_alert']=label
                st.session_state['navegar_a']='Cartera de oportunidades'
                st.rerun()
    ca,cb=st.columns(2)
    with ca:
        st.markdown('#### Volumen por segmento')
        teams={k:sum(x['equipo']==k for x in rows) for k in ('PyME','Contador','Sin determinar')}
        st.bar_chart(__import__('pandas').DataFrame({'Leads':teams}),horizontal=True,color='#14A9C8')
    with cb:
        st.markdown('#### Oportunidades por país')
        countries={p:sum(x['lead'].get('pais')==p for x in rows) for p in ('México','Colombia','Perú','República Dominicana')}
        st.bar_chart(__import__('pandas').DataFrame({'Leads':countries}),horizontal=True,color='#0A8B48')
    st.markdown('#### Próximas citas')
    appointments=[];now=datetime.now()
    for x in rows:
        appt=parse_appointment(x['case'].get('reserva') or x['update'].get('cita'))
        if appt and appt>=now:
            appointments.append({'Lead':x['lead']['nombre'],'País':x['lead'].get('pais'),'Equipo':x['equipo'],'Vendedor':x['responsable'] or 'Por asignar','Fecha':appt.strftime('%d/%m/%Y %H:%M')})
    if appointments:
        st.dataframe(sorted(appointments,key=lambda v:v['Fecha']),hide_index=True,use_container_width=True)
    else:
        st.info('No hay citas próximas registradas en la conversación. Ejemplo de visualización futura:')
        from datetime import timedelta
        now_demo=datetime.now()
        while now_demo.weekday()>=5: now_demo+=timedelta(days=1)
        if now_demo.hour>=14:now_demo+=timedelta(days=1)
        while now_demo.weekday()>=5:now_demo+=timedelta(days=1)
        demo_dates=[now_demo.replace(hour=14,minute=0), (now_demo+timedelta(days=1)).replace(hour=10,minute=0)]
        st.dataframe([
            {'Lead':'Cliente demo A','País':'México','Equipo':'PyME','Vendedor':'Vendedor 1','Fecha':demo_dates[0].strftime('%d/%m/%Y %H:%M'),'Estado':'Ejemplo · no reservada'},
            {'Lead':'Cliente demo B','País':'Colombia','Equipo':'Contador','Vendedor':'Vendedor 2','Fecha':demo_dates[1].strftime('%d/%m/%Y %H:%M'),'Estado':'Ejemplo · no reservada'},
        ],hide_index=True,use_container_width=True)

    st.markdown('#### Cartera histórica · recuperación inteligente')
    st.caption('La IA propone prioridades y correcciones; el CRM será la fuente de verdad para tareas y ejecución.')
    if st.button('Ver diagnóstico y recuperación',use_container_width=True):
        st.session_state['navegar_a']='Recuperación de oportunidades';st.rerun()
