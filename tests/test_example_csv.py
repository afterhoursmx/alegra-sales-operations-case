import unittest
from pathlib import Path
from crm_recovery import parse_csv, audit
class ExampleCSV(unittest.TestCase):
    def test_example_parses_and_audits(self):
        path=Path(__file__).parents[1]/'data'/'cartera_recuperacion_ejemplo.csv'
        rows=parse_csv(path.read_bytes())
        self.assertEqual(10,len(rows))
        self.assertGreater(len(audit(rows)),15)
        self.assertIn('tengo',rows[0]['mensaje'].lower())
