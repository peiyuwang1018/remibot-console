"""Repository-level launcher for the Qt kitchen arm operator console."""

from pathlib import Path
import sys

QT_PROJECT_DIR = Path(__file__).resolve().parent / "qt_operator_console"
sys.path.insert(0, str(QT_PROJECT_DIR))

from kitchen_qt.app import main


if __name__ == "__main__":
    raise SystemExit(main())
