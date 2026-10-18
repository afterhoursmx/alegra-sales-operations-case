"""Pure, scenario-only route metrics. An assisted AI conversation belongs to Con asesor if a seller sold."""
ROUTES=('AI','Con asesor')

def summarize_routes(periods, route='Todos', arpa=400.0):
    if route not in ('Todos', *ROUTES):
        raise ValueError('Ruta desconocida')
    if arpa < 0:
        raise ValueError('ARPA debe ser >= 0')
    active=ROUTES if route=='Todos' else (route,)
    out={}
    for name,counts in periods.items():
        if any(int(counts.get(k,0))<0 for k in ROUTES):
            raise ValueError('Los cierres no pueden ser negativos')
        closings=sum(int(counts.get(k,0)) for k in active)
        out[name]={'cierres':closings,'mrr':closings*arpa}
    return out


def route_alerts(*, reply_on_time, unhandled, failed_handoffs, pending_results, ai_won, advisor_won):
    """Alert, reason and NEXT ACTION. Example thresholds must be validated by RevOps."""
    alerts=[]
    if reply_on_time<.99:
        alerts.append(('🔴 Salud AI: respuestas tardías','Revisar disponibilidad del agente, cola e integración de entrada.'))
    if unhandled>0:
        alerts.append(('🔴 Prospectos sin respuesta','Activar contingencia de asignación humana y revisar fallos de entrada.'))
    if failed_handoffs>0:
        alerts.append(('🟡 Transferencias AI → asesor pendientes','Comprobar asignación y calendario en CRM, y resolver casos abiertos.'))
    if pending_results>0:
        alerts.append(('🟡 Citas sin resultado registrado','Solicitar registro y siguiente acción al asesor responsable.'))
    if ai_won==0:
        alerts.append(('🟡 Sin cierres AI en el escenario','Auditar ruta de compra, producto elegible y fricción de checkout; no atribuir la causa sin investigar.'))
    if advisor_won==0:
        alerts.append(('🟡 Sin cierres Con asesor en el escenario','Verificar oportunidades calificadas, carga y seguimiento; revisar etapa de cierre.'))
    return alerts


def capacity_diagnostics(*, ai_opportunities, advisor_opportunities, ai_won, advisor_won,
                         scheduled_meetings, advisor_count, meetings_capacity_per_advisor):
    """Illustrative funnel and workload, not a staffing optimization or causal estimate."""
    vals=(ai_opportunities, advisor_opportunities, ai_won, advisor_won,
          scheduled_meetings, advisor_count, meetings_capacity_per_advisor)
    if any(v < 0 for v in vals):
        raise ValueError('Los valores no pueden ser negativos')
    if ai_won > ai_opportunities or advisor_won > advisor_opportunities:
        raise ValueError('Los cierres no pueden superar las oportunidades')
    total_capacity=advisor_count*meetings_capacity_per_advisor
    return {
        'ai_conversion':ai_won/ai_opportunities if ai_opportunities else None,
        'advisor_conversion':advisor_won/advisor_opportunities if advisor_opportunities else None,
        'ai_share':ai_won/(ai_won+advisor_won) if ai_won+advisor_won else None,
        'capacity':total_capacity,
        'occupancy':scheduled_meetings/total_capacity if total_capacity else None,
        'over_capacity':max(0,scheduled_meetings-total_capacity),
        'free_slots':max(0,total_capacity-scheduled_meetings),
    }
