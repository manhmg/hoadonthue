import sys
import os
import logging
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon

# Ensure stdout is utf-8 on Windows if attached
if sys.platform == "win32":
    if sys.stdout is not None:
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if sys.stderr is not None:
        try:
            sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

# Add current directory to sys.path (supports PyInstaller frozen mode)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from src.ui.main_window import MainWindow

def setup_logging():
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "app.log"

    handlers = [logging.FileHandler(log_file, encoding="utf-8")]
    if sys.stdout is not None:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers
    )

def main():
    setup_logging()
    
    # Set Windows AppUserModelID so taskbar displays the custom logo
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PhuongNguyen.QuanLyHoaDon.v1.0")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("QuanLyHoaDonPhuongNguyen")

    icon_path = (Path(sys._MEIPASS) / "assets" / "logo.ico") if hasattr(sys, '_MEIPASS') else (BASE_DIR / "assets" / "logo.ico")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
