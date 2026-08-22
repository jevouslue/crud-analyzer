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
        # { "Job1": { "C": set(), "R": set(), "U": set(), "D": set() }, ... }
        job_crud_map = defaultdict(lambda: defaultdict(set))

        for idx, file_path in enumerate(sql_files, 1):
            # ファイルの親フォルダ名を Job ID とする
            job_id = os.path.basename(os.path.dirname(file_path))

            query = self._read_sql_file(file_path)
            file_crud_map = self.parser.extract(query)

            # { "EMPLOYEES": {"C", "U"}, ... } の結果を job_crud_map に登録
            for table_name, ops in file_crud_map.items():
                for op in ops:
                    job_crud_map[job_id][op].add(table_name)

            if progress_callback:
                progress_callback(idx, total_files)

        # ジョブID × CRUD のマトリクスCSVを出力
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
        セル: テーブル名一覧 (カンマ区切り・ソート済)
        """
        records = []
        for job_id in sorted(job_crud_map.keys()):
            ops = job_crud_map[job_id]

            # 各操作ごとのテーブル一覧をカンマ区切りの文字列に整形
            c_tables = ", ".join(sorted(ops.get("C", [])))
            r_tables = ", ".join(sorted(ops.get("R", [])))
            u_tables = ", ".join(sorted(ops.get("U", [])))
            d_tables = ", ".join(sorted(ops.get("D", [])))

            records.append(
                {
                    "JOB_ID": job_id,
                    "C": c_tables,
                    "R": r_tables,
                    "U": u_tables,
                    "D": d_tables,
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