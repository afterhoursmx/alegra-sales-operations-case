"""Illustrative cohort economics. Never present scenario projections as realized income."""

MONTHLY_LEADS = 14_000
BASE_MQL_TO_SQL = .34
BASE_SQL_TO_WON = .21


def revenue_scenarios(*, historical_candidates=1000, base_reach=.05, pilot_reach=.15,
                      historical_to_sql=.30, historical_sql_to_won=.21,
                      mql_share=.70, pilot_mql_to_sql=.42, new_sql_to_won=.21,
                      monthly_value=432.0, monthly_leads=MONTHLY_LEADS):
    """Return hypothetical cohort estimates. Reach is effective re-engagement rate.

    Historical: same existing eligible cohort under baseline/pilot. Both groups use
    comparable reached→SQL and SQL→Won rates. New: same inbound monthly MQL cohort,
    changing only MQL→SQL; SQL→Won held fixed, not double-counting historic demand.
    """
    proportions=(base_reach,pilot_reach,historical_to_sql,historical_sql_to_won,
                 mql_share,pilot_mql_to_sql,new_sql_to_won)
    if any(x<0 or x>1 for x in proportions): raise ValueError('Las tasas deben estar entre 0% y 100%.')
    if historical_candidates<0 or monthly_leads<0 or monthly_value<0:
        raise ValueError('El volumen y la membresía no pueden ser negativos.')
    historical_base=historical_candidates*base_reach*historical_to_sql*historical_sql_to_won
    historical_pilot=historical_candidates*pilot_reach*historical_to_sql*historical_sql_to_won
    monthly_mql=monthly_leads*mql_share
    new_base=monthly_mql*BASE_MQL_TO_SQL*new_sql_to_won
    new_pilot=monthly_mql*pilot_mql_to_sql*new_sql_to_won
    return {
        'historical':{'eligible':historical_candidates,'base_reached':historical_candidates*base_reach,
                      'pilot_reached':historical_candidates*pilot_reach,
                      'base_wins':historical_base,'pilot_wins':historical_pilot,
                      'incremental_wins':historical_pilot-historical_base,
                      'base_mrr':historical_base*monthly_value,'pilot_mrr':historical_pilot*monthly_value,
                      'incremental_mrr':(historical_pilot-historical_base)*monthly_value},
        'inbound':{'leads':monthly_leads,'mql':monthly_mql,'base_wins':new_base,
                   'pilot_wins':new_pilot,'incremental_wins':new_pilot-new_base,
                   'base_mrr':new_base*monthly_value,'pilot_mrr':new_pilot*monthly_value,
                   'incremental_mrr':(new_pilot-new_base)*monthly_value},
        'incremental_mrr_total':(historical_pilot-historical_base+new_pilot-new_base)*monthly_value,
        'incremental_clients_total':historical_pilot-historical_base+new_pilot-new_base,
    }


MARKETS = {
    'México': 'MXN',
    'Colombia': 'COP',
    'Perú': 'PEN',
    'República Dominicana': 'DOP',
}
SEGMENTS = ('PyME', 'Contador')


