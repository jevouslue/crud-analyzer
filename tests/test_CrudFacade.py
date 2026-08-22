import unittest
from unittest.mock import patch
from src.crud_facade import CrudAnalysisFacade
from src.file_finder import SqlFileFinder
from src.matrix_exporter import CrudMatrixCsvExporter


class TestCrudAnalysisFacade(unittest.TestCase):

    def setUp(self):
        self.facade = CrudAnalysisFacade(dialect="oracle")

    @patch.object(SqlFileFinder, "read_file_content")
    @patch.object(CrudMatrixCsvExporter, "export")
    def test_execute_analysis_flow(self, mock_export, mock_read):
        sql_files = ["/path/tests/Job1/Step1.sql"]
        mock_read.return_value = "SELECT * FROM EMPLOYEES;"

        self.facade.execute_analysis(sql_files, "/path/out.csv")

        mock_export.assert_called_once()
        job_map, save_path = mock_export.call_args[0]
        self.assertEqual(job_map["Job1"]["EMPLOYEES"], {"R"})


if __name__ == "__main__":
    unittest.main()