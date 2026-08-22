import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk

# 分離したサービスロジッククラスをインポート
from crud_service import CrudAnalyzerService

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")


class CrudMatrixApp(ctk.CTk):

    def __init__(self):
        super().__init__()

        self.title("SQL CRUD Matrix Generator")
        self.geometry("600x420")
        self.resizable(False, False)

        # サービスレイヤーの保持
        self.service = CrudAnalyzerService(dialect="oracle")

        self.target_dir = ""
        self.sql_files = []
        self.is_processing = False

        self._create_widgets()

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self)
        main_frame.pack(padx=20, pady=20, fill="both", expand=True)

        # フォルダ選択
        dir_label = ctk.CTkLabel(
            main_frame, text="対象フォルダ選択", font=ctk.CTkFont(size=14, weight="bold")
        )
        dir_label.pack(anchor="w", padx=15, pady=(15, 5))

        dir_select_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        dir_select_frame.pack(fill="x", padx=15, pady=(0, 10))

        self.entry_dir = ctk.CTkEntry(
            dir_select_frame, placeholder_text="フォルダを選択してください..."
        )
        self.entry_dir.pack(side="left", fill="x", expand=True, padx=(0, 10))

        btn_browse = ctk.CTkButton(
            dir_select_frame, text="参照", width=80, command=self._browse_folder
        )
        btn_browse.pack(side="right")

        # ファイル件数表示
        self.lbl_file_count = ctk.CTkLabel(
            main_frame,
            text="対象: 0 ファイル",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.lbl_file_count.pack(anchor="w", padx=15, pady=(0, 15))

        # 解析実行ボタン
        self.btn_analyze = ctk.CTkButton(
            main_frame,
            text="解析",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=40,
            state="disabled",
            command=self._start_analysis_process,
        )
        self.btn_analyze.pack(fill="x", padx=15, pady=(10, 20))

        # 進捗プログレスバー
        self.lbl_progress = ctk.CTkLabel(
            main_frame, text="待機中", font=ctk.CTkFont(size=12)
        )
        self.lbl_progress.pack(anchor="w", padx=15, pady=(0, 5))

        self.progressbar = ctk.CTkProgressBar(main_frame)
        self.progressbar.pack(fill="x", padx=15, pady=(0, 15))
        self.progressbar.set(0)

    def _browse_folder(self):
        """フォルダ選択イベント（ロジック側でファイル検索を実行）"""
        folder_selected = filedialog.askdirectory()
        if not folder_selected:
            return

        self.target_dir = folder_selected
        self.entry_dir.delete(0, "end")
        self.entry_dir.insert(0, self.target_dir)

        # ロジック側にファイル検索を委託
        self.sql_files = self.service.search_sql_files(self.target_dir)

        count = len(self.sql_files)
        self.lbl_file_count.configure(
            text=f"対象: {count} ファイル",
            text_color="white" if count > 0 else "gray",
        )

        if count > 0:
            self.btn_analyze.configure(state="normal")
            self.lbl_progress.configure(text="準備完了")
        else:
            self.btn_analyze.configure(state="disabled")
            self.lbl_progress.configure(
                text="対象フォルダ内に .sql ファイルが見つかりません"
            )

    def _start_analysis_process(self):
        if not self.sql_files or self.is_processing:
            return

        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="解析結果CSVの保存先を指定",
            initialfile="crud_matrix_result.csv",
        )

        if not save_path:
            return

        self.is_processing = True
        self.btn_analyze.configure(state="disabled")
        self.progressbar.set(0)

        # バックグラウンドスレッドで実行
        threading.Thread(
            target=self._run_analysis, args=(save_path,), daemon=True
        ).start()

    def _run_analysis(self, save_path: str):
        """バックグラウンドでサービス処理を呼び出し"""

        def on_progress(current: int, total: int):
            percent = int((current / total) * 100)
            progress_val = current / total
            status_text = f"{percent}% ({current}/{total}ファイル解析中)"
            # スレッド安全にUI更新
            self.after(
                0, self._update_ui_progress, progress_val, status_text
            )

        try:
            # サービス領域の主処理を実行
            self.service.analyze_and_export(
                self.sql_files, save_path, progress_callback=on_progress
            )
            self.after(0, self._on_analysis_complete, save_path)
        except Exception as e:
            self.after(0, self._on_analysis_error, str(e))

    def _update_ui_progress(self, progress_val: float, status_text: str):
        self.progressbar.set(progress_val)
        self.lbl_progress.configure(text=status_text)

    def _on_analysis_complete(self, save_path: str):
        self.is_processing = False
        self.btn_analyze.configure(state="normal")
        self.lbl_progress.configure(text="解析が完了しました。")

        ans = messagebox.askyesno(
            "処理完了",
            "解析が完了しました。\nCSVファイルを開きますか？",
            parent=self,
        )
        if ans:
            try:
                self.service.open_file_with_default_app(save_path)
            except Exception as e:
                messagebox.showwarning(
                    "警告", f"ファイルを開けませんでした。\n{e}", parent=self
                )

    def _on_analysis_error(self, err_msg: str):
        self.is_processing = False
        self.btn_analyze.configure(state="normal")
        self.lbl_progress.configure(text="エラーが発生し中断しました。")

        messagebox.showerror(
            "エラー",
            f"エラーが発生しましたため処理を中止します。\n\n詳細: {err_msg}",
            parent=self,
        )


if __name__ == "__main__":
    app = CrudMatrixApp()
    app.mainloop()