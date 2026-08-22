from collections import defaultdict
import os
from typing import Callable, Dict, List, Optional, Set

from .crud_parser import CrudParser
from .file_finder import SqlFileFinder
from .matrix_exporter import CrudMatrixCsvExporter


class CrudAnalysisFacade:
    """CRUD解析に関する一連のユースケースを取りまとめる窓口クラス"""

    def __init__(self, dialect: str = "oracle"):
        self.parser = CrudParser(dialect=dialect)
        self.finder = SqlFileFinder()
        self.exporter = CrudMatrixCsvExporter()

    def get_sql_files(self, target_dir: str) -> List[str]:
        """ファイル一覧の取得"""
        return self.finder.find_sql_files(target_dir)

    def execute_analysis(
        self,
        sql_files: List[str],
        save_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """解析を一括実行しCSVを出力するコアロジック"""
        total_files = len(sql_files)
        # { "Job1": { "TABLE_A": {"C", "R"}, ... } }
        job_crud_map: Dict[str, Dict[str, Set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )

        for idx, file_path in enumerate(sql_files, 1):
            job_id = os.path.basename(os.path.dirname(file_path))
            sql_text = self.finder.read_file_content(file_path)

            file_crud_map = self.parser.extract(sql_text)

            for table_name, ops in file_crud_map.items():
                job_crud_map[job_id][table_name].update(ops)

            if progress_callback:
                progress_callback(idx, total_files)

        self.exporter.export(job_crud_map, save_path)