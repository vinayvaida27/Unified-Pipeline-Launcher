"""Qt style sheet."""

APP_STYLE = """
QWidget {
    color: #27312e;
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    font-size: 10pt;
}
QWidget#root {
    background: #f3f5f3;
}

/* Header */
QWidget#header {
    background: #202b28;
    border-bottom: 1px solid #202b28;
}
QLabel#platformTitle {
    font-size: 17pt;
    font-weight: 700;
    color: #ffffff;
}
QLabel#platformSubtitle {
    color: #b9c8c2;
    font-size: 9pt;
}
QLabel#summary {
    color: #d8e3de;
    font-size: 9pt;
    padding: 6px 10px;
    background: #2b3935;
    border: 1px solid #40514b;
    border-radius: 5px;
}

/* Toolbar */
QWidget#toolbar {
    background: #fdfefd;
    border-bottom: 1px solid #dce3df;
}
QWidget#grid {
    background: #f3f5f3;
}

/* Inputs */
QLineEdit, QComboBox {
    background: #ffffff;
    border: 1px solid #cdd7d2;
    border-radius: 6px;
    padding: 8px 12px;
    min-height: 22px;
    selection-background-color: #0f766e;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #0f766e;
}
QComboBox::drop-down {
    border: 0;
    width: 24px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #cdd7d2;
    border-radius: 6px;
    selection-background-color: #e2f1ed;
    selection-color: #27312e;
    outline: 0;
}

/* Buttons */
QPushButton {
    background: #ffffff;
    color: #27312e;
    border: 1px solid #cdd7d2;
    border-radius: 6px;
    padding: 8px 12px;
    font-weight: 600;
    min-height: 22px;
}
QPushButton:hover {
    background: #f2f6f4;
    border: 1px solid #9fb1a9;
}
QPushButton:disabled {
    color: #a6afab;
    background: #f0f2f1;
    border: 1px solid #dfe4e1;
}
QPushButton#primary {
    background: #0f766e;
    color: #ffffff;
    border: 1px solid #0f766e;
}
QPushButton#primary:hover {
    background: #0b655e;
    border: 1px solid #0b655e;
}
QPushButton#primary:disabled {
    background: #9bbdb8;
    border: 1px solid #9bbdb8;
    color: #ffffff;
}
QPushButton#secondary {
    background: #ffffff;
    color: #27312e;
    border: 1px solid #cdd7d2;
}
QPushButton#danger, QPushButton#dangerIcon {
    background: #ffffff;
    color: #a33a32;
    border: 1px solid #dfb8b3;
}
QPushButton#danger:hover, QPushButton#dangerIcon:hover {
    background: #fff3f1;
    border: 1px solid #c87b73;
}
QPushButton#danger:disabled, QPushButton#dangerIcon:disabled {
    color: #b9b9b5;
    background: #f0f2f1;
    border: 1px solid #dfe4e1;
}
QPushButton#ghost {
    background: transparent;
    color: #eef4f1;
    border: 1px solid transparent;
    padding: 6px 12px;
}
QPushButton#ghost:hover {
    background: #2b3935;
    border: 1px solid #40514b;
}
QPushButton#toolIcon {
    background: transparent;
    color: #53615c;
    border: 1px solid #d6dfda;
    padding: 7px;
}
QPushButton#toolIcon:hover {
    background: #edf2ef;
    border: 1px solid #9fb1a9;
}
QPushButton#dangerIcon {
    padding: 7px;
}

/* App cards */
QFrame#card {
    background: #ffffff;
    border: 1px solid #dce3df;
    border-radius: 8px;
}
QFrame#card:hover {
    border: 1px solid #a9bbb3;
}
QLabel#appTitle {
    color: #17211e;
    font-size: 11.5pt;
    font-weight: 700;
}
QLabel#appMeta {
    color: #78857f;
    font-size: 8.5pt;
}
QLabel#description {
    color: #53615c;
    font-size: 9pt;
}
QLabel#emptyState {
    color: #75817c;
    font-size: 11pt;
    font-weight: 600;
}

/* Status badges */
QLabel#badge {
    border-radius: 5px;
    padding: 4px 8px;
    background: #edf0ee;
    color: #56625d;
    font-weight: 600;
    font-size: 8.5pt;
}
QLabel#badgeRunning {
    border-radius: 5px;
    padding: 4px 8px;
    background: #dcefe4;
    color: #17643a;
    font-weight: 700;
    font-size: 8.5pt;
}
QLabel#badgeStarting {
    border-radius: 5px;
    padding: 4px 8px;
    background: #f8ebcb;
    color: #825b13;
    font-weight: 700;
    font-size: 8.5pt;
}
QLabel#badgeFailed {
    border-radius: 5px;
    padding: 4px 8px;
    background: #f8dfdc;
    color: #9d3029;
    font-weight: 700;
    font-size: 8.5pt;
}

/* Scrollbar */
QScrollArea {
    background: transparent;
    border: 0;
}
QScrollBar:vertical {
    background: transparent;
    width: 10px;
    margin: 4px 2px 4px 0;
}
QScrollBar::handle:vertical {
    background: #bcc8c2;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: #99aaa2;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
"""
