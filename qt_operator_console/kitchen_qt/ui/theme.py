"""Qt stylesheet for a modern operator-console look."""

STYLE_SHEET = """
QWidget {
    background: #0f141c;
    color: #e6ebf4;
    font-family: "Segoe UI", "Microsoft YaHei", "Noto Sans", sans-serif;
    font-size: 14px;
}
QLabel {
    background: transparent;
}
QMainWindow, QDialog {
    background: #0f141c;
}
QFrame#TopBar, QFrame#Panel {
    background: #151b25;
    border: 1px solid #2e3a4d;
    border-radius: 8px;
}
QLabel#SectionTitle {
    background: transparent;
    color: #b7c5dc;
    font-size: 15px;
    font-weight: 600;
}
QLabel#Muted {
    background: transparent;
    color: #8c99ad;
}
QLabel#Pill {
    background: #202a3a;
    border: 1px solid #35445c;
    border-radius: 6px;
    padding: 5px 9px;
}
QLabel#VisualizationFrame {
    background: #202a3a;
    border: 1px solid #35445c;
    border-radius: 7px;
    color: #aebbd0;
    padding: 16px;
}
QPushButton {
    background: #2865a6;
    border: 1px solid #3578bf;
    border-radius: 7px;
    color: #edf5ff;
    padding: 7px 12px;
    min-height: 24px;
}
QPushButton:hover {
    background: #347abe;
}
QPushButton:pressed {
    background: #3f8cd7;
}
QPushButton#Danger {
    background: #b83b42;
    border-color: #d6555c;
}
QPushButton#Danger:hover {
    background: #d04a52;
}
QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox {
    background: #1d2635;
    border: 1px solid #35445c;
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: #347abe;
}
QComboBox::drop-down {
    border: 0;
    width: 24px;
}
QTabWidget::pane {
    border: 1px solid #2e3a4d;
    border-radius: 8px;
    top: -1px;
}
QTabBar::tab {
    background: #1a2230;
    border: 1px solid #2e3a4d;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 14px;
    margin-right: 2px;
    color: #aebbd0;
}
QTabBar::tab:selected {
    background: #2865a6;
    color: #ffffff;
}
QTableWidget, QTextEdit, QListWidget {
    background: #121821;
    alternate-background-color: #171f2b;
    border: 1px solid #2e3a4d;
    border-radius: 7px;
    gridline-color: #2e3a4d;
}
QHeaderView::section {
    background: #202a3a;
    color: #c8d3e5;
    border: 0;
    border-right: 1px solid #2e3a4d;
    padding: 7px;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #263247;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
    background: #66c9a4;
}
"""

LIGHT_STYLE_SHEET = """
QWidget {
    background: #f4f6f8;
    color: #202938;
    font-family: "Segoe UI", "Microsoft YaHei", "Noto Sans", sans-serif;
    font-size: 14px;
}
QLabel {
    background: transparent;
}
QMainWindow, QDialog {
    background: #f4f6f8;
}
QFrame#TopBar, QFrame#Panel {
    background: #ffffff;
    border: 1px solid #cfd7e3;
    border-radius: 8px;
}
QLabel#SectionTitle {
    background: transparent;
    color: #42526b;
    font-size: 15px;
    font-weight: 600;
}
QLabel#Muted {
    background: transparent;
    color: #697589;
}
QLabel#Pill {
    background: #eef3f8;
    border: 1px solid #cbd6e4;
    border-radius: 6px;
    padding: 5px 9px;
}
QLabel#VisualizationFrame {
    background: #eef3f8;
    border: 1px solid #cbd6e4;
    border-radius: 7px;
    color: #42526b;
    padding: 16px;
}
QPushButton {
    background: #256fb8;
    border: 1px solid #1d5d9c;
    border-radius: 7px;
    color: #ffffff;
    padding: 7px 12px;
    min-height: 24px;
}
QPushButton:hover {
    background: #2f7fcf;
}
QPushButton:pressed {
    background: #19558f;
}
QPushButton#Danger {
    background: #c94852;
    border-color: #a93841;
}
QPushButton#Danger:hover {
    background: #d95a63;
}
QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox {
    background: #ffffff;
    border: 1px solid #cbd6e4;
    border-radius: 6px;
    padding: 5px 8px;
    selection-background-color: #2f7fcf;
}
QComboBox::drop-down {
    border: 0;
    width: 24px;
}
QTabWidget::pane {
    border: 1px solid #cfd7e3;
    border-radius: 8px;
    top: -1px;
}
QTabBar::tab {
    background: #e9eef5;
    border: 1px solid #cfd7e3;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 14px;
    margin-right: 2px;
    color: #42526b;
}
QTabBar::tab:selected {
    background: #256fb8;
    color: #ffffff;
}
QTableWidget, QTextEdit, QListWidget {
    background: #ffffff;
    alternate-background-color: #f2f5f9;
    border: 1px solid #cfd7e3;
    border-radius: 7px;
    gridline-color: #d8e0eb;
}
QHeaderView::section {
    background: #eef3f8;
    color: #344054;
    border: 0;
    border-right: 1px solid #d8e0eb;
    padding: 7px;
}
QSlider::groove:horizontal {
    height: 6px;
    background: #d6dee9;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    width: 16px;
    margin: -5px 0;
    border-radius: 8px;
    background: #2f9e7e;
}
"""
