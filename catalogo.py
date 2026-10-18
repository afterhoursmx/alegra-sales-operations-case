"""Instantánea verificable para la demo; NO consulta precios en tiempo real."""
SOURCE = 'https://alegra.com/mexico/precios/'
VERIFIED_ON = '2026-10-17'
PLANS_MX = {
 'Facturación Inicial': {'mxn_mes':249, 'detalle':'Facturación CFDI ilimitada, 1 usuario. Apropiado si la necesidad principal es facturar bajo demanda.'},
 'Facturación Plus': {'mxn_mes':699, 'detalle':'Facturación e inventario con costo, listas de precios y 3 usuarios.'},
 'POS Lite': {'mxn_mes':199, 'detalle':'Ventas en mostrador, CFDI ilimitada, existencias básicas y 1 sucursal.'},
}


def recommended_plan(needs, country):
    if country != 'México':
        return ''
    if 'Inventarios / ventas' in needs and 'Facturación' in needs:
        p='Facturación Plus'
        reason='porque necesitas facturación y control de inventario con costo; si solo quieres ventas de mostrador conviene evaluar POS.'
    elif 'Inventarios / ventas' in needs:
        p='POS Lite'; reason='porque tu necesidad se concentra en vender en mostrador y manejar existencias básicas, sujeto a confirmar tu operación.'
    elif 'Facturación' in needs:
        p='Facturación Inicial'; reason='porque quieres emitir facturas cuando tus clientes las soliciten sin contratar funciones avanzadas que aún no has pedido.'
    else: return ''
    return (f'**Alegra {p}** — ${PLANS_MX[p]["mxn_mes"]} MXN/mes + IVA (precio de referencia).\n\n'
            f'{PLANS_MX[p]["detalle"]}\n\n'
            f'**Consulta los planes vigentes:** {SOURCE}')
