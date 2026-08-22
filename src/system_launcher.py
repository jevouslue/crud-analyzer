import os
import platform
import subprocess


class SystemLauncher:
    """OSに合わせた規定アプリケーション起動を担当するクラス"""

    @staticmethod
    def open_file(file_path: str) -> None:
        """OSの既定アプリで指定ファイルを開く"""
        system_name = platform.system()
        if system_name == "Windows":
            os.startfile(file_path)
        elif system_name == "Darwin":  # macOS
            subprocess.run(["open", file_path])
        else:  # Linux
            subprocess.run(["xdg-open", file_path])