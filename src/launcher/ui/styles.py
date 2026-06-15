"""Qt style sheet."""

APP_STYLE = """
QWidget {
    color: #1f2937;
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    font-size: 10pt;
}
QWidget#root {
    background: #f1f4f9;
}

/* Header */
QWidget#header {
    background: #ffffff;
    border-bottom: 1px solid #e3e8f0;
}
QLabel#title {
    font-size: 16pt;
    font-weight: 700;
    color: #0f172a;
}
QLabel#subtitle {
    color: #6b7686;
    font-size: 9pt;
}
QLabel#summary {
    color: #5b6678;
    font-size: 9pt;
    padding-right: 6px;
}

/* Toolbar */
QWidget#toolbar {
    background: #ffffff;
    border-bottom: 1px solid #e3e8f0;
}
QWidget#grid {
    background: #f1f4f9;
}

/* Inputs */
QLineEdit, QComboBox {
    background: #ffffff;
    border: 1px solid #d4dbe6;
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 22px;
    selection-background-color: #2f6fed;
}
QLineEdit:focus, QComboBox:focus {
    border: 1px solid #2f6fed;
}
QComboBox::drop-down {
    border: 0;
    width: 24px;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    border: 1px solid #d4dbe6;
    border-radius: 8px;
    selection-background-color: #eaf1fe;
    selection-color: #0f172a;
    outline: 0;
}

/* Buttons */
QPushButton {
    background: #ffffff;
    color: #1f2937;
    border: 1px solid #d4dbe6;
    border-radius: 8px;
    padding: 8px 16px;
    font-weight: 600;
    min-height: 22px;
}
QPushButton:hover {
    background: #f5f8fc;
    border: 1px solid #b9c5d6;
}
QPushButton:disabled {
    color: #aab3c0;
    background: #f3f5f9;
    border: 1px solid #e3e8f0;
}
QPushButton#primary {
    background: #2368d8;
    color: #ffffff;
    border: 1px solid #2368d8;
}
QPushButton#primary:hover {
    background: #1d5fc9;
    border: 1px solid #1d5fc9;
}
QPushButton#primary:disabled {
    background: #aebfd9;
    border: 1px solid #aebfd9;
    color: #ffffff;
}
QPushButton#secondary {
    background: #ffffff;
    color: #1f2937;
    border: 1px solid #d4dbe6;
}
QPushButton#ghost {
    background: transparent;
    color: #475063;
    border: 1px solid transparent;
    padding: 6px 12px;
}
QPushButton#ghost:hover {
    background: #eef2f8;
    border: 1px solid #e3e8f0;
}

/* App cards */
QFrame#card {
    background: #ffffff;
    border: 1px solid #e3e8f0;
    border-radius: 12px;
}
QFrame#card:hover {
    border: 1px solid #c2d0e4;
}
QLabel#description {
    color: #5b6678;
    font-size: 9pt;
}

/* Status badges */
QLabel#badge {
    border-radius: 11px;
    padding: 4px 12px;
    background: #eef1f6;
    color: #445062;
    font-weight: 600;
    font-size: 8.5pt;
}
QLabel#badgeRunning {
    border-radius: 11px;
    padding: 4px 12px;
    background: #dcfce7;
    color: #15803d;
    font-weight: 700;
    font-size: 8.5pt;
}
QLabel#badgeStarting {
    border-radius: 11px;
    padding: 4px 12px;
    background: #dbeafe;
    color: #1d4ed8;
    font-weight: 700;
    font-size: 8.5pt;
}
QLabel#badgeFailed {
    border-radius: 11px;
    padding: 4px 12px;
    background: #fee2e2;
    color: #b91c1c;
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
    background: #c7d0dd;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: #aab7c8;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: transparent;
}
"""
