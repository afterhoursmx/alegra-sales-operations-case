import csv
import io
import unittest
from unittest.mock import patch
import tempfile
from pathlib import Path
import crm_recovery as r

class CRMRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.rows=[{'id':'1','nombre':'Cliente 1','pais':'México','telefono':'+52 (477) 000 0000','correo':'ABC@EJEMPLO.COM','segmento':'','mensaje':'Tengo una tienda de ropa','etapa':'MQL','responsable':'Vendedor 1','ultimo_intento':'','respondio':''},
            {'id':'2','nombre':'Cliente 2','pais':'Perú','telefono':'+51 999 000 100','correo':'cliente2@ejemplo.com','segmento':'Contador','mensaje':'Soy contador','etapa':'SQL','responsable':'','ultimo_intento':'','respondio':''},
            {'id':'3','nombre':'Cliente 3','pais':'','telefono':'+52 477 000 0001','correo':'cliente3@ejemplo.com','segmento':'PyME','mensaje':'Opero en Perú','etapa':'MQL','responsable':'','ultimo_intento':'','respondio':''}]
    def test_country_not_inferred_as_business(self):
        result=r.audit(self.rows)
        p=next(x for x in result if x['id']=='3' and x['campo']=='pais_telefono')
        self.assertEqual(p['propuesto'],'México')
        self.assertEqual(p['manager'],'RevOps / sin país comercial')
        self.assertFalse(any(x['id']=='3' and x['campo']=='pais' for x in result))
    def test_safe_proposal(self):
        p=next(x for x in r.audit(self.rows) if x['id']=='1' and x['campo']=='correo')
        self.assertEqual(p['propuesto'],'abc@ejemplo.com');self.assertEqual(p['riesgo'],'bajo')
    def test_scope_and_audit(self):
        p=next(x for x in r.audit(self.rows) if x['id']=='1' and x['campo']=='correo')
        with tempfile.TemporaryDirectory() as d,patch.object(r,'STORE',Path(d)/'review.json'):
            with self.assertRaises(PermissionError): r.review(p,'Sales Manager 2','Aprobado (simulado)')
            r.review(p,'Sales Manager 1','Aprobado (simulado)')
            self.assertEqual(r.load_reviews()[p['key']]['estado'],'Aprobado (simulado)')
    def test_high_risk_not_approved(self):
        p=next(x for x in r.audit(self.rows) if x['id']=='2' and x['campo']=='responsable')
        with self.assertRaises(ValueError):r.review(p,'Sales Manager 3','Aprobado (simulado)')
    def test_dup_detection(self):
        rows=[dict(x) for x in self.rows]; rows[1]['correo']=rows[0]['correo']
        self.assertTrue(any(x['campo']=='posible_duplicado' for x in r.audit(rows)))
    def test_csv_roundtrip(self):
        buff=io.StringIO();w=csv.DictWriter(buff,fieldnames=r.FIELDS);w.writeheader();w.writerows(self.rows)
        parsed=r.parse_csv(buff.getvalue().encode());self.assertEqual(len(parsed),3)
        with self.assertRaises(ValueError):r.parse_csv(b'bad,data\n1,2')

if __name__=='__main__': unittest.main()
