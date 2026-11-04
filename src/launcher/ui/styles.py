"""Lightweight native-style visual language for the launcher."""

APP_STYLE = """
QWidget { color: #f5f5f7; font-family: 'Segoe UI', 'SF Pro Display', 'Inter', Arial, sans-serif; font-size: 10pt; }
QWidget#root, QWidget#content, QWidget#grid { background: #0f1115; }
QToolTip { color: #ffffff; background: #252932; border: 1px solid #3b414d; border-radius: 7px; padding: 6px 9px; }
QWidget#sidebar { background: #15181e; border-right: 1px solid #272c35; }
QLabel#brandIcon { background: transparent; }
QLabel#brandTitle { color: #f5f5f7; font-size: 11pt; font-weight: 700; }
QLabel#navSection { color: #858b96; font-size: 8pt; font-weight: 700; padding: 0 9px 5px 9px; }
QPushButton#navButton, QPushButton#navActive { background: transparent; color: #a3a9b4; border: 0; border-radius: 9px; padding: 0 10px; text-align: left; font-weight: 600; }
QPushButton#navButton:hover { background: #20242c; color: #f5f5f7; }
QPushButton#navActive { background: #352126; color: #ff8790; border: 1px solid #63343b; }
QFrame#sidebarRule { color: #2b3039; background: #2b3039; border: 0; max-height: 1px; }
QLabel#sidebarMeta { color: #858b96; font-size: 8.5pt; padding: 7px 4px 1px 4px; }
QWidget#header { background: #0f1115; border-bottom: 1px solid #272c35; }
QLabel#pageTitle { color: #f5f5f7; font-size: 19pt; font-weight: 700; }
QLabel#pageSubtitle { color: #8f96a2; font-size: 9pt; }
QLabel#summary { color: #aeb4bf; font-size: 8.5pt; font-weight: 600; padding: 6px 10px; background: #1b1f27; border: 1px solid #303641; border-radius: 9px; }
QLabel#summary[state="active"] { color: #72d99e; background: #172b21; border-color: #2d6245; }
QLabel#summary[state="busy"] { color: #f3ca6d; background: #332b17; border-color: #665621; }
QWidget#toolbar { background: #0f1115; border-bottom: 1px solid #242932; }
QLineEdit, QComboBox { background: #191d24; color: #f5f5f7; border: 1px solid #343a45; border-radius: 10px; padding: 8px 12px; selection-background-color: #ff4f5e; }
QLineEdit:hover, QComboBox:hover { border-color: #4b5361; }
QLineEdit:focus, QComboBox:focus { border: 2px solid #ff6572; padding: 7px 11px; }
QLineEdit::placeholder { color: #7e8692; }
QComboBox::drop-down { border: 0; width: 25px; }
QComboBox QAbstractItemView { background: #1c2028; color: #f5f5f7; border: 1px solid #3a414d; selection-background-color: #352126; selection-color: #ff9aa2; outline: 0; }
QMenu { background: #1c2028; color: #f5f5f7; border: 1px solid #3a414d; padding: 4px; }
QMenu::item { color: #f5f5f7; background: transparent; padding: 7px 22px 7px 10px; border-radius: 6px; }
QMenu::item:selected { color: #ffffff; background: #343b48; }
QMenu::item:disabled { color: #707887; }
QMenu::separator { height: 1px; background: #343a45; margin: 4px 6px; }
QPushButton { background: #1b1f27; color: #dce0e7; border: 1px solid #343a45; border-radius: 9px; padding: 7px 11px; font-weight: 600; }
QPushButton:hover { background: #252a34; border-color: #4b5361; }
QPushButton:pressed { background: #303641; }
QPushButton:disabled { color: #606875; background: #171a20; border-color: #282e38; }
QPushButton#primary { background: #ff4f5e; color: #ffffff; border-color: #ff4f5e; }
QPushButton#primary:hover { background: #ff6572; border-color: #ff6572; }
QPushButton#primary:pressed { background: #df3545; border-color: #df3545; }
QPushButton#primary:disabled { background: #f4b5ba; color: #fff7f8; border-color: #f4b5ba; }
QPushButton#danger { background: transparent; color: #ff9aa2; border-color: #63343b; }
QPushButton#danger:hover { background: #352126; color: #ffb5ba; border-color: #8c454d; }
QPushButton#danger:disabled { color: #6d5b60; border-color: #30272a; }
QPushButton#secondary { background: #181c23; color: #aeb4bf; border-color: #303641; }
QPushButton#secondary:hover { background: #252a34; color: #f5f5f7; border-color: #4b5361; }
QFrame#card { background: #191d24; border: 1px solid #2b313b; border-radius: 12px; }
QFrame#card:hover { background: #1d222a; border-color: #4a515d; }
QFrame#card[state="running"] { background: #18231e; border-color: #2e6246; }
QFrame#card[state="starting"] { border-color: #685722; }
QFrame#card[state="failed"] { border-color: #783d43; }
QLabel#title { color: #f5f5f7; font-size: 10.5pt; font-weight: 700; }
QLabel#subtitle { color: #858d99; font-size: 8.5pt; }
QLabel#description { color: #aeb4bf; font-size: 9pt; }
QLabel#emptyState { color: #858d99; font-size: 10pt; font-weight: 600; }
QLabel#badge, QLabel#badgeRunning, QLabel#badgeStarting, QLabel#badgeFailed { border-radius: 7px; font-weight: 700; font-size: 7.5pt; padding: 3px 8px; }
QLabel#badge { background: #2a2f38; color: #aeb4bf; }
QLabel#badgeRunning { background: #1b3a29; color: #72d99e; }
QLabel#badgeStarting { background: #3a3018; color: #f3ca6d; }
QLabel#badgeFailed { background: #402328; color: #ff9aa2; }
QDialog, QMessageBox { background: #15181e; }
QPlainTextEdit { background: #0f1115; color: #dce0e7; border: 1px solid #343a45; border-radius: 9px; }
QScrollArea { background: transparent; border: 0; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 4px 2px 4px 0; }
QScrollBar::handle:vertical { background: #3a414d; border-radius: 5px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #515a68; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
"""
