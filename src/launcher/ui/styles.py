"""Qt style sheet."""

APP_STYLE = """
QWidget {
    color: #25302c;
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    font-size: 10pt;
}
QWidget#root {
    background: #f4f6f5;
}

/* Header */
QWidget#header {
    background: #ffffff;
    border-bottom: 1px solid #dfe5e2;
}
QLabel#platformTitle {
    font-size: 16pt;
    font-weight: 700;
    color: #17221e;
}
QLabel#platformSubtitle {
    color: #74827c;
    font-size: 9pt;
}
QLabel#summary {
    color: #596760;
    font-size: 9pt;
    font-weight: 600;
    padding: 5px 10px;
    background: #f0f3f1;
    border: 1px solid #dde4e0;
    border-radius: 6px;
}
QLabel#summary[state="active"] {
    color: #176648;
    background: #e8f3ee;
    border: 1px solid #cfe3d9;
}
QLabel#summary[state="busy"] {
    color: #7b5918;
    background: #f8edcf;
    border: 1px solid #ead8a8;
}

/* Toolbar */
QWidget#toolbar {
    background: #fafcfb;
    border-bottom: 1px solid #dce3df;
}
QWidget#grid {
    background: #f4f6f5;
}

/* Inputs */
QLineEdit, QComboBox {
    background: #ffffff;
    border: 1px solid #ccd6d1;
    border-radius: 7px;
    padding: 7px 11px;
    selection-background-color: #087f72;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #087f72;
}
QComboBox::drop-down {
    border: 0;
    width: 24px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #ccd6d1;
    border-radius: 7px;
    selection-background-color: #e5f2ee;
    selection-color: #25302c;
    outline: 0;
}

/* Buttons */
QPushButton {
    background: #ffffff;
    color: #25302c;
    border: 1px solid #ccd6d1;
    border-radius: 6px;
    padding: 6px 10px;
    font-weight: 600;
}
QPushButton:hover {
    background: #f1f5f3;
    border: 1px solid #9eafa7;
}
QPushButton:disabled {
    color: #a3ada8;
    background: #eff2f0;
    border: 1px solid #dfe5e2;
}
QPushButton#primary {
    background: #087f72;
    color: #ffffff;
    border: 1px solid #087f72;
}
QPushButton#primary:hover {
    background: #066c62;
    border: 1px solid #066c62;
}
QPushButton#primary:disabled {
    background: #9fc3bd;
    border: 1px solid #9fc3bd;
    color: #ffffff;
}
QPushButton#secondary {
    background: #ffffff;
    color: #34413c;
    border: 1px solid #ccd6d1;
}
QPushButton#quiet {
    background: transparent;
    color: #5d6a65;
    border: 1px solid transparent;
}
QPushButton#quiet:hover {
    background: #edf2ef;
    border: 1px solid #d8e1dc;
}
QPushButton#danger {
    background: #ffffff;
    color: #a33c34;
    border: 1px solid #e1bbb6;
}
QPushButton#danger:hover {
    background: #fff3f1;
    border: 1px solid #c87b73;
}
QPushButton#danger:disabled {
    color: #b9b9b5;
    background: #f0f2f1;
    border: 1px solid #dfe4e1;
}
QPushButton#ghost {
    background: transparent;
    color: #4f5d57;
    border: 1px solid transparent;
    padding: 5px 10px;
}
QPushButton#ghost:hover {
    background: #f0f4f2;
    border: 1px solid #dce4e0;
}

/* App cards */
QFrame#card {
    background: #ffffff;
    border: 1px solid #dbe3df;
    border-radius: 8px;
}
QFrame#card:hover {
    border: 1px solid #a8b9b1;
}
QFrame#card[state="running"] {
    background: #fbfefd;
    border: 1px solid #94c7b7;
}
QFrame#card[state="starting"] {
    border: 1px solid #dbc27d;
}
QFrame#card[state="failed"] {
    border: 1px solid #d8a19a;
}
QLabel#appTitle {
    color: #17211e;
    font-size: 11pt;
    font-weight: 700;
}
QLabel#appMeta {
    color: #7b8882;
    font-size: 8.5pt;
}
QLabel#description {
    color: #56635e;
    font-size: 9pt;
}
QLabel#appIconFallback {
    background: #edf2ef;
    border: 1px solid #d5ded9;
    border-radius: 6px;
    color: #34413c;
    font-size: 13pt;
    font-weight: 700;
}
QLabel#emptyState {
    color: #75817c;
    font-size: 11pt;
    font-weight: 600;
}

/* Status badges */
QLabel#badge {
    border-radius: 6px;
    background: #eef1ef;
    color: #59655f;
    font-weight: 600;
    font-size: 8pt;
}
QLabel#badgeRunning {
    border-radius: 6px;
    background: #dff1e7;
    color: #17663b;
    font-weight: 700;
    font-size: 8pt;
}
QLabel#badgeStarting {
    border-radius: 6px;
    background: #f8ebcb;
    color: #825b13;
    font-weight: 700;
    font-size: 8pt;
}
QLabel#badgeFailed {
    border-radius: 6px;
    background: #f8dfdc;
    color: #9d3029;
    font-weight: 700;
    font-size: 8pt;
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
