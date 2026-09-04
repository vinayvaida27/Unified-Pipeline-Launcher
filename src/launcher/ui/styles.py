"""Qt style sheet."""

APP_STYLE = """
QWidget {
    color: #ededee;
    font-family: 'Segoe UI', 'Inter', Arial, sans-serif;
    font-size: 10pt;
    letter-spacing: 0;
}
QWidget#root,
QWidget#content,
QWidget#grid {
    background: #0a0a0b;
}
QToolTip {
    color: #f4f4f5;
    background: #202023;
    border: 1px solid #39393f;
    padding: 5px 7px;
}

/* Sidebar */
QWidget#sidebar {
    background: #111113;
    border-right: 1px solid #242428;
}
QLabel#brandIcon {
    background: transparent;
}
QLabel#brandTitle {
    color: #f7f7f8;
    font-size: 11pt;
    font-weight: 700;
}
QLabel#navSection {
    color: #68686f;
    font-size: 8pt;
    font-weight: 700;
    padding: 0 9px 5px 9px;
}
QPushButton#navButton,
QPushButton#navActive {
    background: transparent;
    color: #a5a5ab;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 0 10px;
    text-align: left;
    font-weight: 600;
}
QPushButton#navButton:hover {
    background: #19191c;
    color: #f4f4f5;
}
QPushButton#navActive {
    background: #202024;
    color: #ffffff;
    border-left: 2px solid #3b82f6;
}
QFrame#sidebarRule {
    color: #29292d;
    background: #29292d;
    border: 0;
    max-height: 1px;
}
QLabel#sidebarMeta {
    color: #717179;
    font-size: 8.5pt;
    padding: 7px 4px 1px 4px;
}

/* Main header */
QWidget#header {
    background: #0d0d0f;
    border-bottom: 1px solid #242428;
}
QLabel#pageTitle {
    color: #fafafa;
    font-size: 18pt;
    font-weight: 700;
}
QLabel#pageSubtitle {
    color: #85858d;
    font-size: 9pt;
}
QLabel#summary {
    color: #9b9ba2;
    font-size: 8.5pt;
    font-weight: 600;
    padding: 5px 9px;
    background: #19191c;
    border: 1px solid #2c2c31;
    border-radius: 5px;
}
QLabel#summary[state="active"] {
    color: #75d9aa;
    background: #14271f;
    border: 1px solid #26533f;
}
QLabel#summary[state="busy"] {
    color: #f3cc75;
    background: #292311;
    border: 1px solid #52451e;
}

/* Toolbar and inputs */
QWidget#toolbar {
    background: #0d0d0f;
    border-bottom: 1px solid #1e1e22;
}
QLineEdit,
QComboBox {
    background: #151517;
    color: #eeeeef;
    border: 1px solid #303035;
    border-radius: 6px;
    padding: 7px 11px;
    selection-background-color: #3b82f6;
}
QLineEdit:hover,
QComboBox:hover {
    border: 1px solid #414148;
}
QLineEdit:focus,
QComboBox:focus {
    border: 1px solid #3b82f6;
}
QLineEdit::placeholder {
    color: #72727a;
}
QComboBox::drop-down {
    border: 0;
    width: 25px;
}
QComboBox QAbstractItemView {
    background: #18181b;
    color: #eeeeef;
    border: 1px solid #34343a;
    selection-background-color: #2a2a30;
    selection-color: #ffffff;
    outline: 0;
}

/* Buttons */
QPushButton {
    background: #1a1a1d;
    color: #e4e4e7;
    border: 1px solid #34343a;
    border-radius: 6px;
    padding: 6px 10px;
    font-weight: 600;
}
QPushButton:hover {
    background: #252529;
    border: 1px solid #494950;
}
QPushButton:pressed {
    background: #2d2d32;
}
QPushButton:disabled {
    color: #55555c;
    background: #151517;
    border: 1px solid #252529;
}
QPushButton#primary {
    background: #f4f4f5;
    color: #111113;
    border: 1px solid #f4f4f5;
}
QPushButton#primary:hover {
    background: #ffffff;
    border: 1px solid #ffffff;
}
QPushButton#primary:pressed {
    background: #d9d9dc;
    border: 1px solid #d9d9dc;
}
QPushButton#primary:disabled {
    background: #29292d;
    color: #626269;
    border: 1px solid #29292d;
}
QPushButton#danger {
    background: transparent;
    color: #d4d4d8;
    border: 1px solid #3b3b41;
}
QPushButton#danger:hover {
    background: #321b1d;
    color: #ff9b98;
    border: 1px solid #6c3334;
}
QPushButton#danger:disabled {
    color: #4e4e54;
    background: transparent;
    border: 1px solid #252529;
}
QPushButton#tool,
QPushButton#toolDanger {
    background: transparent;
    color: #b3b3b9;
    border: 1px solid transparent;
    padding: 0;
}
QPushButton#tool:hover {
    background: #252529;
    color: #ffffff;
    border: 1px solid #3d3d43;
}
QPushButton#toolDanger:hover {
    background: #321b1d;
    color: #ff9b98;
    border: 1px solid #6c3334;
}
QPushButton#quiet {
    background: transparent;
    color: #a8a8af;
    border: 1px solid transparent;
    padding: 0 5px;
}
QPushButton#quiet:hover {
    background: #252529;
    color: #ffffff;
    border: 1px solid #3d3d43;
}

/* Application cards */
QFrame#card {
    background: #121214;
    border: 1px solid #26262a;
    border-radius: 7px;
}
QFrame#card:hover {
    background: #151518;
    border: 1px solid #3a3a40;
}
QFrame#card[state="running"] {
    background: #121715;
    border: 1px solid #315f4b;
}
QFrame#card[state="starting"] {
    border: 1px solid #655522;
}
QFrame#card[state="failed"] {
    border: 1px solid #713c3a;
}
QLabel#appTitle {
    color: #f3f3f4;
    font-size: 10.5pt;
    font-weight: 700;
}
QLabel#appMeta {
    color: #777780;
    font-size: 8.5pt;
}
QLabel#description {
    color: #9a9aa2;
    font-size: 9pt;
}
QLabel#appIconFallback {
    background: #1e2633;
    border: 1px solid #354765;
    border-radius: 6px;
    color: #a8c9ff;
    font-size: 13pt;
    font-weight: 700;
}
QLabel#emptyState {
    color: #717179;
    font-size: 10pt;
    font-weight: 600;
}

/* Status badges */
QLabel#badge,
QLabel#badgeRunning,
QLabel#badgeStarting,
QLabel#badgeFailed {
    border-radius: 5px;
    font-weight: 700;
    font-size: 7.5pt;
}
QLabel#badge {
    background: #232326;
    color: #9b9ba2;
}
QLabel#badgeRunning {
    background: #183528;
    color: #72d9a8;
}
QLabel#badgeStarting {
    background: #3a3015;
    color: #f3ca6d;
}
QLabel#badgeFailed {
    background: #402120;
    color: #ff918c;
}

/* Dialogs and scrolling */
QDialog,
QMessageBox {
    background: #111113;
}
QPlainTextEdit {
    background: #0a0a0b;
    color: #dedee1;
    border: 1px solid #303035;
    border-radius: 6px;
    selection-background-color: #3b82f6;
}
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
    background: #35353a;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover {
    background: #4a4a51;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
}
"""
