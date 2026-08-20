APP_STYLESHEET = r"""
QWidget {
    color: #183247;
    font-family: "Segoe UI";
    font-size: 10pt;
}
QMainWindow, QWidget#AppRoot { background: #F5F1E8; }
QFrame#Sidebar { background: #102A43; border: none; }
QLabel#BrandName { color: #FFF9ED; font-size: 17pt; font-weight: 700; }
QLabel#BrandCaption { color: #AFC4D2; font-size: 9pt; }
QPushButton#NavButton {
    color: #DDE8ED; background: transparent; border: none; border-radius: 9px;
    text-align: left; padding: 11px 14px; font-weight: 600;
}
QPushButton#NavButton:hover { background: #183D59; color: white; }
QPushButton#NavButton:checked { background: #244E69; color: white; border-left: 3px solid #F2B84B; }
QLabel#PageTitle { color: #102A43; font-size: 25pt; font-weight: 700; }
QLabel#PageSubtitle { color: #637788; font-size: 11pt; }
QFrame#Card, QFrame#Panel {
    background: #FFFDF8; border: 1px solid #E3DDD1; border-radius: 14px;
}
QFrame#Card:hover { border-color: #C5A05A; }
QLabel#CardTitle { color: #183247; font-size: 12pt; font-weight: 700; }
QLabel#Muted { color: #6D7E8B; }
QLabel#SectionTitle { color: #183247; font-size: 11pt; font-weight: 700; }
QPushButton {
    background: #E9E1D3; border: 1px solid #D8CDBD; border-radius: 8px;
    padding: 8px 13px; font-weight: 600;
}
QPushButton:hover { background: #DED3C2; }
QPushButton:pressed { background: #D2C4AF; }
QPushButton#PrimaryButton {
    color: white; background: #D6533D; border-color: #D6533D; padding: 10px 17px;
}
QPushButton#PrimaryButton:hover { background: #BD4432; }
QPushButton#SecondaryButton { color: #173A53; background: #EEF4F5; border-color: #C6D8DE; }
QPushButton#DangerButton { color: #A7392B; background: #FFF3F0; border-color: #ECC8C1; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
    background: white; border: 1px solid #D5CEC2; border-radius: 7px; padding: 7px 9px;
    selection-background-color: #D6533D;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 2px solid #2E7D80; }
QComboBox::drop-down { border: none; width: 24px; }
QSlider::groove:horizontal { height: 5px; background: #D7D0C3; border-radius: 2px; }
QSlider::handle:horizontal { width: 17px; margin: -6px 0; background: #2E7D80; border-radius: 8px; }
QCheckBox { spacing: 8px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: #C7BFB2; border-radius: 5px; min-height: 28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QToolTip { color: white; background: #102A43; border: none; padding: 6px; }
QStatusBar { background: #FFFDF8; color: #627483; border-top: 1px solid #E3DDD1; }
QMenu { background: #FFFDF8; border: 1px solid #D8CDBD; padding: 5px; }
QMenu::item { padding: 7px 24px 7px 10px; border-radius: 5px; }
QMenu::item:selected { background: #E9F1F1; }
"""

