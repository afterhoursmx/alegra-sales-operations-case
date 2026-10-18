# Alegra Smart Lead Intelligence — prototipo funcional

**Caso técnico para la evaluación de Sales Manager. No es un producto oficial de Alegra.**

## Propósito comercial

Demostrar una capa de inteligencia para la operación comercial que (1) atiende, orienta y clasifica nuevos prospectos con IA y reglas, (2) detecta oportunidades existentes que requieren recuperación o asignación y (3) ofrece un dashboard para evaluar ejecución, cierres y revenue potencial.

**Modelo de demostración:** todos los leads, vendedores, ventas, citas, monedas e importes son registros de ejemplo. Las simulaciones muestran escenarios posibles, no resultados reales. El caso señala un equipo que ejecuta bien, pero procesos manuales y un CRM poco confiable como fuente de verdad.

## Ejecutar en Windows / PowerShell

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Visitar `http://localhost:8501`. Para habilitar Gemini, introducir una clave válida exclusivamente en la configuración privada de la aplicación. Sin clave, las reglas locales de respaldo permiten un recorrido de demostración. No pegar claves ni datos personales en el repositorio ni mostrar credenciales en la grabación.

## Recorrido recomendado para el video (máximo 5 minutos)

1. **Overview gerencial:** mostrar KPI, filtro de Sales Manager y alertas.
2. **Impacto en revenue:** filtrar México; distinguir cierres `AI` y `Con asesor`; mostrar ingresos por ventas de ejemplo y escenarios futuros como cálculos distintos.
3. **Recuperación de oportunidades:** mostrar prioridades, una fila por prospecto y siguientes acciones.
4. **Atención comercial con IA:** iniciar conversación con datos inventados de una tienda de ropa, solicitar facturación y POS, compartir contacto ficticio, pedir llamada y seleccionar un horario disponible (`lunes a las 4pm`, solo si el slot está ofrecido); confirmar la cita ficticia.
5. **Código en VS Code:** `atencion.py` (flujo y agendamiento), `engine.py` (evaluación), `crm_recovery.py` (prioridades), `revenue_records.py` / `revenue_view.py` (atribución y cifras), `app.py` (orquestación).

## Origen de las cifras de la demo

- **Ventas de ejemplo**: `revenue_records.py` contiene los registros ilustrativos que alimentan ingresos por país, segmento y recorrido (`AI` vs `Con asesor`). Los totales deben obtenerse sumando el ingreso mensual de las ventas filtradas; no se infieren de cifras reales de Alegra.
- **MRR de nuevas ventas**: suma de ingresos mensuales recurrentes asociados a nuevas altas de la cohorte seleccionada. No equivale al MRR total de la compañía ni a efectivo cobrado.
- **Cierres**: número de ventas registradas en ese mismo conjunto ficticio; cada cierre se clasifica una sola vez por recorrido.
- **Variación mensual**: diferencia entre el conjunto de ventas del mes actual y el mes anterior, usando el mismo filtro.
- **Recuperación**: `crm_recovery.py` y `data/cartera_recuperacion_ejemplo.csv` aportan una cartera de muestra; **varias incidencias pueden corresponder a una sola oportunidad**.
- **Proyección / escenarios**: `revenue_model.py` calcula resultados bajo parámetros editables de leads, proporción MQL, tasas de conversión, recuperación y valores de suscripción. **Estos cálculos no deben presentarse como ingresos ya obtenidos**, y no deben sumarse a ingresos reales.
- **Moneda**: México MXN, Colombia COP, Perú PEN, República Dominicana DOP; no sumar monedas distintas sin una tasa de conversión y política de reporte.

## Datos de referencia del caso (no resultados del prototipo)

14,000 leads por mes a nivel global; MQL→SQL 34%; SQL→Closed Won 21%; 5.2 horas hasta primer contacto; 38% de las **oportunidades perdidas** codificadas como «No responde»; completitud de CRM 61%; desviación forecast vs. cierre real 27%. El documento no proporciona distribución por país, tamaño de cartera histórica, promedio mensual real por cuenta o asignaciones reales de managers; los de la demo son supuestos.

## Arquitectura

- `app.py`: coordinación general y Streamlit.
- `atencion.py`: conversación, interpretación de intención, Gemini opcional, modalidades y agenda simulada.
- `contactos.py`: extracción de contactos y deduplicación local.
- `catalogo.py`: orientación de soluciones y referencias comerciales.
- `engine.py`: evaluación y clasificación.
- `crm_recovery.py` y `crm_recovery_view.py`: detección y visualización de prioridades de cartera existente.
- `manager_views.py` y `manager_metrics.py`: vistas y medidas de supervisión.
- `revenue_records.py`, `revenue_view.py`, `revenue_model.py`: datos de ventas simuladas, presentación de ingresos y modelado de escenarios.
- `route_analytics.py` y `route_view.py`: análisis comparativo por recorrido comercial.
- `data/`: CSV de prueba con registros ficticios.
- `tests/`: pruebas automatizadas.

## Límites y siguiente paso con RevOps

**Sí funciona:** aplicación local, reglas de atención y clasificación, demo conversacional (Gemini opcional), agenda y citas ficticias, auditoría local, indicadores y escenarios interactivos con registros de muestra.

**No está integrado:** CRM de Alegra, WhatsApp, correo saliente, Teams/Slack, Outlook/Google Calendar, facturación real, pagos, control de acceso corporativo ni atribución causal del incremento comercial.

Para validar impacto: piloto controlado con cohortes comparables y seguimiento de contacto efectivo, citas realizadas, MQL→SQL, SQL→Won, nuevos clientes y MRR realmente contratado. La respuesta automática rápida y la ejecución humana de citas deben medirse por separado.

## Pruebas

```powershell
python -m pytest -q
```

No enviar información de clientes reales ni exponer claves API.
