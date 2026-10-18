from revenue_records import synthetic_sales,aggregate_sales,filter_sales,CURRENCIES

def test_unique_sales_and_currencies():
    rows=synthetic_sales()
    assert len({r['id'] for r in rows})==len(rows)
    assert all(r['moneda']==CURRENCIES[r['pais']] for r in rows)
    assert all(r['mrr_mensual']>0 for r in rows)

def test_current_figures_reconcile_by_route_and_origin():
    sales=synthetic_sales()
    for country in CURRENCIES:
        total=filter_sales(sales,country=country,period='Actual')
        ai=filter_sales(sales,country=country,route='AI',period='Actual')
        advisor=filter_sales(sales,country=country,route='Con asesor',period='Actual')
        hist=[r for r in total if r['origen']=='Cartera recuperada']
        new=[r for r in total if r['origen']=='Lead nuevo']
        for group_a,group_b in [(ai,advisor),(hist,new)]:
            assert aggregate_sales(group_a)['mrr']+aggregate_sales(group_b)['mrr']==aggregate_sales(total)['mrr']
            assert len(group_a)+len(group_b)==len(total)

def test_country_and_route_filters():
    rows=synthetic_sales()
    assert all(r['recorrido']=='AI' for r in filter_sales(rows,route='AI',period='Actual'))
    assert all(r['segmento']=='Contador' for r in filter_sales(rows,segment='Contador'))
