"""Consulta de recuperación de cartera histórica sintética; la ejecución corresponde al CRM."""
from collections import Counter
from pathlib import Path
import pandas as pd
import streamlit as st
from crm_recovery import parse_csv, audit, MANAGERS

SAMPLE=Path(__file__).parent/'data'/'cartera_recuperacion_ejemplo.csv'

def group_action(p):
    field=p['campo']
    if field in ('telefono','correo'): return 'Normalización segura · automatizable con RevOps'
    if field=='seguimiento': return 'Recuperar contacto · tarea urgente en CRM'
    if field=='responsable': return 'Asignar vendedor por país, segmento y capacidad'
    if field=='posible_duplicado': return 'Validar identidad con RevOps antes de fusionar'
    if field=='segmento': return 'Validar PyME / Contador según evidencia'
    if field in ('pais_comercial','pais_telefono'): return 'Verificar país de operación (no asumir por prefijo)'
    return 'Solicitar o confirmar información faltante'

def view():
    st.subheader('Recuperación de oportunidades')
    st.caption('Cartera histórica ficticia · lectura y diagnóstico. En producción los registros y tareas provendrían del CRM conectado; este panel no envía mensajes ni modifica contactos.')
    rows=parse_csv(SAMPLE.read_bytes())
    proposals=audit(rows)
    a,b,c=st.columns(3)
    manager=a.selectbox('Sales Manager',['Todos']+list(MANAGERS),key='rec_manager')
    country=b.selectbox('País',['Todos','México','Colombia','Perú','República Dominicana','Sin país confirmado'],key='rec_country')
    kinds=['Todos','Prioridad alta','Normalización automática','Revisión comercial','Validación RevOps']
    kind=c.selectbox('Enfoque',kinds,key='rec_type')
    filtered=[]
    for p in proposals:
        if manager!='Todos' and p['manager']!=manager:continue
        if country!='Todos' and (p['pais'] if p['pais']!='Sin país' else 'Sin país confirmado')!=country:continue
        category=('Normalización automática' if p['riesgo']=='bajo' else 'Validación RevOps' if p['campo'] in ('posible_duplicado','pais_comercial','pais_telefono') else 'Prioridad alta' if p['campo'] in ('seguimiento','responsable') else 'Revisión comercial')
        if kind!='Todos' and category!=kind:continue
        filtered.append((p,category))
    ids={p['id'] for p,_ in filtered}
    col=st.columns(4)
    numbers=[('Leads por revisar',len(ids)),('Correcciones de formato',len({p['id'] for p,t in filtered if t=='Normalización automática'})),('Recuperación / asignación',len({p['id'] for p,t in filtered if t=='Prioridad alta'})),('Excepciones RevOps',len({p['id'] for p,t in filtered if t=='Validación RevOps'}))]
    for z,(label,val) in zip(col,numbers):z.metric(label,val)
    st.markdown('#### ¿Dónde hay que actuar?')
    action_count=Counter(t for _,t in filtered)
    if action_count:
        st.bar_chart(pd.DataFrame({'Casos':dict(action_count)}),horizontal=True,color='#17A9C3')
    else:st.info('Sin incidencias en esta selección.')
    st.markdown('#### Casos detectados y siguiente paso')
    display=[{'ID':p['id'],'Lead':p['cliente'],'País':p['pais'],'Sales Manager':p['manager'],'Incidencia':p['campo'].replace('_',' '),'Categoría':category,'Evidencia':p['evidencia'],'Siguiente acción':group_action(p)} for p,category in filtered]
    if display:
        event=st.dataframe(display,selection_mode='single-row',on_select='rerun',hide_index=True,use_container_width=True,key='rec_table')
        indexes=list(event.selection.rows)
        if indexes:
            p,_=filtered[indexes[0]]
            with st.container(border=True):
                st.markdown('**Diagnóstico · '+p['cliente']+'**')
                st.write('**Problema:**',p['accion'])
                st.write('**Evidencia:**',p['evidencia'])
                if p['propuesto']:st.write('**Sugerencia:**',p['propuesto'])
                st.info('**Acción a ejecutar en CRM:** '+group_action(p))
                st.caption('La asignación, alertas y correcciones son el siguiente paso de integración con RevOps. No se ha contactado al cliente.')
    st.markdown('#### Plan de mitigación')
    st.write('🟢 **Reglas verificables:** estandarizar formato y completar únicamente datos demostrables.  🟡 **Revisión:** validar país comercial, segmento e identidades ambiguas.  🔴 **Atención urgente:** crear o escalar tareas para los contactos prioritarios sin seguimiento.')
    st.caption('Muestra sintética de 10 registros: no representa la cartera real ni los 14,000 leads mensuales informados en el caso.')
    import io,csv
    if display:
        buf=io.StringIO();w=csv.DictWriter(buf,fieldnames=list(display[0]));w.writeheader();w.writerows(display)
        st.download_button('Descargar diagnóstico (CSV)',buf.getvalue().encode('utf-8-sig'),file_name='recuperacion_oportunidades_demo.csv',mime='text/csv')
