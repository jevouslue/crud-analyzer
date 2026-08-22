from typing import Dict, Set
import pandas as pd


class CrudMatrixCsvExporter:
    """JOB ID × CRUD テーブル構造のマトリクスデータをCSVに出力するクラス"""

    def export(
        self,
        job_crud_map: Dict[str, Dict[str, Set[str]]],
        save_path: str,
    ) -> None:
        """
        job_crud_map: { "Job1": { "TABLE_A": {"C", "U"}, ... }, ... }
        1テーブル1行形式でCSVに書き出す
        """
        records = []
        for job_id in sorted(job_crud_map.keys()):
            tables_map = job_crud_map[job_id]

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