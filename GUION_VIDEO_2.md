# Guion de grabación · Video 2 (5 minutos máximo)

**0:00–0:30 — Problema.** 14,000 leads/mes, 5.2 h primer contacto, 61% completitud CRM. Objetivo: atención temprana, recuperación y visibilidad gerencial.

**0:30–1:05 — Cómo lo construí.** VS Code: Python = lógica; Streamlit = interfaz web/dashboard; Gemini API = interpretación; reglas = decisiones comerciales. Mostrar archivos `app.py`, `atencion.py`, `contactos.py`, `engine.py`. ChatGPT = asistente para código, depuración y pruebas.

**1:05–3:05 — Recorrido funcional.** Streamlit → Atención con IA. Nuevo prospecto con tienda de ropa, nombre y teléfono FICTICIOS; recomendación; acepta llamada; escoge fecha y confirma; mostrar cita local en Overview. Evitar hablar de envíos reales.

**3:05–4:05 — Recuperación y gestión.** Overview, alerta clicable → cartera filtrada → prioridad y siguiente paso. Vista de recuperación histórica sintética.

**4:05–4:35 — Siguiente fase con RevOps.** CRM por API, reglas validadas, responsable y tarea; Outlook/Google Calendar, Teams/Slack y permisos. No están conectados hoy.

**4:35–5:00 — Medición.** Pilotar y comparar vs control: tiempo de contacto humano, completitud, duplicados, asistencia a citas, conversión y MRR. No adjudicar resultados no medidos.

**Antes de grabar:** ocultar Gemini API key; usar datos inventados; comprobar horarios ficticios disponibles; preparar VS Code, dashboard y enlace GitHub.


**Actualización revenue:** reserva unos 40–50 segundos del cierre para abrir
`Impacto en revenue` desde la barra de vistas (o desde Overview). Enseña:
(1) cartera histórica y su tamaño hipotético, (2) conversión de nuevos leads,
(3) incremento hipotético de clientes y MRR vs. escenario base,
(4) metodología de medición control/piloto. No afirmar que los cierres
estimados hayan ocurrido ni que la respuesta IA ≤1 minuto sea el mismo evento
que el primer contacto humano de 5.2 horas.


### Cambio final de enfoque: revenue
En el Video 2, abrir **Impacto en revenue** con **México** preseleccionado; enseñar MRR recuperable de cartera histórica, MRR incremental de leads nuevos y la tabla/proyección en MXN a meses 3, 6 y 12. Deslizar la tabla de metas de CRM y «No responde» indicando que son metas de validación. Cambiar rápidamente a **Colombia** solo para evidenciar COP y segmentación Contador. El análisis estratégico de acciones por fase va en el Video 1. No mezclar primera respuesta automática ≤1 minuto con primera llamada humana (base caso 5.2 h). Mención expresa: resultados son ilustrativos y deben comprobarse mediante cohortes de control vs tratamiento.

### Ajuste final del recorrido
En la grabación prioriza primero **Overview gerencial** (incluye comparación de los tres managers, métricas y alertas), luego **Cartera de oportunidades** y **Recuperación de oportunidades**, después **Impacto en revenue** (base vs. IA; México MXN; Colombia COP). Al final abre **Atención comercial con IA** únicamente para demostrar la atención y agenda ficticia. Las metas a 3, 6 y 12 meses se cuentan en Video 1, no en este dashboard.

Nunca afirmar que las diferencias de MRR son ingresos reales: las tasas piloto, mezcla de productos y ARPA aún son supuestos. La comparación temporal de ventas necesita CRM y facturación conectados.

## Demostración opcional del laboratorio (25–35 s, sustituye parte del recorrido anterior)
En `Impacto en revenue`, seleccionar México: abrir "Laboratorio de escenarios" y enseñar el MRR incremental a meses 3, 6 y 12 y la evolución mensual. Ajustar reducción del tiempo humano al 5% en un checkpoint y mostrar que el ingreso **no sube automáticamente** sin una hipótesis de relación con conversión; cambiar el control de sensibilidad para demostrar un escenario, y explicar que se validaría con cohortes reales. Mantener una escena breve de backend y otra de atención IA, ya que el Video 2 dura cinco minutos.

**Nota sobre velocidad:** respuesta IA objetivo ≤1 minuto desde lanzamiento; no proyectar reducción gradual de primer contacto humano. Los 5.2 h del caso corresponden a primer contacto y deben monitorearse por separado.
