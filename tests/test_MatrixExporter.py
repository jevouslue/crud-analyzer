import os
import tempfile
import unittest
import pandas as pd
from src.matrix_exporter import CrudMatrixCsvExporter


class TestCrudMatrixCsvExporter(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.exporter = CrudMatrixCsvExporter()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_export_format(self):
        job_crud_map = {
            "Job1": {
                "DEPARTMENTS": {"R"},
                "EMPLOYEES": {"C", "U"},
            }
        }
        save_path = os.path.join(self.temp_dir.name, "result.csv")
        self.exporter.export(job_crud_map, save_path)

        df = pd.read_csv(save_path, dtype=str).fillna("")
        expected = [
            {"JOB_ID": "Job1", "C": "", "R": "DEPARTMENTS", "U": "", "D": ""},
            {
                "JOB_ID": "Job1",
                "C": "EMPLOYEES",
                "R": "",
                "U": "EMPLOYEES",
                "D": "",
            },
        ]
        self.assertEqual(df.to_dict(orient="records"), expected)


if __name__ == "__main__":
    unittest.main()