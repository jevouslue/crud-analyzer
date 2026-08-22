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
        """指定ディレクトリ配下のサブフォルダ内にある .sql ファイルを検索"""
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
        """ジョブ（フォルダ）単位でCRUD操作を取りまとめてマトリクスCSVを出力"""
        total_files = len(sql_files)

        # ジョブごとのCRUDマップ構造:
        # { "Job1": { "EMPLOYEES": {"C", "U"}, "DEPARTMENTS": {"R"} }, ... }
        job_crud_map = defaultdict(lambda: defaultdict(set))

        for idx, file_path in enumerate(sql_files, 1):
            # ファイルの親フォルダ名を Job ID とする
            job_id = os.path.basename(os.path.dirname(file_path))

            query = self._read_sql_file(file_path)
            file_crud_map = self.parser.extract(query)

            # 結果を job_crud_map[job_id][table_name] に統合
            for table_name, ops in file_crud_map.items():
                job_crud_map[job_id][table_name].update(ops)

            if progress_callback:
                progress_callback(idx, total_files)

        # テーブルごとに別行（1テーブル1行）で出力
        self._export_to_job_matrix_csv(job_crud_map, save_path)

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
    def _export_to_job_matrix_csv(job_crud_map: dict, save_path: str) -> None:
        """
        縦軸: JOB_ID
        横軸: C, R, U, D
        セル: テーブル名（同一ジョブで複数テーブルが存在する場合は別々の行として出力）
        """
        records = []
        for job_id in sorted(job_crud_map.keys()):
            tables_map = job_crud_map[job_id]

            # ジョブ内の各テーブルをソートして1行ずつレコードを生成
            for table_name in sorted(tables_map.keys()):
                ops = tables_map[table_name]
                records.append(
                    {
                        "JOB_ID": job_id,
                        "C": table_name if "C" in ops else "",
                        "R": table_name if "R" in ops else "",
                        "U": table_name if "U" in ops else "",
                        "D": table_name if "D" in ops else "",
                    }
                )

        df = pd.DataFrame(records)
        if df.empty:
            df = pd.DataFrame(columns=["JOB_ID", "C", "R", "U", "D"])

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