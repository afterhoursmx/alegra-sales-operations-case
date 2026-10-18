import sys
from pathlib import Path
import unittest
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from manager_metrics import team_of, parse_appointment, alerts_for, forecast_delta, scoped_rows, sample_summary

class TestDashboards(unittest.TestCase):
    def test_team_segments(self):
        self.assertEqual(team_of({'segmento':'Pyme'}),'PyME')
        self.assertEqual(team_of({'segmento':'Contador'}),'Contador')
        self.assertEqual(team_of({'segmento':''}),'Sin determinar')
    def test_appointment_parser(self):
        self.assertEqual(parse_appointment('19/10/2026 · 14:00 (México)'),datetime(2026,10,19,14))
        self.assertIsNone(parse_appointment('inventada'))
    def test_appointment_not_assumed_no_show(self):
        record={'id':'L-1','etapa':'MQL','revision_seguimiento':False}
        case={'reserva':'15/10/2026 · 14:00 (México)','asesor':'Vendedor 1'}
        alerts=alerts_for(record,case,{},datetime(2026,10,17,14))
        self.assertIn(('Rojo','Resultado de cita vencido (>24 h)'),alerts)
        recent=alerts_for(record,{'reserva':'16/10/2026 · 18:00 (México)','asesor':'Vendedor 1'}, {}, datetime(2026,10,17,14))
        self.assertIn(('Amarillo','Cita vencida sin resultado'),recent)
        self.assertFalse(any('No asistió' in n for _,n in alerts))
        self.assertIn(('Rojo','No asistió (registrado)'), alerts_for(record,case,{'estado_cita':'No asistió'},datetime(2026,10,17,14)))
    def test_followup_is_alert(self):
        r={'id':'L-2','etapa':'MQL','revision_seguimiento':True}
        self.assertIn(('Rojo','Seguimiento vencido'),alerts_for(r,{},{}))
        self.assertNotIn(('Rojo','Seguimiento vencido'),alerts_for(r,{}, {'seguimiento_estado':'Realizado'}))
    def test_onboarding_after_win(self):
        record={'id':'L-2','etapa':'MQL','revision_seguimiento':False}
        self.assertIn(('Amarillo','Onboarding pendiente'),alerts_for(record,{}, {'resultado_comercial':'Ganado'}))
    def test_scoping(self):
        rec=[{'id':'1','nombre':'A','pais':'México','segmento':'Contador'}, {'id':'2','nombre':'B','pais':'Perú','segmento':'Pyme'}]
        filt=scoped_rows(rec,{}, {}, 'México','Contador')
        self.assertEqual(len(filt),1)
        self.assertEqual(sample_summary(filt)['leads'],1)
    def test_forecast(self):
        self.assertEqual(forecast_delta(100000,73000),27.0)
        self.assertIsNone(forecast_delta(0,100))

if __name__=='__main__': unittest.main()
