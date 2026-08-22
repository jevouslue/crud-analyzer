import os
import tempfile
import unittest
from src.file_finder import SqlFileFinder


class TestSqlFileFinder(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_find_sql_files_recursive(self):
        job1_dir = os.path.join(self.temp_dir.name, "Job1")
        os.makedirs(job1_dir)

        sql_file = os.path.join(job1_dir, "step1.sql")
        txt_file = os.path.join(job1_dir, "readme.txt")

        for p in [sql_file, txt_file]:
            with open(p, "w", encoding="utf-8") as f:
                f.write("SELECT 1 FROM DUAL;")

        found_files = SqlFileFinder.find_sql_files(self.temp_dir.name)
        self.assertEqual(found_files, [sql_file])

    def test_read_file_content_sjis(self):
        file_path = os.path.join(self.temp_dir.name, "sjis.sql")
        content = "SELECT * FROM 社員;"
        with open(file_path, "w", encoding="cp932") as f:
            f.write(content)

        self.assertEqual(SqlFileFinder.read_file_content(file_path), content)


if __name__ == "__main__":
    unittest.main()