def market_scenarios(rows, *, historical_base_reach=.05, historical_pilot_reach=.15,
                     historical_to_sql=.30, historical_to_won=.21,
                     inbound_baseline_to_sql=.34, inbound_pilot_to_sql=.42,
                     inbound_to_won=.21):
    """Per-market hypothetical cohort economics, intentionally never summing currencies.

    rows: country, segment, new_leads, mql_share, historical_candidates, arpa_local.
    Each country/segment pair must be unique. If plan value differs, input separately.
    """
    rates=(historical_base_reach,historical_pilot_reach,historical_to_sql,
           historical_to_won,inbound_baseline_to_sql,inbound_pilot_to_sql,inbound_to_won)
    if any(not 0 <= rate <= 1 for rate in rates):
        raise ValueError('Las tasas deben estar entre 0 y 1.')
    results=[]
    seen=set()
    for row in rows:
        country=row['country']; segment=row['segment']
        if country not in MARKETS or segment not in SEGMENTS: raise ValueError('País o segmento desconocido.')
        key=(country,segment)
        if key in seen: raise ValueError('Combinación país/segmento duplicada.')
        seen.add(key)
        leads=float(row['new_leads']); share=float(row['mql_share'])
        historical=float(row['historical_candidates']); arpa=float(row['arpa_local'])
        if leads < 0 or historical < 0 or arpa < 0 or not 0 <= share <= 1:
            raise ValueError('Volúmenes y ARPA no negativos, MQL entre 0 y 1.')
        hist_wins=(historical_pilot_reach-historical_base_reach)*historical*historical_to_sql*historical_to_won
        inbound_wins=leads*share*(inbound_pilot_to_sql-inbound_baseline_to_sql)*inbound_to_won
        results.append({'country':country,'segment':segment,'currency':MARKETS[country],
                        'new_leads':leads,'historical_candidates':historical,
                        'arpa_local':arpa,'historical_incremental_wins':hist_wins,
                        'inbound_incremental_wins':inbound_wins,
                        'historical_incremental_mrr':hist_wins*arpa,
                        'inbound_incremental_mrr':inbound_wins*arpa,
                        'incremental_mrr_local':(hist_wins+inbound_wins)*arpa})
    return results


def trajectory_scenarios(rows, *, country='México', segment='Ambos segmentos',
                         historical_base_reach=.05, historical_to_sql=.30, historical_to_won=.21,
                         inbound_to_won=.21, months=(3, 6, 12),
                         checkpoints=None):
    """Hypothetical incremental MRR at checkpoints: one recoverable historical cohort,
    plus monthly inbound cohorts at each month's assumed conversion. Zero churn,
    unchanged ARPA, unchanged volumes. Not causal/actual revenue or cash flow.
    """
    if checkpoints is None:
        checkpoints={0: {'reach': historical_base_reach,'mql_sql': .34},
                     3: {'reach': .10,'mql_sql': .37},
                     6: {'reach': .13,'mql_sql': .39},
                     12:{'reach': .15,'mql_sql': .42}}
    if 0 not in checkpoints or any(m not in checkpoints for m in (3,6,12)):
        raise ValueError('Se requieren puntos de mes 0, 3, 6 y 12.')
    for point in checkpoints.values():
        if any(not (0 <= point[k] <= 1) for k in ('reach','mql_sql')):
            raise ValueError('Tasas fuera de 0–100%.')
    max_month=max(months)
    if max_month>12 or min(months)<1: raise ValueError('Horizonte entre 1 y 12 meses.')
    selected=[r for r in rows if r['country']==country and (segment=='Ambos segmentos' or r['segment']==segment)]
    if country not in MARKETS: raise ValueError('País desconocido')
    months_recovered_mrr={}; inbound_cumulative=0.0; output=[]
    historical_base=sum(float(r['historical_candidates'])*historical_base_reach*historical_to_sql*historical_to_won*float(r['arpa_local']) for r in selected)
    for month in range(1,max_month+1):
        lo=max(x for x in checkpoints if x<=month)
        hi=min(x for x in checkpoints if x>=month)
        def interpolate(k):
            if lo==hi: return checkpoints[lo][k]
            return checkpoints[lo][k]+(checkpoints[hi][k]-checkpoints[lo][k])*(month-lo)/(hi-lo)
        current_reach=interpolate('reach'); current_mql_sql=interpolate('mql_sql')
        # One historical backlog cohort tackled only once; use current cumulative reach at each milestone.
        historical_mrr=sum(float(r['historical_candidates'])*current_reach*historical_to_sql*historical_to_won*float(r['arpa_local']) for r in selected)-historical_base
        inbound_increment=sum(float(r['new_leads'])*float(r['mql_share'])*(current_mql_sql-.34)*inbound_to_won*float(r['arpa_local']) for r in selected)
        inbound_cumulative+=inbound_increment
        if month in months:
            output.append({'month':month,'historical_incremental_mrr':historical_mrr,
                           'inbound_cohort_incremental_mrr':inbound_increment,
                           'inbound_accumulated_mrr':inbound_cumulative,
                           'incremental_run_rate_mrr':historical_mrr+inbound_cumulative,
                           'annualized_incremental_run_rate':(historical_mrr+inbound_cumulative)*12,
                           'reach':current_reach,'mql_sql':current_mql_sql})
    return output


