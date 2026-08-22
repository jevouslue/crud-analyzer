import os
from typing import List


class SqlFileFinder:
    """指定ディレクトリからのSQLファイル探索および読み込みを担当するクラス"""

    @staticmethod
    def find_sql_files(target_dir: str) -> List[str]:
        """指定フォルダ配下（サブフォルダ含む）から .sql ファイルを探索"""
        sql_files = []
        if not target_dir or not os.path.exists(target_dir):
            return sql_files

        for root, _, files in os.walk(target_dir):
            for file in files:
                if file.lower().endswith(".sql"):
                    sql_files.append(os.path.join(root, file))
        return sorted(sql_files)

    @staticmethod
    def read_file_content(file_path: str) -> str:
        """複数の文字コードを順次試行して安全にテキストを読み込む"""
        encodings = ["utf-8", "cp932", "shift_jis", "euc-jp"]
        for enc in encodings:
            try:
                with open(file_path, "r", encoding=enc) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()