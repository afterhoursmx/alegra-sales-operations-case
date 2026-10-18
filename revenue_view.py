"""Decision-first revenue panel. All fictional realized sales come from one coherent dataset."""
import pandas as pd
import streamlit as st
from revenue_records import CURRENCIES, synthetic_sales, filter_sales, aggregate_sales
from revenue_model import market_scenarios

DEFAULT_VALUES={
    'México':{'new':4900,'hist':350,'PyME':400,'Contador':700},
    'Colombia':{'new':4200,'hist':300,'PyME':60000,'Contador':100000},
    'Perú':{'new':2800,'hist':200,'PyME':80,'Contador':140},
    'República Dominicana':{'new':2100,'hist':150,'PyME':900,'Contador':1500},
}

def fmt(value,currency):return f'{value:,.0f} {currency}'

def show():
    st.subheader('Revenue comercial')
    st.caption('DEMO · Ventas de ejemplo · Puedes filtrar para explorar decisiones.')
    col1,col2,col3=st.columns(3)
    country=col1.selectbox('País',list(CURRENCIES),key='revenue_country')
    segment=col2.selectbox('Segmento',['Ambos','PyME','Contador'],key='revenue_segment')
    route=col3.selectbox('Recorrido',['Todos','AI','Con asesor'],key='revenue_route')
    currency=CURRENCIES[country]
    sales=synthetic_sales()
    curr=filter_sales(sales,country=country,segment=segment,route=route,period='Actual')
    prev=filter_sales(sales,country=country,segment=segment,route=route,period='Anterior')
    now_stats=aggregate_sales(curr);old_stats=aggregate_sales(prev)
    st.markdown('### Resultado del mes')
    c1,c2,c3=st.columns(3)
    c1.metric('MRR de nuevas ventas',fmt(now_stats['mrr'],currency),
              delta=fmt(now_stats['mrr']-old_stats['mrr'],currency)+' vs. anterior')
    c2.metric('Cierres',now_stats['cierres'],delta=now_stats['cierres']-old_stats['cierres'])
    average=now_stats['mrr']/now_stats['cierres'] if now_stats['cierres'] else 0
    c3.metric('Ingreso mensual medio por cierre',fmt(average,currency))
    st.markdown('### ¿Quién está cerrando?')
    routes=[]
    for label in ('AI','Con asesor'):
        current_route=[r for r in curr if r['recorrido']==label]
        last_route=[r for r in prev if r['recorrido']==label]
        a,b=aggregate_sales(current_route),aggregate_sales(last_route)
        routes.append({'Recorrido':label,'Cierres actuales':a['cierres'],'Cierres anteriores':b['cierres'],
                       'MRR actual':a['mrr'],'Variación MRR':a['mrr']-b['mrr']})
    st.dataframe(pd.DataFrame(routes),hide_index=True,use_container_width=True,
                 column_config={'MRR actual':st.column_config.NumberColumn(f'MRR actual ({currency})',format='%d'),
                                'Variación MRR':st.column_config.NumberColumn(f'Δ MRR ({currency})',format='%d')})
    plot=pd.DataFrame([{'Periodo':name,'AI':sum(r['mrr_mensual'] for r in sales if r['pais']==country and r['periodo']==name and r['recorrido']=='AI' and (segment=='Ambos' or r['segmento']==segment)) if route in ('Todos','AI') else 0,
                        'Con asesor':sum(r['mrr_mensual'] for r in sales if r['pais']==country and r['periodo']==name and r['recorrido']=='Con asesor' and (segment=='Ambos' or r['segmento']==segment)) if route in ('Todos','Con asesor') else 0} for name in ['Anterior','Actual']]).set_index('Periodo')
    st.bar_chart(plot[[c for c in ['AI','Con asesor'] if route=='Todos' or c==route]],stack=False)
    st.markdown('### ¿De dónde vienen los ingresos?')
    recovery=aggregate_sales([r for r in curr if r['origen']=='Cartera recuperada'])
    inbound=aggregate_sales([r for r in curr if r['origen']=='Lead nuevo'])
    left,right=st.columns(2)
    left.metric('Cartera recuperada',fmt(recovery['mrr'],currency),help=f'{recovery["cierres"]} ventas de contactos que ya existían en CRM.')
    right.metric('Leads nuevos',fmt(inbound['mrr'],currency),help=f'{inbound["cierres"]} ventas de contactos nuevos.')
    st.caption(f'{recovery["cierres"]}+{inbound["cierres"]}={now_stats["cierres"]} cierres; cada contrato se cuenta una sola vez.')
    st.markdown('### Alertas y próximas decisiones')
    ai_now=aggregate_sales([r for r in curr if r['recorrido']=='AI'])
    ai_prev=aggregate_sales([r for r in prev if r['recorrido']=='AI'])
    advisor_now=aggregate_sales([r for r in curr if r['recorrido']=='Con asesor'])
    advisor_prev=aggregate_sales([r for r in prev if r['recorrido']=='Con asesor'])
    if route in ('Todos','AI') and ai_now['mrr']<ai_prev['mrr']:
        st.warning('**AI bajó frente al mes anterior.** Revisar producto, calidad de calificación y fricción en la compra.')
    if route in ('Todos','Con asesor') and advisor_now['mrr']<advisor_prev['mrr']:
        st.warning('**Ventas con asesor bajaron.** Revisar etapa de cierre, distribución de oportunidades y capacidad.')
    if not curr:st.warning('Sin cierres en este filtro: verificar volumen, asignación y conversión.')
    elif not (ai_now['mrr']<ai_prev['mrr'] or advisor_now['mrr']<advisor_prev['mrr']):
        delta_total=now_stats['mrr']-old_stats['mrr']
        st.success(f'**MRR {"creció" if delta_total>=0 else "cambió"} {fmt(abs(delta_total),currency)}** frente al mes anterior en este filtro. Revisar qué productos aportaron el cambio en «Ver ventas que originan las cifras».')
    with st.expander('Ver ventas que originan las cifras'):
        st.dataframe(pd.DataFrame(curr)[['id','fecha','pais','segmento','producto','recorrido','origen','responsable','mrr_mensual']],
                     hide_index=True,use_container_width=True)
        st.caption('Los importes mensuales son ejemplos por producto, no precios oficiales ni contratos reales. MRR = suma de membresías mensuales de cada cierre.')
    with st.expander('Proyección hipotética · cambia los supuestos'):
        show_scenario(country,currency,segment)

