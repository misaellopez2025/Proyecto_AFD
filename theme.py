"""Native Qt styles for AFD Studio."""
COLORS = {
    'text':'#1d1d1f', 'panel':'#ffffff', 'line':'#e8e9ed',
    'selected':'#eaf0f6', 'active':'#d6e3ef', 'active_text':'#355675',
    'accepted':'#24734b', 'rejected':'#b2434f',
}
STYLE = """
* { font-family: 'Segoe UI'; font-size: 13px; color: #1d1d1f; }
QMainWindow { background: #f5f5f7; }
QScrollArea#pageScroll, QWidget#pageViewport { background: transparent; border: none; }
QWidget#app { background: transparent; }
QLabel { background: transparent; border: none; }
QLabel#logo { font-size: 30px; font-weight: 800; color: #1d1d1f; }
QLabel#heading { font-size: 19px; font-weight: 750; color: #1d1d1f; }
QLabel#muted { font-size: 13px; color: #6e6e73; }
QLabel#message { font-size: 13px; color: #6e6e73; }
QLabel#fileInfo { font-size: 13px; color: #6e6e73; }
QLabel#foot { color: #86868b; font-size: 12px; padding: 15px; }
QFrame#panel { background: #ffffff; border: 1px solid #e2e3e7; border-radius: 24px; }
QLabel#pill { background: #eef0f3; color: #515863; border-radius: 15px; padding: 7px 11px; font-size: 12px; font-weight: 700; }
QLabel#deriveCount { color: #515863; background: #eef0f3; border-radius: 15px; font-size: 11px; font-weight: 750; padding: 7px 10px; }
QLabel#deriveHeading { color: #1d1d1f; font-size: 16px; font-weight: 700; }
QLabel#deriveSub { color: #86868b; font-size: 12px; }
QPushButton { background: #f4f4f6; border: 1px solid #e0e1e5; color: #414149; font-size: 16px; font-weight: 650; border-radius: 12px; padding: 10px 15px; }
QPushButton:hover { background: #ececf0; }
QPushButton:pressed { background: #e3e4e9; }
QPushButton:disabled { background: #f8f8fa; color: #afb1b7; border-color: #ebecf0; }
QPushButton#primary { background: #2c2c2e; color: white; border: none; padding: 12px 18px; font-weight: 750; }
QPushButton#primary:hover { background: #454548; }
QPushButton#primary:disabled { background: #c7c9ce; color: #f8f8fa; }
QPushButton#nav { background: #fafafb; color: #414149; border: 1px solid #dadce1; border-radius: 13px; font-weight: 600; padding: 10px 15px; }
QPushButton#nav:hover { background: #e9eaee; color: #1d1d1f; }
QPushButton#nav::menu-indicator { image: none; width: 0; }
QMenu { background: #ffffff; color: #1d1d1f; border: 1px solid #dedfe4; border-radius: 16px; padding: 7px; }
QMenu::item { padding: 11px; min-width: 177px; border-radius: 8px; font-size: 16px; }
QMenu::item:selected { background: #eaf0f6; }
QMenu::separator { background: #e2e3e7; height: 1px; margin: 4px; }
QLineEdit { background: white; color: #1d1d1f; font-size: 15px; border: 1px solid #dcdde3; border-radius: 12px; padding: 13px; selection-background-color: #d6e3ef; }
QLineEdit:focus { border-color: #7891ab; }
QPlainTextEdit { background: white; color: #1d1d1f; border: 1px solid #dcdde3; border-radius: 12px; padding: 14px; font-family: 'Consolas'; font-size: 13px; selection-background-color: #d6e3ef; }
QFrame#drawingFrame { border: 1px solid #e2e3e7; border-radius: 19px; background: #fafafb; }
QLabel#status { background: #edf1f5; color: #4b5f75; border-radius: 14px; padding: 12px; font-size: 14px; font-weight: 700; }
QLabel#status[result="ok"] { background: #eaf4ed; color: #24734b; }
QLabel#status[result="no"] { background: #faeff0; color: #b2434f; }
QFrame#tableWrap { background: #ffffff; border: 1px solid #e2e3e7; border-radius: 15px; }
QTableWidget { background: #ffffff; border: none; color: #1d1d1f; outline: none; selection-background-color: #eaf0f6; selection-color: #1d1d1f; font-size: 13px; }
QTableWidget::item { border-bottom: 1px solid #e8e9ed; padding: 11px 12px; }
QTableWidget::item:selected { background: #eaf0f6; }
QHeaderView::section { background: #f5f5f7; color: #6e6e73; padding: 11px 12px; border: none; border-bottom: 1px solid #e8e9ed; text-align: left; font-size: 13px; font-weight: 700; }
QScrollArea#derivations { background: transparent; border: none; }
QWidget#deriveContent { background: transparent; }
QFrame#deriveRow { background: #fafafb; border: 1px solid #e5e6eb; border-radius: 12px; }
QFrame#deriveRow:hover { background: #f0f2f6; }
QFrame#deriveRow[current="true"] { background: #eaf0f6; border: 1px solid #9eafc0; border-left: 3px solid #627e9b; }
QLabel#deriveNumber { color: #86868b; font-size: 11px; font-weight: 750; }
QLabel#deriveWord { color: #1d1d1f; font-size: 16px; font-weight: 700; }
QLabel#deriveArrow { color: #a4a8ae; font-size: 16px; }
QLabel#deriveState { color: #4b6580; font-size: 12px; font-weight: 750; }
QLabel#deriveResult { font-size: 10px; font-weight: 750; padding: 5px 8px; border-radius: 12px; }
QLabel#deriveResult[accepted="true"] { color: #24734b; background: #eaf4ed; }
QLabel#deriveResult[accepted="false"] { color: #b2434f; background: #faeff0; }
QLabel#deriveEmpty { padding: 14px; color: #6e6e73; background: #f4f4f6; border-radius: 12px; }
QLabel#deriveError { padding: 14px; color: #b2434f; background: #faeff0; border-radius: 12px; }
QFrame#modal { background: #ffffff; border: none; border-radius: 20px; }
QLabel#modalTitle { color: #1d1d1f; font-size: 24px; font-weight: 700; }
QLabel#modalError { color: #b2434f; font-size: 13px; }
QScrollArea#modalScroll { background: transparent; border: none; }
QWidget#modalContent { background: #ffffff; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 2px; }
QScrollBar::handle:vertical { background: #c4c7cf; border-radius: 3px; min-height: 22px; }
QScrollBar:horizontal { background: transparent; height: 8px; margin: 2px; }
QScrollBar::handle:horizontal { background: #c4c7cf; border-radius: 3px; min-width: 22px; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QToolTip { color: #1d1d1f; background: #ffffff; border: 1px solid #dcdde3; padding: 6px; }
"""
