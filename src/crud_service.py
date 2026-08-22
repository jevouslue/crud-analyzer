from collections import defaultdict
import os
import platform
import subprocess
from typing import Callable, List, Optional
import pandas as pd

from crud_parser import CrudParser


class CrudAnalyzerService:
    """SQLファイルの検索・解析・CSV出力を担当するサービス領域クラス"""

    def __init__(self, dialect: str = "oracle"):
        self.parser = CrudParser(dialect=dialect)

    @staticmethod
    def search_sql_files(target_dir: str) -> List[str]:
        """指定ディレクトリ配下（サブフォルダ含む）から .sql ファイルを再帰検索"""
        sql_files = []
        if not target_dir or not os.path.exists(target_dir):
            return sql_files

        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.lower().endswith(".sql"):
                    sql_files.append(os.path.join(root, file))
        return sql_files

    def analyze_and_export(
        self,
        sql_files: List[str],
        save_path: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> None:
        """SQLファイルを順次解析し、CSVを出力する（進捗通知対応）"""
        total_files = len(sql_files)
        combined_crud_map = defaultdict(set)

        for idx, file_path in enumerate(sql_files, 1):
            query = self._read_sql_file(file_path)
            file_crud_map = self.parser.extract(query)

            for table, op_set in file_crud_map.items():
                combined_crud_map[table].update(op_set)

            # 進捗をUI（呼び出し元）へ通知
            if progress_callback:
                progress_callback(idx, total_files)

        # CSVの作成・出力
        self._export_to_csv(combined_crud_map, save_path)

    @staticmethod
    def _read_sql_file(file_path: str) -> str:
        """エンコーディング順次試行による読み込み"""
        encodings = ["utf-8", "cp932", "shift_jis", "euc-jp"]
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    @staticmethod
    def _export_to_csv(combined_crud_map: dict, save_path: str) -> None:
        """マトリクス形式でCSV出力"""
        records = []
        for table_name in sorted(combined_crud_map.keys()):
            ops = combined_crud_map[table_name]
            records.append(
                {
                    "TABLE_NAME": table_name,
                    "C": "◯" if "C" in ops else "",
                    "R": "◯" if "R" in ops else "",
                    "U": "◯" if "U" in ops else "",
                    "D": "◯" if "D" in ops else "",
                }
            )

        df = pd.DataFrame(records)
        if df.empty:
            df = pd.DataFrame(columns=["TABLE_NAME", "C", "R", "U", "D"])

        df.to_csv(save_path, index=False, encoding="utf-8-sig")

    @staticmethod
    def open_file_with_default_app(file_path: str) -> None:
        """OS標準の規定アプリでファイルを開く"""
        system_name = platform.system()
        if system_name == "Windows":
            os.startfile(file_path)
        elif system_name == "Darwin":  # macOS
            subprocess.run(["open", file_path])
        else:  # Linux
            subprocess.run(["xdg-open", file_path])