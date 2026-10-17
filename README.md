# Alegra Smart Lead Intelligence — prototipo de caso comercial

> Proyecto independiente y conceptual para un caso de selección. **No es un producto oficial de Alegra**, no está integrado con su CRM ni con sus canales reales. Todo dato utilizado para las pruebas debe ser sintético.

## Problema de negocio (datos proporcionados en el caso)
- 14,000 leads por mes, sin asumir que todos son MQL.
- Tiempo medio de primer contacto: **5.2 horas**.
- Completitud de CRM: **61%**.
- Conversión MQL → SQL: **34%**.
- Conversión SQL → Closed Won: **21%**.
- **38% de las oportunidades perdidas** llevan etiqueta «No responde» (NO 38% de todos los leads).
- Error de forecast: **27%**.

Estos datos son **línea base**, no resultados atribuidos al prototipo. No sabemos todavía qué campos de CRM faltan ni la causa de los tiempos de atención.

## Tesis de solución
Unificar la interpretación comercial y las reglas de decisión entre canales (web, Instagram, WhatsApp, correo y formularios provenientes de publicidad), ofrecer **orientación automatizada útil** y reservar el tiempo humano para quien lo solicite o lo necesite. CRM como fuente de verdad en una implementación posterior.

**Secuencia:** mensaje libre → Gemini interpreta → reglas comerciales deciden → IA orienta o se asigna asesor → calendario/aviso simulado → seguimiento → dashboard.

La urgencia de compra y la necesidad de un asesor **son dimensiones diferentes**. Pedir información o querer contratar este mes no equivale a solicitar una reunión.

## Componentes del proyecto
- `app.py`: interfaz Streamlit, dashboard, nuevos leads, almacenamiento local y atención conversacional de demostración.
- `engine.py`: evaluación determinista de clasificación, seguimiento y fechas.
- `atencion.py`: lógica del canal conversacional, respuestas de Gemini, derivación, asesores/horarios ficticios.
- `data/leads.csv`: 12 registros sintéticos de referencia.
- `tests/test_atencion.py`: pruebas del flujo.
- `data/leads_manuales.json` y `data/conversaciones_demo.json`: **datos generados localmente**, no deben subirse a GitHub.

## Ejecutar en Windows
Requiere Python 3.13 y Streamlit instalado.

```powershell
python -m pip install streamlit
python -m streamlit run app.py
```

La clave Gemini se proporciona temporalmente en la barra lateral de la app; no debe guardarse en el código ni subirse al repositorio. Sin clave, la app usa reglas locales cuando corresponda.

## Estado de validación y deuda técnica
- Se observó el dashboard y almacenamiento de leads funcionando en Windows.
- Las pruebas de lógica de atención estaban aprobadas al generar el paquete de la demo, pero ello **no demuestra** conectividad real con canales externos.
- **Problema abierto de calidad conversacional:** con el lead de Tienda Ropa, Gemini recomendó agendar demasiado pronto, en vez de aclarar si necesita facturación y control de inventarios. Debe responder primero, preguntar únicamente lo necesario y **no mandar a vendedor por defecto**.
- La demo no dispone de catálogo de precios reales verificados; evitar recomendaciones o cotizaciones inventadas.
- Asignaciones, calendarios, citas y notificaciones son **simulados**.
- No se ha medido reducción real de las 5.2 h ni mejora de conversión o forecast.

## Plan de implementación real
1. **Diagnóstico:** auditar campos CRM, distribución/asignación y fuentes reales; identificar causas de demora por etapas.
2. **Piloto:** calificación/atención omnicanal en una muestra, verificación humana, medición de resolución autónoma, tiempo a atención humana y conversión.
3. **Integraciones:** CRM, disponibilidad, mensajería con permisos y calendarios, trazabilidad y escalamiento.
4. **Escala:** mejoras basadas en resultados comparativos, revisión de reglas por Ventas y RevOps.

## Gobierno comercial
La IA interpreta y redacta, las reglas comerciales determinan ruta y excepciones, y la automatización ejecuta únicamente acciones permitidas. Ventas y RevOps **aprueban reglas**, no cada asignación individual. Solicitudes explícitas de atención humana tienen prioridad de derivación.

## Protección de datos
No subir archivos `.env`, tokens, claves Gemini, datos personales reales ni historiales de conversaciones. Los datos de esta demo son ficticios y el almacenamiento local no sustituye las prácticas de seguridad y privacidad de una implementación real.
