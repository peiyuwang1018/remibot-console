"""Application factory for the Qt operator console."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .backend import MockBackend, Ros2Backend
from .config import DEFAULT_DATA_DIR
from .models import RobotState
from .storage import JsonStore
from .ui import MainWindow


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Kitchen arm Qt operator console")
    parser.add_argument("--backend", choices=["mock", "ros2"], default="mock")
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR)
    return parser


def main(argv: list[str] | None = None) -> int:
    args, _ros_args = build_parser().parse_known_args(argv)
    app = QApplication.instance() or QApplication(sys.argv[:1])
    state = RobotState()
    store = JsonStore(args.data_dir)
    store.load_all(state)
    backend = MockBackend(state) if args.backend == "mock" else Ros2Backend(state)
    window = MainWindow(state, backend, store, args.data_dir)
    window.show()
    return app.exec()
