# Alegra Smart Lead Intelligence — Video 2

Prototipo independiente para el reto Sales Manager. Datos y citas ficticios; no es un producto oficial Alegra.

## Ejecutar

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Abrir `http://localhost:8501`. La clave Gemini se introduce solo en configuración y nunca se comparte.

## Módulos
- `app.py`: Streamlit y coordinación.
- `atencion.py`: conversación Gemini y agendamiento local.
- `contactos.py`: identificación/deduplicación local.
- `engine.py`: reglas y priorización.
- `catalogo.py`: catálogo de referencia.
- `manager_views.py` y `manager_metrics.py`: Overview, métricas y alertas.
- `crm_recovery.py` y `crm_recovery_view.py`: oportunidades históricas sintéticas.
- `data/`: CSV ficticios.
- `tests/`: pruebas automatizadas.

## Límites
Funciona localmente: atención con IA (si hay clave), reglas, dashboard, alertas y reservas **simuladas**. Pendiente con RevOps: CRM corporativo por API, calendarios reales (Outlook/Google), tareas y notificaciones Teams/Slack, permisos y seguimiento efectivo. No se envían correos/WhatsApp ni se actualiza CRM real.

Los valores del caso son línea base, **no mejoras logradas**: 14,000 leads mensuales; MQL→SQL 34%; SQL→Won 21%; primer contacto 5.2 h; CRM completo 61%; 38% de las oportunidades perdidas marcadas «No responde»; error de forecast 27%.

No cargar datos personales, contactos reales ni claves. El selector de manager es simulado, no autenticación real.

## Pruebas

```powershell
python -m pytest -q
```
