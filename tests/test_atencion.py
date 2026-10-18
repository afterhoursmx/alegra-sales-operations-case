import unittest
from datetime import datetime
from zoneinfo import ZoneInfo
from atencion import (explicit_human_request, human_declined, route_case,
                      assign_advisor, demo_slots, deterministic_fallback)
from engine import text_facts, assess

class TestAtencion(unittest.TestCase):
    def test_no_human_from_urgency(self):
        self.assertFalse(explicit_human_request('Quiero facturar hoy mismo. ¿Qué opción recomiendas?'))
    def test_no_human_from_migration(self):
        self.assertFalse(explicit_human_request('Me urge migrar mi sistema para mañana'))
    def test_human_request(self):
        self.assertTrue(explicit_human_request('Necesito hablar con un asesor mañana por videollamada'))
    def test_human_declined(self):
        self.assertFalse(explicit_human_request('No necesito asesor, yo lo hago por mi cuenta'))
        self.assertTrue(human_declined('No necesito asesor, yo lo hago por mi cuenta'))
    def test_human_declined_sentence(self):
        self.assertTrue(human_declined('No quiero hablar con un asesor'))
    def test_self_service_routing(self):
        case={'lead_id':'L-101','mensajes':[{'rol':'prospecto','texto':'Quiero empezar a facturar hoy'}],'reserva':''}
        route_case(case,{},'México')
        self.assertEqual(case['estado'],'Atención con IA')
        self.assertFalse(case.get('asesor'))
    def test_human_routing_and_notification(self):
        case={'lead_id':'L-101','mensajes':[{'rol':'prospecto','texto':'Quiero una videollamada con un asesor'}],'reserva':''}
        route_case(case,{},'México')
        self.assertEqual(case['estado'],'Pendiente de agenda')
        self.assertEqual(case['asesor'],'Juan López (asesor ficticio)')
        self.assertIn('SIMULACIÓN',case['notificacion'])
    def test_balancing(self):
        cases={'L-101':{'estado':'Pendiente de agenda','asesor':'Juan López (asesor ficticio)'}}
        self.assertEqual(assign_advisor('México',cases,'L-102'),'María Pérez (asesora ficticia)')
    def test_change_to_self_service(self):
        case={'lead_id':'L-101','mensajes':[{'rol':'prospecto','texto':'Quiero una videollamada con un asesor'},{'rol':'prospecto','texto':'Mejor por mi cuenta, no necesito asesor'}],'asesor':'Juan López (asesor ficticio)','reserva':''}
        route_case(case,{},'México')
        self.assertEqual(case['estado'],'Atención con IA')
        self.assertFalse(case['asesor'])
    def test_slots_future_weekdays(self):
        today=datetime(2026,10,17,13,1,tzinfo=ZoneInfo('America/Mexico_City'))
        slots=demo_slots('México',today)
        self.assertGreater(len(slots),0)
        self.assertTrue(all(datetime.fromisoformat(i).weekday()<5 for i in slots))
        self.assertTrue(all(datetime.fromisoformat(i)>today for i in slots))
    def test_response_no_price(self):
        facts=text_facts('Quiero facturar este mes')
        reply=deterministic_fallback('Quiero facturar este mes',facts)
        self.assertNotIn('$',reply)
    def test_engine_compatibility(self):
        lead={'id':'L-101','pais':'México','contacto':'demo@example.com','mensaje':'Quiero facturar este mes','etapa':'MQL','fecha_ingreso':'2026-10-17','intentos':'0'}
        result=assess(lead,facts={'segmento_inferido':'Pyme','necesidad':'Facturación','horizonte':'Este mes','asistencia':'No declarada'},reference_date='2026-10-17')
        self.assertIn('prioridad',result)

if __name__=='__main__':unittest.main()
