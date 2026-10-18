"""Actionable example dashboard by closing route, with no claim of actual CRM revenue."""
import pandas as pd
import streamlit as st
from route_analytics import ROUTES, summarize_routes, route_alerts, capacity_diagnostics


def show(selected, country, segment):
    st.divider()
    st.markdown('### Cierres y revenue por recorrido comercial')
    st.caption('**SIMULACIÓN EDITABLE**, NO VENTAS REGISTRADAS. AI = compra sin intervención de un asesor comercial; Con asesor = venta en la que participó un asesor (aunque AI haya originado el lead). Una venta solo se cuenta en una ruta. Onboarding humano posterior no cambia esa clasificación.')
    if not selected or len({x['currency'] for x in selected})!=1:
        st.info('Selecciona un país para comparar los recorridos en una moneda local.')
        return
    curr=selected[0]['currency']
    total_leads=sum(r['new_leads'] for r in selected)
    effective_arpa=(sum(r['arpa_local']*r['new_leads'] for r in selected)/total_leads if total_leads else 0)
    mgr={'México':'Sales Manager 1','Colombia':'Sales Manager 2','Perú':'Sales Manager 3','República Dominicana':'Sales Manager 3'}.get(country,'Varios managers')
    st.caption(f'Mercado: {country} · Segmento: {segment} · Territorio ilustrativo: {mgr}. Para comparar por vendedor o manager real necesitaríamos oportunidades y contratos con responsable identificable.')
    a,b,c=st.columns(3)
    with a: route=st.selectbox('Filtrar recorrido',['Todos','AI','Con asesor'],key='route_filter')
    with b: arpa=float(st.number_input(f'Ingreso mensual por cierre · {curr} (hipótesis)',min_value=0.,value=float(round(effective_arpa)),step=10.,key=f'route_arpa_{country}_{segment}'))
    with c: period=st.selectbox('Comparación',['Mes actual vs. anterior'],key='route_period')
    ratio=max(total_leads/4900,0)
    with st.expander('Modificar cierres de ejemplo por recorrido y periodo'):
        x,y=st.columns(2)
        with x:
            st.markdown('**Periodo anterior · ficticio**')
            prev_ai=st.number_input('Cierres AI · anterior',min_value=0,value=int(round(20*ratio)),key='route_prev_ai')
            prev_ad=st.number_input('Cierres Con asesor · anterior',min_value=0,value=int(round(60*ratio)),key='route_prev_ad')
        with y:
            st.markdown('**Periodo actual · ficticio**')
            now_ai=st.number_input('Cierres AI · actual',min_value=0,value=int(round(42*ratio)),key='route_now_ai')
            now_ad=st.number_input('Cierres Con asesor · actual',min_value=0,value=int(round(68*ratio)),key='route_now_ad')
    periods={'Anterior':{'AI':prev_ai,'Con asesor':prev_ad},'Actual':{'AI':now_ai,'Con asesor':now_ad}}
    sm=summarize_routes(periods,route,arpa)
    base=sm['Anterior']; current=sm['Actual']
    delta=current['mrr']-base['mrr']
    k1,k2,k3=st.columns(3)
    k1.metric(f'Cierres · {route}',f'{current["cierres"]:,}',delta=f'{current["cierres"]-base["cierres"]:+,} vs. anterior')
    k2.metric('MRR modelado · actual',f'{current["mrr"]:,.0f} {curr}')
    k3.metric('Variación MRR',f'{delta:+,.0f} {curr}',delta=f'{(delta/base["mrr"]*100):+.1f}%' if base['mrr'] else 'Sin base comparable')
    chart=pd.DataFrame({p:{r:(counts[r] if route in ('Todos',r) else 0) for r in ROUTES} for p,counts in periods.items()}).T
    st.markdown('#### Comparación de cierres · recorrido seleccionado')
    st.bar_chart(chart,stack=False)
    st.dataframe(pd.DataFrame([{'Recorrido':r,'Cierres · anterior':periods['Anterior'][r], 'Cierres · actual':periods['Actual'][r],
         f'MRR actual ({curr})':round(periods['Actual'][r]*arpa),'Cambio de cierres':periods['Actual'][r]-periods['Anterior'][r]}
        for r in ROUTES if route in ('Todos',r)]),hide_index=True,use_container_width=True)
    st.caption('Este desglose ilustra mezcla de cierres, NO prueba revenue incremental causado por la IA. Tampoco se suma al simulador de cohorts: es una vista alternativa de atribución.')

    st.markdown('#### Eficiencia y capacidad · decisiones de dirección')
    st.caption('Ejemplo ajustable. Un cierre AI no prueba por sí solo ahorro de personal: hay que comparar conversión, carga, valor de las cuentas y costos reales.')
    with st.expander('Modificar embudos y carga comercial · escenario ficticio'):
        ca, cb = st.columns(2)
        ai_opps = ca.number_input('Oportunidades gestionadas por AI · periodo',min_value=int(now_ai),value=max(300,int(now_ai)),key='capacity_ai_opps')
        advisor_opps = cb.number_input('Oportunidades con asesor · periodo',min_value=int(now_ad),value=max(400,int(now_ad)),key='capacity_advisor_opps')
        cc,cd,ce=st.columns(3)
        booked=cc.number_input('Citas programadas · periodo',min_value=0,value=120,key='capacity_booked')
        advisors=cd.number_input('Asesores disponibles · escenario',min_value=0,value=8,key='capacity_advisors')
        slots=ce.number_input('Capacidad de citas por asesor · periodo',min_value=0,value=20,key='capacity_slots')
    diag=capacity_diagnostics(ai_opportunities=ai_opps,advisor_opportunities=advisor_opps,
          ai_won=int(now_ai),advisor_won=int(now_ad),scheduled_meetings=booked,
          advisor_count=advisors,meetings_capacity_per_advisor=slots)
    ea,eb,ec,ed=st.columns(4)
    ea.metric('Conversión AI',f"{diag['ai_conversion']:.1%}" if diag['ai_conversion'] is not None else 'Sin base')
    eb.metric('Conversión Con asesor',f"{diag['advisor_conversion']:.1%}" if diag['advisor_conversion'] is not None else 'Sin base')
    ec.metric('Cierres del recorrido AI',f"{diag['ai_share']:.1%}" if diag['ai_share'] is not None else 'Sin cierres')
    ed.metric('Ocupación de agenda',f"{diag['occupancy']:.0%}" if diag['occupancy'] is not None else 'Sin capacidad')
    if diag['over_capacity']:
        st.error(f"**Capacidad de agenda insuficiente:** {diag['over_capacity']} citas por encima del máximo ilustrativo. Revisar reparto, bloques y cobertura antes de aceptar más reservas.")
    elif diag['occupancy'] is not None and diag['occupancy'] < .6:
        st.info(f"**Capacidad disponible:** {diag['free_slots']} espacios ilustrativos. Investigar si falta demanda calificada o si los asesores están atendiendo trabajo no reflejado en agenda; no inferir plantilla sobrante.")
    elif diag['occupancy'] is not None:
        st.info('**Capacidad:** la agenda está dentro del límite ilustrativo. Contrastar duración real de reuniones, prospección y complejidad de cartera antes de cambiar la distribución de oportunidades.')
    else:
        st.warning('No hay capacidad de asesores registrada en el escenario. Verificar cobertura y transferencias AI → asesor.')
    if diag['ai_conversion'] is not None and diag['advisor_conversion'] is not None:
        if diag['ai_conversion'] > diag['advisor_conversion']:
            st.caption('Revisar qué productos y perfiles convierten por AI, sin asumir equivalencia de dificultad, ticket o fuente de leads.')
        else:
            st.caption('Revisar el mix de oportunidades que llegan a asesores y qué fricciones impiden el cierre en AI; tasas sin ajustar por mix no son comparables causalmente.')
    st.caption('Para decisiones de presupuesto o plantilla faltan: fuente/campaña y CAC, horas realmente trabajadas, capacidad por segmento, costos operativos, ARPA neto, retención y resultados longitudinales. Esto NO automatiza cambios de plantilla.')

    st.markdown('#### Salud de automatización y alertas accionables')
    st.caption('Métricas de salud editables de demostración. Los umbrales deben acordarse con RevOps; la atención inicial AI y el cumplimiento humano se supervisan por separado.')
    with st.expander('Editar salud de automatización · datos ficticios',expanded=False):
        ca,cb,cc,cd=st.columns(4)
        reply=ca.slider('% respuestas AI ≤1 minuto',0,100,98,1,key='health_reply')/100
        unhandled=cb.number_input('Prospectos sin respuesta',min_value=0,value=2,key='health_unhandled')
        handoffs=cc.number_input('Transferencias sin responsable confirmado',min_value=0,value=3,key='health_handoffs')
        pending=cd.number_input('Citas sin resultado >24 h',min_value=0,value=4,key='health_pending')
    h1,h2,h3,h4=st.columns(4)
    h1.metric('Respuesta AI ≤1 min',f'{reply:.0%}')
    h2.metric('Sin respuesta',unhandled)
    h3.metric('Transferencias pendientes',handoffs)
    h4.metric('Resultados de cita vencidos',pending)
    alerts=route_alerts(reply_on_time=reply,unhandled=unhandled,failed_handoffs=handoffs,pending_results=pending,
                        ai_won=now_ai,advisor_won=now_ad)
    if route=='AI':
        alerts=[a for a in alerts if ('AI' in a[0] or 'respuesta' in a[0] or 'Transferencias' in a[0])]
    elif route=='Con asesor':
        alerts=[a for a in alerts if ('asesor' in a[0] or 'Citas' in a[0] or 'Transferencias' in a[0])]
    if alerts:
        for title,action in alerts:
            with st.container(border=True):
                st.markdown('**'+title+'**')
                st.write('**Siguiente acción:** '+action)
    else:
        st.success('No hay alertas bajo los umbrales de este escenario. Revisar igualmente tendencias y datos de CRM.')
    st.info('**Para decidir:** filtra AI si quieres revisar conversión autónoma, fricciones del recorrido y fallas de automatización; filtra Con asesor para detectar necesidades de agenda, cumplimiento y cierre. Consulta país y segmento antes de comparar porque el MRR por cuenta puede ser diferente.')
