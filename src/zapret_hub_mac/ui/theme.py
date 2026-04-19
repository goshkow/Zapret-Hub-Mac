from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UiPalette:
    is_dark: bool
    window_bg: str
    text: str
    root_bg: str
    root_border: str
    sidebar_bg: str
    content_bg: str
    card_bg: str
    hero_bg: str
    soft_card_bg: str
    card_border: str
    hero_border: str
    text_primary: str
    text_muted: str
    badge_bg: str
    badge_border: str
    badge_text: str
    status_bg: str
    status_border: str
    status_text: str
    action_hover: str
    button_bg: str
    button_hover: str
    button_border: str
    primary_bg: str
    primary_border: str
    primary_text: str
    danger_bg: str
    danger_border: str
    danger_text: str
    input_bg: str
    input_border: str
    selection_bg: str
    gridline: str
    header_bg: str
    nav_hover: str
    nav_hover_border: str
    nav_checked: str
    nav_checked_border: str
    nav_highlight: str
    nav_glow: str
    power_core: str
    power_edge: str
    power_glow: str
    power_idle: str
    ring: str


def resolve_palette(theme: str) -> UiPalette:
    if theme == "oled":
        return UiPalette(
            is_dark=True,
            window_bg="#17181a",
            text="#d9dde4",
            root_bg="#131416",
            root_border="#2a2d31",
            sidebar_bg="#131416",
            content_bg="qlineargradient(x1:0, y1:1, x2:1, y2:0, stop:0 #17191c, stop:0.62 #191b1e, stop:1 #1b1d20)",
            card_bg="qlineargradient(x1:0, y1:1, x2:1, y2:0, stop:0 #181a1d, stop:0.68 #1a1c1f, stop:1 #1c1e21)",
            hero_bg="qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a1c1f, stop:1 #181a1d)",
            soft_card_bg="#181a1d",
            card_border="#2d3137",
            hero_border="#373c44",
            text_primary="#f5f7fc",
            text_muted="#9fa4ac",
            badge_bg="#181a1d",
            badge_border="#2d3137",
            badge_text="#d3d6dd",
            status_bg="#1b1d21",
            status_border="#373c44",
            status_text="#f8fbff",
            action_hover="rgba(255, 255, 255, 0.055)",
            button_bg="#1b1d21",
            button_hover="#22252a",
            button_border="#555b64",
            primary_bg="#5865f2",
            primary_border="#6773ff",
            primary_text="#ffffff",
            danger_bg="#15191d",
            danger_border="#fb5e5e",
            danger_text="#ffd9dd",
            input_bg="#17191d",
            input_border="#2d3137",
            selection_bg="#23262b",
            gridline="#2d3137",
            header_bg="#1a1c20",
            nav_hover="rgba(255, 255, 255, 0.02)",
            nav_hover_border="#555b64",
            nav_checked="rgba(255, 255, 255, 0.04)",
            nav_checked_border="#555b64",
            nav_highlight="#3a3f47",
            nav_glow="#5a6069",
            power_core="#7c85ff",
            power_edge="#a0a7ff",
            power_glow="#8f97ff",
            power_idle="#1a1c20",
            ring="#9098ff",
        )
    return UiPalette(
        is_dark=False,
        window_bg="#eef2f7",
        text="#132033",
        root_bg="#f8fbff",
        root_border="#d1dceb",
        sidebar_bg="#f8fbff",
        content_bg="qlineargradient(x1:0, y1:1, x2:1, y2:0, stop:0 #f0f5fb, stop:0.62 #f7faff, stop:1 #ffffff)",
        card_bg="#ffffff",
        hero_bg="#ffffff",
        soft_card_bg="#ffffff",
        card_border="#d7e2ef",
        hero_border="#d7e2ef",
        text_primary="#102033",
        text_muted="#5b6a80",
        badge_bg="#edf4fb",
        badge_border="#d3e0ef",
        badge_text="#48607d",
        status_bg="#edf4fb",
        status_border="#d3e0ef",
        status_text="#48607d",
        action_hover="rgba(114, 142, 181, 0.16)",
        button_bg="#dfeafb",
        button_hover="#d1e2fb",
        button_border="#bdd0ea",
        primary_bg="#355ee8",
        primary_border="#355ee8",
        primary_text="#ffffff",
        danger_bg="#fff0f1",
        danger_border="#f1b6bb",
        danger_text="#aa3646",
        input_bg="#ffffff",
        input_border="#d7e2ef",
        selection_bg="#dbe8fb",
        gridline="#d7e2ef",
        header_bg="#edf4fb",
        nav_hover="#e7eef9",
        nav_hover_border="#b5c9e6",
        nav_checked="#e3edfb",
        nav_checked_border="#9fbde5",
        nav_highlight="#d2e3fb",
        nav_glow="#7ca6f5",
        power_core="#3f78f0",
        power_edge="#90b5ff",
        power_glow="#80a8f7",
        power_idle="#edf4fb",
        ring="#99bbf8",
    )