def show_scenario(country,currency,segment):
    """Separate what-if estimates from coherent fictional contract results."""
    st.caption('Este simulador NO alimenta las ventas de ejemplo que aparecen arriba.')
    vals=DEFAULT_VALUES[country]
    a,b=st.columns(2)
    with a:
        new=st.number_input('Leads nuevos por mes (país seleccionado)',min_value=0,value=vals['new'],step=100,key=f'what_new_{country}')
        old=st.number_input('Oportunidades recuperables',min_value=0,value=vals['hist'],step=10,key=f'what_old_{country}')
        mql=st.slider('Proporción estimada MQL (%)',0,100,70,key=f'what_mql_{country}')/100
    with b:
        pyme=st.number_input(f'Ingreso mensual medio PyME ({currency})',min_value=0,value=vals['PyME'],key=f'what_pyme_{country}')
        contador=st.number_input(f'Ingreso mensual medio Contador ({currency})',min_value=0,value=vals['Contador'],key=f'what_cont_{country}')
        mix=st.slider('Proporción estimada Contador (%)',0,100,25,key=f'what_mix_{country}')/100
    c,d=st.columns(2)
    base_reach=c.slider('Cartera contactada antes (%)',0,100,5,key=f'what_b_{country}')/100
    pilot_reach=d.slider('Cartera contactada ahora (%)',0,100,15,key=f'what_p_{country}')/100
    sql=st.slider('Conversión nueva MQL → SQL (%)',0,100,42,key=f'what_sql_{country}')/100
    rows=[]
    for seg,share,arpa in [('PyME',1-mix,pyme),('Contador',mix,contador)]:
        if segment in ('Ambos',seg):rows.append({'country':country,'segment':seg,'new_leads':new*share,
            'historical_candidates':old*share,'mql_share':mql,'arpa_local':arpa})
    result=market_scenarios(rows,historical_base_reach=base_reach,
            historical_pilot_reach=pilot_reach,inbound_pilot_to_sql=sql)
    old_delta=sum(r['historical_incremental_mrr'] for r in result)
    new_delta=sum(r['inbound_incremental_mrr'] for r in result)
    st.metric('MRR incremental potencial',fmt(old_delta+new_delta,currency))
    st.caption(f'Cartera: +{fmt(old_delta,currency)} · Nuevos: +{fmt(new_delta,currency)}. Hipótesis de conversión, no atribución causal ni ventas realizadas.')
