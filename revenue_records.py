"""Synthetic contract-level sample. Each row is one fictional closed-won subscription."""
from datetime import date
from collections import defaultdict

CURRENCIES={'México':'MXN','Colombia':'COP','Perú':'PEN','República Dominicana':'DOP'}
# Illustrative NET MONTHLY subscription amounts, not official Alegra prices or ARPA.
PLANS={
 'México':{'PyME':[('Facturación',300),('POS',550),('ERP',1150)],'Contador':[('Contador',650),('Contador Plus',950)]},
 'Colombia':{'PyME':[('Facturación',45000),('Contabilidad',89000),('POS',99000)],'Contador':[('Contador',120000),('Contador Plus',175000)]},
 'Perú':{'PyME':[('Facturación',55),('Gestión',105),('POS',145)],'Contador':[('Contador',165),('Contador Plus',220)]},
 'República Dominicana':{'PyME':[('Facturación',650),('Gestión',1100),('POS',1600)],'Contador':[('Contador',1950),('Contador Plus',2550)]},
}
MANAGERS={'México':'Sales Manager 1','Colombia':'Sales Manager 2','Perú':'Sales Manager 3','República Dominicana':'Sales Manager 3'}

def synthetic_sales():
    """Deterministic period data so all KPI figures come from the exact same rows."""
    sales=[]
    months=[('Anterior',9),('Actual',10)]
    targets={
      'México':{'Anterior':(18,26),'Actual':(28,33)},
      'Colombia':{'Anterior':(10,17),'Actual':(14,21)},
      'Perú':{'Anterior':(7,12),'Actual':(10,14)},
      'República Dominicana':{'Anterior':(5,9),'Actual':(8,11)},
    }
    for country in CURRENCIES:
        for period,month in months:
            ai_n,advisor_n=targets[country][period]
            for route,count in [('AI',ai_n),('Con asesor',advisor_n)]:
                for i in range(count):
                    segment='Contador' if i%5==0 else 'PyME'
                    plans=PLANS[country][segment]
                    product,mrr=plans[(i//3)%len(plans)]
                    source='Cartera recuperada' if i%9==0 else 'Lead nuevo'
                    sales.append({'id':f'{country[:2]}-{month}-{route[:2]}-{i+1:03}',
                       'periodo':period,'fecha':date(2026,month,min(i%27+1,28)).isoformat(),
                       'pais':country,'moneda':CURRENCIES[country], 'segmento':segment,
                       'producto':product,'recorrido':route,'origen':source,
                       'responsable': 'Equipo AI' if route=='AI' else f'Vendedor {(i%8)+1}',
                       'sales_manager':MANAGERS[country], 'mrr_mensual':mrr})
    return sales

def aggregate_sales(rows):
    """Counts and monetary totals derive exclusively from records, never separate sliders."""
    return {'cierres':len(rows),'mrr':sum(r['mrr_mensual'] for r in rows)}

def filter_sales(rows,*,country='México',segment='Ambos',route='Todos',period=None):
    return [r for r in rows if r['pais']==country and (segment=='Ambos' or r['segmento']==segment)
            and (route=='Todos' or r['recorrido']==route) and (period is None or r['periodo']==period)]