def is_light_theme(theme: str) -> bool:
    return resolve_palette(theme).is_dark is False


def build_stylesheet(theme: str, *, chevron_icon: str = "", check_icon: str = "", close_icon: str = "", min_icon: str = "") -> str:
    palette = resolve_palette(theme)
    chevron_icon = chevron_icon.replace("\\", "/")
    check_icon = check_icon.replace("\\", "/")
    close_icon = close_icon.replace("\\", "/")
    min_icon = min_icon.replace("\\", "/")
    chevron_rule = f'image: url("{chevron_icon}");' if chevron_icon else "image: none;"
    check_rule = f'image: url("{check_icon}");' if check_icon else "image: none;"
    close_rule = f'image: url("{close_icon}");' if close_icon else "image: none;"
    min_rule = f'image: url("{min_icon}");' if min_icon else "image: none;"
    return f"""
    QWidget {{
        background: {palette.window_bg};
        color: {palette.text};
        font-family: "Helvetica Neue", "Segoe UI", sans-serif;
        font-size: 13pt;
    }}
    QLabel {{
        background: transparent;
    }}
    #WindowShell {{
        background: transparent;
    }}
    QDialog#SettingsDialog {{
        background: transparent;
        border: none;
    }}
    QStackedWidget, QStackedWidget > QWidget, QWidget#PagesShell, QStackedWidget#PagesStack {{
        background: transparent;
    }}
    QWidget[class="pageRoot"], QWidget[class="pageCanvas"] {{
        background: transparent;
    }}
    QWidget[class="transparentPane"], QWidget[uiRole="trafficCluster"] {{
        background: transparent;
    }}
    QWidget[class="dialogCanvas"] {{
        background: {palette.root_bg};
    }}
    #RootFrame {{
        background: {palette.root_bg};
        border: 1px solid {palette.root_border};
        border-radius: 16px;
    }}
    #TitleBar, #TitleStrip, #TitleDragSurface {{
        background: {palette.root_bg};
        border: none;
        border-top-left-radius: 16px;
        border-top-right-radius: 16px;
    }}
    #DialogRoot {{
        background: {palette.root_bg};
        border: 1px solid {palette.root_border};
        border-radius: 16px;
    }}
    #DialogTitleBar, #DialogTitleDragSurface, #DialogBody {{
        background: {palette.root_bg};
        border: none;
    }}
    #DialogTitleBar {{
        border-top-left-radius: 16px;
        border-top-right-radius: 16px;
    }}
    #Sidebar {{
        background: {palette.sidebar_bg};
        border-bottom-left-radius: 16px;
        border-right: none;
    }}
    #Content {{
        background: transparent;
        border: none;
    }}
    #ContentSurface {{
        background: {palette.content_bg};
        border-top: 1px solid {palette.root_border};
        border-left: 1px solid {palette.root_border};
        border-top-left-radius: 18px;
        border-top-right-radius: 0px;
        border-bottom-right-radius: 16px;
        border-bottom-left-radius: 0px;
    }}
    QFrame[class="card"], QFrame[class="statusCard"] {{
        background: {palette.card_bg};
        border: 1px solid {palette.card_border};
        border-radius: 16px;
    }}
    QDialog#SettingsDialog QFrame#SettingsSection,
    QDialog#SettingsDialog QFrame[class="settingsSection"],
    QDialog#SettingsDialog QFrame[uiRole="settingsSection"],
    QFrame[class="settingsSection"], QFrame[uiRole="settingsSection"], QFrame#SettingsSection {{
        background: {("#181a1d" if palette.is_dark else "#edf3fa")};
        border: 1px solid {("#2d3137" if palette.is_dark else "#d4deec")};
        border-radius: 18px;
    }}
    QDialog#SettingsDialog QFrame#SettingsSectionBody,
    QDialog#SettingsDialog QFrame[class="settingsSectionBody"],
    QDialog#SettingsDialog QFrame[uiRole="settingsSectionBody"],
    QDialog#SettingsDialog QWidget#SettingsFormPanel,
    QFrame[class="settingsSectionBody"], QFrame[uiRole="settingsSectionBody"], QFrame#SettingsSectionBody, QWidget#SettingsFormPanel {{
        background: {("#1b1d21" if palette.is_dark else "#ffffff")};
        border: 1px solid {("#373c44" if palette.is_dark else "#d7e1ef")};
        border-radius: 14px;
    }}
    QFrame[class="hero"] {{
        background: {palette.hero_bg};
        border: 1px solid {palette.hero_border};
        border-radius: 16px;
    }}
    QFrame[class="softCard"] {{
        background: {palette.soft_card_bg};
        border: 1px solid {palette.card_border};
        border-radius: 16px;
    }}
    QLabel[class="title"] {{
        color: {palette.text_primary};
        font-size: 17pt;
        font-weight: 700;
    }}
    QLabel[class="muted"] {{
        color: {palette.text_muted};
    }}
    QLabel[class="toolbarMeta"] {{
        color: {palette.text_muted};
    }}
    QLabel[class="badge"], QLabel[class="chip"] {{
        color: {palette.badge_text};
        background: {palette.badge_bg};
        border: 1px solid {palette.badge_border};
        border-radius: 12px;
        padding: 6px 12px;
    }}
    QLabel[class="status"] {{
        color: {palette.status_text};
        background: {palette.status_bg};
        border: 1px solid {palette.status_border};
        border-radius: 12px;
        padding: 6px 12px;
        font-weight: 600;
    }}
    QToolButton[class="nav"] {{
        min-width: 46px;
        min-height: 46px;
        max-width: 46px;
        max-height: 46px;
        border-radius: 12px;
        border: 1px solid transparent;
        background: transparent;
    }}
    QToolButton[class="nav"]:hover {{
        background: {palette.nav_hover};
        border: 1px solid {palette.nav_hover_border};
    }}
    QToolButton[class="nav"]:checked {{
        background: {palette.nav_checked};
        border: 1px solid {palette.nav_checked_border};
    }}
    QToolButton[class="window"], QToolButton[class="action"] {{
        min-width: 26px;
        min-height: 26px;
        max-width: 26px;
        max-height: 26px;
        border: none;
        border-radius: 12px;
        background: transparent;
        padding: 0px;
        margin: 0px;
    }}
    QToolButton[class="sectionHeader"] {{
        min-height: 30px;
        border: none;
        background: transparent;
        color: {palette.text_primary};
        font-size: 14pt;
        font-weight: 700;
        text-align: left;
        padding: 0px 0px 0px 12px;
    }}
    QToolButton[class="sectionHeader"]:hover {{
        background: transparent;
    }}
    QToolButton[class="traffic"] {{
        min-width: 13px;
        min-height: 13px;
        max-width: 13px;
        max-height: 13px;
        border-radius: 6px;
        border: none;
        padding: 0px;
        margin: 0px;
        image: none;
    }}
    QToolButton[class="traffic"][role="close"], QToolButton[class="traffic"][role="min"] {{
        background-position: center;
        background-repeat: no-repeat;
    }}
    QToolButton[class="traffic"][role="close"] {{
        background: #8b93a1;
    }}
    QToolButton[class="traffic"][role="min"] {{
        background: #9aa2ae;
    }}
    QToolButton[class="traffic"]:hover {{
        border: none;
    }}
    QToolButton[class="traffic"][role="close"][showSymbol="true"] {{
        {close_rule}
    }}
    QToolButton[class="traffic"][role="min"][showSymbol="true"] {{
        {min_rule}
    }}
    QToolButton[class="window"]:hover, QToolButton[class="action"]:hover {{
        background: {palette.action_hover};
    }}
    QToolButton[class="action"]::menu-indicator {{
        image: none;
        width: 0px;
        height: 0px;
    }}
    QToolButton[class="window"][role="close"]:hover {{
        background: rgba(170, 84, 97, 0.62);
    }}
    QPushButton {{
        background: {palette.button_bg};
        border: 1px solid {palette.button_border};
        border-radius: 10px;
        padding: 9px 13px;
        color: {palette.text_primary};
    }}
    QPushButton:hover {{
        background: {palette.button_hover};
    }}
    QPushButton[class="dialogAction"] {{
        background: {("rgba(255, 255, 255, 0.035)" if palette.is_dark else "rgba(16, 32, 51, 0.04)")};
        border: 1px solid {("rgba(255, 255, 255, 0.08)" if palette.is_dark else "rgba(16, 32, 51, 0.14)")};
        border-radius: 10px;
        padding: 2px 10px;
        color: {palette.text_primary};
        min-height: 14px;
        font-size: 10pt;
    }}
    QToolButton[class="power"] {{
        min-width: 132px;
        min-height: 132px;
        max-width: 132px;
        max-height: 132px;
        border-radius: 66px;
        background: transparent;
        border: none;
        padding: 0px;
    }}
    QPushButton[class="primary"] {{
        background: {palette.primary_bg};
        border-color: {palette.primary_border};
        color: {palette.primary_text};
        font-weight: 700;
    }}
    QPushButton[class="danger"] {{
        background: {palette.danger_bg};
        border-color: {palette.danger_border};
        color: {palette.danger_text};
        font-weight: 700;
    }}
    QComboBox, QLineEdit, QTextEdit, QPlainTextEdit, QListWidget, QTableWidget {{
        background: {palette.input_bg};
        border: 1px solid {palette.input_border};
        border-radius: 10px;
        padding: 6px 8px;
        selection-background-color: {palette.selection_bg};
        gridline-color: {palette.gridline};
    }}
    QDialog#SettingsDialog QComboBox,
    QDialog#SettingsDialog QLineEdit,
    QDialog#SettingsDialog QSpinBox {{
        background: {("#1b1d21" if palette.is_dark else "#ffffff")};
        border: 1px solid {("#373c44" if palette.is_dark else "#b8c8dc")};
        color: {palette.text_primary};
        font-size: 13pt;
        min-height: 24px;
        padding: 3px 10px;
    }}
    QComboBox {{
        combobox-popup: 0;
        min-height: 22px;
        padding-right: 34px;
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 34px;
        border: none;
        border-left: 1px solid {("#373c44" if palette.is_dark else "#b8c8dc")};
        background: {("rgba(255, 255, 255, 0.02)" if palette.is_dark else "rgba(16, 32, 51, 0.045)")};
        border-top-right-radius: 10px;
        border-bottom-right-radius: 10px;
    }}
    QComboBox::down-arrow {{
        {chevron_rule}
        width: 12px;
        height: 12px;
    }}
    QComboBox QAbstractItemView {{
        background: {palette.input_bg};
        color: {palette.text_primary};
        border: 1px solid {palette.input_border};
        border-radius: 12px;
        padding: 4px;
        selection-background-color: transparent;
        outline: none;
    }}
    QComboBox QAbstractItemView::item {{
        background: transparent;
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 9px 12px;
        margin: 2px 4px;
    }}
    QComboBox QAbstractItemView::item:selected {{
        background: {palette.selection_bg};
        border: 1px solid {palette.input_border};
        color: {palette.text_primary};
    }}
    QListWidget::item {{
        background: {palette.card_bg};
        border: 1px solid {palette.card_border};
        border-radius: 10px;
        padding: 10px;
        margin: 2px 0;
    }}
    QListWidget::item:selected {{
        background: {palette.nav_checked};
        border: 1px solid {palette.nav_checked_border};
    }}
    QCheckBox {{
        background: transparent;
        spacing: 8px;
        padding: 2px 0;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 5px;
        border: 1px solid {palette.button_border};
        background: transparent;
    }}
    QCheckBox::indicator:checked {{
        border: 1px solid {palette.primary_border};
        background: {palette.primary_bg};
        {check_rule}
    }}
    QHeaderView::section {{
        background: {palette.header_bg};
        color: {palette.badge_text};
        border: 0;
        border-bottom: 1px solid {palette.input_border};
        padding: 8px;
    }}
    QFrame[class="fileModeCard"] {{
        background: {palette.card_bg};
        border: 1px solid {palette.card_border};
        border-radius: 14px;
    }}
    QFrame[class="fileModeCard"][hovered="true"] {{
        background: {palette.hero_bg};
        border: 1px solid {palette.nav_checked_border};
    }}
    QMenu {{
        background: {palette.root_bg};
        border: 1px solid {palette.card_border};
        border-radius: 8px;
        padding: 6px;
    }}
    QMenu::item {{
        padding: 7px 10px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background: {palette.nav_hover};
    }}
    QScrollArea {{
        background: transparent;
        border: none;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 8px;
        margin: 4px 0 4px 0;
        border: none;
    }}
    QScrollBar::handle:vertical {{
        background: {("#4b5058" if palette.is_dark else "#b2bccb")};
        min-height: 34px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {("#5a616b" if palette.is_dark else "#98a8bf")};
    }}
    QScrollBar::add-line:vertical,
    QScrollBar::sub-line:vertical {{
        height: 0px;
        background: transparent;
        border: none;
    }}
    QScrollBar::add-page:vertical,
    QScrollBar::sub-page:vertical {{
        background: transparent;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 8px;
        margin: 0 4px 0 4px;
        border: none;
    }}
    QScrollBar::handle:horizontal {{
        background: {("#4b5058" if palette.is_dark else "#b2bccb")};
        min-width: 34px;
        border-radius: 4px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {("#5a616b" if palette.is_dark else "#98a8bf")};
    }}
    QScrollBar::add-line:horizontal,
    QScrollBar::sub-line:horizontal {{
        width: 0px;
        background: transparent;
        border: none;
    }}
    QScrollBar::add-page:horizontal,
    QScrollBar::sub-page:horizontal {{
        background: transparent;
    }}
    QDialog#SettingsDialog QScrollBar:vertical, QDialog#SettingsDialog QScrollBar:horizontal {{
        width: 0px;
        height: 0px;
        background: transparent;
        border: none;
    }}
    QDialog#SettingsDialog QLabel[class="muted"] {{
        color: {palette.text_muted};
    }}
    """