def decision_forecast(rows, *, country='México', segment='Ambos segmentos',
                      checkpoints=None, ai_response_minutes=1.0,
                      historical_to_sql=.30, historical_to_won=.21, inbound_to_won=.21,
                      baseline_hours=5.2, baseline_mql_to_sql=.34, baseline_historical_reach=.05,
                      baseline_no_response=.38, baseline_crm_complete=.61):
    """12-month illustrative monthly incremental MRR vs unchanged baseline.

    First AI response is a fixed operating target, not a gradually improved metric.
    It does not directly imply a conversion lift.
    The same historical backlog is reactivated cumulatively, not each month.
    New inbound cohorts add incremental MRR if retained (zero churn assumption).
    Changes to No responde and CRM completeness are displayed as KPIs, not used
    as independent revenue multipliers (would double count conversion effects).
    """
    if checkpoints is None:
        checkpoints={0:{'mql_lift_pp':0,'reach':.05,'no_response':.38,'crm_complete':.61},
                     3:{'mql_lift_pp':3,'reach':.10,'no_response':.35,'crm_complete':.75},
                     6:{'mql_lift_pp':5,'reach':.13,'no_response':.32,'crm_complete':.85},
                     12:{'mql_lift_pp':8,'reach':.15,'no_response':.28,'crm_complete':.95}}
    if country not in MARKETS: raise ValueError('País desconocido')
    if any(m not in checkpoints for m in (0,3,6,12)): raise ValueError('Se necesitan 0, 3, 6 y 12 meses')
    if ai_response_minutes <= 0 or baseline_hours < 0: raise ValueError('Tiempo inválido')
    for cp in checkpoints.values():
        if not 0<=cp['reach']<=1 or not 0<=cp['no_response']<=1 or not 0<=cp['crm_complete']<=1:
            raise ValueError('Tasas fuera de rango')
        if not 0 <= cp['mql_lift_pp'] <= 100: raise ValueError('Conversión inválida')
    selected=[r for r in rows if r['country']==country and (segment=='Ambos segmentos' or r['segment']==segment)]
    hist_base=sum(float(r['historical_candidates'])*baseline_historical_reach*historical_to_sql*historical_to_won*float(r['arpa_local']) for r in selected)
    base_mrr_per_inbound_cohort=sum(float(r['new_leads'])*float(r['mql_share'])*baseline_mql_to_sql*inbound_to_won*float(r['arpa_local']) for r in selected)
    cumulative_new=0.0; out=[]
    def interp(month,key):
        left=max(t for t in checkpoints if t<=month)
        right=min(t for t in checkpoints if t>=month)
        if left==right:return checkpoints[left][key]
        return checkpoints[left][key]+(checkpoints[right][key]-checkpoints[left][key])*(month-left)/(right-left)
    for month in range(1,13):
        hours=baseline_hours  # línea base, NO se proyecta primer contacto humano sin datos
        manual_pp=interp(month,'mql_lift_pp')
        conversion=min(1.0,baseline_mql_to_sql+manual_pp/100.0)
        reached=interp(month,'reach')
        hist_gain=sum(float(r['historical_candidates'])*(reached-baseline_historical_reach)*historical_to_sql*historical_to_won*float(r['arpa_local']) for r in selected)
        new_gain=sum(float(r['new_leads'])*float(r['mql_share'])*(conversion-baseline_mql_to_sql)*inbound_to_won*float(r['arpa_local']) for r in selected)
        cumulative_new+=new_gain
        baseline=(base_mrr_per_inbound_cohort*month)+hist_base
        out.append({'month':month,'hours':hours,'ai_response_minutes':ai_response_minutes,'mql_sql':conversion,
                    'no_response':interp(month,'no_response'),'crm_complete':interp(month,'crm_complete'),
                    'historical_reach':reached,'new_incremental_cohort_mrr':new_gain,
                    'new_incremental_accumulated_mrr':cumulative_new,'historical_incremental_mrr':hist_gain,
                    'incremental_mrr':cumulative_new+hist_gain,
                    'baseline_mrr':baseline,'projected_mrr':baseline+cumulative_new+hist_gain})
    return out
