from __future__ import annotations

from dataclasses import asdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QPointF, QSize, Qt, QPropertyAnimation, QTimer, QUrl, Signal
from PySide6.QtGui import QAction, QActionGroup, QCloseEvent, QDesktopServices, QIcon, QIntValidator, QMouseEvent, QTextCursor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from zapret_hub_mac.bootstrap import ApplicationContext
from zapret_hub_mac import __version__
from zapret_hub_mac.domain import AppSettings
from zapret_hub_mac.ui.theme import build_stylesheet, resolve_palette
from zapret_hub_mac.ui.widgets import AnimatedNavButton, AnimatedPowerButton, PowerAuraWidget, SidebarPanel


@dataclass(slots=True)
class NavItem:
    key: str
    icon_file: str
    tooltip: str


class MainWindowBridge(QObject):
    refresh_requested = Signal()
    runtime_failed = Signal(str)


class CollapsibleSection(QFrame):
    def __init__(self, title: str, expanded: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("SettingsSection")
        self.setProperty("class", "settingsSection")
        self.setProperty("uiRole", "settingsSection")
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 16)
        layout.setSpacing(10)

        self.toggle_btn = QToolButton(self)
        self.toggle_btn.setProperty("class", "sectionHeader")
        self.toggle_btn.setText(f"     {title}")
        self.toggle_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_btn.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.toggle_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.toggle_btn.setIconSize(QSize(9, 9))
        self.toggle_btn.clicked.connect(self.toggle)
        layout.addWidget(self.toggle_btn)

        self.body = QFrame(self)
        self.body.setObjectName("SettingsSectionBody")
        self.body.setProperty("class", "settingsSectionBody")
        self.body.setProperty("uiRole", "settingsSectionBody")
        self.body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(14, 14, 14, 14)
        self.body_layout.setSpacing(14)
        self.body_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.body.setVisible(expanded)
        layout.addWidget(self.body)

    def toggle(self) -> None:
        visible = not self.body.isVisible()
        self.body.setVisible(visible)
        self.toggle_btn.setArrowType(Qt.ArrowType.DownArrow if visible else Qt.ArrowType.RightArrow)


class AdaptiveComboBox(QComboBox):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        popup_view = QListView(self)
        popup_view.setObjectName("ComboPopupView")
        popup_view.setFrameShape(QFrame.Shape.NoFrame)
        popup_view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        popup_view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        popup_view.setSpacing(2)
        self.setView(popup_view)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

    def apply_theme(self, theme: str) -> None:
        palette = resolve_palette(theme)
        bg = "#191c20" if palette.is_dark else "#ffffff"
        border = "#383d45" if palette.is_dark else "#ced9e7"
        selected = "#262b32" if palette.is_dark else "#deebfb"
        text = palette.text_primary
        view = self.view()
        view.setStyleSheet(
            f"""
            QListView#ComboPopupView {{
                background: {bg};
                color: {text};
                border: 1px solid {border};
                border-radius: 12px;
                padding: 6px;
                outline: none;
            }}
            QListView#ComboPopupView::item {{
                background: transparent;
                color: {text};
                border: none;
                border-radius: 8px;
                min-height: 22px;
                padding: 4px 12px;
                margin: 1px 0px;
            }}
            QListView#ComboPopupView::item:selected {{
                background: {selected};
                color: {text};
            }}
            """
        )
        container = view.window()
        container.setObjectName("ComboPopupContainer")
        container.setStyleSheet(
            f"QFrame#ComboPopupContainer, QWidget#ComboPopupContainer {{ background: {bg}; border: 1px solid {border}; border-radius: 12px; }}"
        )

    def showPopup(self) -> None:
        self.view().setMinimumWidth(self._popup_width())
        super().showPopup()
        container = self.view().window()
        width = self._popup_width()
        if container.width() < width:
            container.resize(width, container.height())

    def _popup_width(self) -> int:
        metrics = self.fontMetrics()
        widest = 0
        for index in range(self.count()):
            widest = max(widest, metrics.horizontalAdvance(self.itemText(index)))
        return max(self.width(), widest + 54)


class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._language = settings.language
        self.setWindowTitle("Settings")
        self.setModal(True)
        self.setObjectName("SettingsDialog")
        self.setFixedSize(680, 820)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self._drag_pos: QPoint | None = None
        if parent is not None:
            self.setStyleSheet(parent.styleSheet())

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        shell = QFrame(self)
        shell.setObjectName("DialogRoot")
        shell_layout = QVBoxLayout(shell)
        shell_layout.setContentsMargins(0, 0, 0, 0)
        shell_layout.setSpacing(0)
        root.addWidget(shell)

        title_bar = QFrame(shell)
        title_bar.setObjectName("DialogTitleBar")
        title_bar.setFixedHeight(50)
        title_bar.installEventFilter(self)
        title_row = QHBoxLayout(title_bar)
        title_row.setContentsMargins(16, 10, 16, 8)
        title_row.setSpacing(8)
        self._traffic_buttons: list[QToolButton] = []
        self._traffic_hover_cluster = None

        traffic_cluster = QWidget(title_bar)
        traffic_cluster.setProperty("class", "transparentPane")
        traffic_cluster.setProperty("uiRole", "trafficCluster")
        traffic_cluster.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        traffic_cluster_layout = QHBoxLayout(traffic_cluster)
        traffic_cluster_layout.setContentsMargins(0, 0, 0, 0)
        traffic_cluster_layout.setSpacing(10)
        traffic_cluster.installEventFilter(self)
        self._traffic_hover_cluster = traffic_cluster

        for role, handler in (("close", self.reject),):
            btn = QToolButton(title_bar)
            btn.setProperty("class", "traffic")
            btn.setProperty("role", role)
            btn.setProperty("showSymbol", False)
            btn.setFixedSize(13, 13)
            btn.installEventFilter(self)
            btn.clicked.connect(handler)
            traffic_cluster_layout.addWidget(btn)
            self._traffic_buttons.append(btn)
        title_row.addWidget(traffic_cluster)

        drag_surface = QWidget(title_bar)
        drag_surface.setObjectName("DialogTitleDragSurface")
        drag_surface.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        drag_surface.installEventFilter(self)
        title_row.addWidget(drag_surface, 1)

        self.cancel_button = QPushButton(self._t("Отмена", "Cancel"))
        self.cancel_button.setProperty("class", "dialogAction")
        self.cancel_button.clicked.connect(self.reject)
        title_row.addWidget(self.cancel_button)

        self.save_button = QPushButton(self._t("Сохранить", "Save"))
        self.save_button.setProperty("class", "dialogAction")
        self.save_button.clicked.connect(self.accept)
        title_row.addWidget(self.save_button)

        title = QLabel("Настройки")
        title.setProperty("class", "title")
        title.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        title_row.addWidget(title)
        shell_layout.addWidget(title_bar)

        scroll = QScrollArea(shell)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setStyleSheet("background: transparent; border: none;")
        shell_layout.addWidget(scroll, 1)

        content = QWidget()
        content.setObjectName("DialogBody")
        content.setProperty("class", "dialogCanvas")
        content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        scroll.setWidget(content)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 10, 18, 18)
        layout.setSpacing(14)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._section_frames: list[QFrame] = []
        self._section_bodies: list[QFrame] = []
        self._surface_panels: list[QWidget] = []
        self._settings_inputs: list[QWidget] = []

        general_section = CollapsibleSection(self._t("Общие настройки", "General settings"), expanded=True)
        self._section_frames.append(general_section)
        self._section_bodies.append(general_section.body)
        general_form = QFormLayout()
        general_form.setSpacing(10)
        general_form.setHorizontalSpacing(20)
        general_form.setVerticalSpacing(14)
        general_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        general_form.setFormAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        general_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        general_panel = QWidget()
        general_panel.setObjectName("SettingsFormPanel")
        general_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._surface_panels.append(general_panel)
        general_panel_layout = QVBoxLayout(general_panel)
        general_panel_layout.setContentsMargins(16, 14, 16, 14)
        general_panel_layout.setSpacing(12)

        self.theme_combo = AdaptiveComboBox()
        for theme_id, label in (
            ("system", self._t("Системная", "System")),
            ("oled", self._t("Тёмная", "Dark")),
            ("light", self._t("Светлая", "Light")),
        ):
            self.theme_combo.addItem(label, theme_id)
        self.theme_combo.setMinimumHeight(28)
        self.theme_combo.setMinimumWidth(190)
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(settings.theme)))
        self._settings_inputs.append(self.theme_combo)
        general_form.addRow(self._form_label(self._t("Тема", "Theme")), self.theme_combo)

        self.language_combo = AdaptiveComboBox()
        for language_id, label in (("ru", "Русский"), ("en", "English")):
            self.language_combo.addItem(label, language_id)
        self.language_combo.setMinimumHeight(28)
        self.language_combo.setMinimumWidth(190)
        self.language_combo.setCurrentIndex(max(0, self.language_combo.findData(settings.language)))
        self._settings_inputs.append(self.language_combo)
        general_form.addRow(self._form_label(self._t("Язык", "Language")), self.language_combo)
        general_panel_layout.addLayout(general_form)

        self.launch_at_login = QCheckBox(self._t("Запускать при входе в систему", "Launch at login"))
        self.launch_at_login.setChecked(settings.launch_at_login)
        general_panel_layout.addWidget(self.launch_at_login)

        self.launch_hidden = QCheckBox(self._t("Запускать скрытым в строке меню", "Start hidden in menu bar"))
        self.launch_hidden.setChecked(settings.launch_hidden)
        general_panel_layout.addWidget(self.launch_hidden)

        self.auto_run_components = QCheckBox(self._t("Автоматически запускать включённые компоненты", "Auto-run enabled components"))
        self.auto_run_components.setChecked(settings.auto_run_components)
        general_panel_layout.addWidget(self.auto_run_components)

        self.check_updates = QCheckBox(self._t("Проверять обновления автоматически (при запуске и каждые 5 часов)", "Check updates automatically (on launch and every 5 hours)"))
        self.check_updates.setChecked(settings.check_updates_on_start)
        general_panel_layout.addWidget(self.check_updates)
        general_section.body_layout.addWidget(general_panel)
        layout.addWidget(general_section)

        tg_section = CollapsibleSection(self._t("Настройки Telegram", "Telegram settings"), expanded=True)
        self._section_frames.append(tg_section)
        self._section_bodies.append(tg_section.body)
        tg_form = QFormLayout()
        tg_form.setSpacing(10)
        tg_form.setHorizontalSpacing(20)
        tg_form.setVerticalSpacing(14)
        tg_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        tg_form.setFormAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        tg_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        tg_panel = QWidget()
        tg_panel.setObjectName("SettingsFormPanel")
        tg_panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._surface_panels.append(tg_panel)
        tg_panel_layout = QVBoxLayout(tg_panel)
        tg_panel_layout.setContentsMargins(16, 14, 16, 14)
        tg_panel_layout.setSpacing(0)

        self.tg_host_input = QLineEdit(settings.tg_proxy_host)
        self.tg_host_input.setMinimumHeight(28)
        self.tg_host_input.setMinimumWidth(300)
        self.tg_host_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._settings_inputs.append(self.tg_host_input)
        tg_form.addRow(self._form_label(self._t("Хост Telegram", "Telegram host")), self.tg_host_input)

        self.tg_port_input = QLineEdit(str(int(settings.tg_proxy_port)))
        self.tg_port_input.setValidator(QIntValidator(1, 65535, self))
        self.tg_port_input.setMinimumHeight(28)
        self.tg_port_input.setMinimumWidth(300)
        self.tg_port_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._settings_inputs.append(self.tg_port_input)
        tg_form.addRow(self._form_label(self._t("Порт Telegram", "Telegram port")), self.tg_port_input)

        self.tg_secret_input = QLineEdit(settings.tg_proxy_secret)
        self.tg_secret_input.setMinimumHeight(28)
        self.tg_secret_input.setMinimumWidth(300)
        self.tg_secret_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.tg_secret_input.setPlaceholderText(self._t("автоматически сгенерируется, если пусто", "auto-generated if empty"))
        self._settings_inputs.append(self.tg_secret_input)
        tg_form.addRow(self._form_label(self._t("Секрет Telegram", "Telegram secret")), self.tg_secret_input)
        tg_panel_layout.addLayout(tg_form)
        tg_section.body_layout.addWidget(tg_panel)
        layout.addWidget(tg_section)

        engine_title = "ByeDPI" if settings.traffic_engine_id == "zapret" else "SpoofDPI"
        engine_section = CollapsibleSection(self._t(f"Настройки {engine_title}", f"{engine_title} settings"), expanded=False)
        self._section_frames.append(engine_section)
        self._section_bodies.append(engine_section.body)

        self.spoofdpi_box = QWidget()
        self.spoofdpi_box.setObjectName("SettingsFormPanel")
        self.spoofdpi_box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._surface_panels.append(self.spoofdpi_box)
        spoofdpi_form = QFormLayout(self.spoofdpi_box)
        spoofdpi_form.setSpacing(10)
        spoofdpi_form.setHorizontalSpacing(20)
        spoofdpi_form.setVerticalSpacing(14)
        spoofdpi_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        spoofdpi_form.setFormAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        spoofdpi_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.spoofdpi_host_input = QLineEdit(settings.spoofdpi_host)
        self.spoofdpi_host_input.setMinimumHeight(28)
        self.spoofdpi_host_input.setMinimumWidth(300)
        self._settings_inputs.append(self.spoofdpi_host_input)
        spoofdpi_form.addRow("SpoofDPI host", self.spoofdpi_host_input)

        self.spoofdpi_port_input = QLineEdit(str(int(settings.spoofdpi_port)))
        self.spoofdpi_port_input.setValidator(QIntValidator(1, 65535, self))
        self.spoofdpi_port_input.setMinimumHeight(28)
        self.spoofdpi_port_input.setMinimumWidth(300)
        self.spoofdpi_port_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._settings_inputs.append(self.spoofdpi_port_input)
        spoofdpi_form.addRow("SpoofDPI port", self.spoofdpi_port_input)

        self.spoofdpi_args_input = QLineEdit(settings.spoofdpi_args)
        self.spoofdpi_args_input.setMinimumHeight(28)
        self.spoofdpi_args_input.setMinimumWidth(300)
        self.spoofdpi_args_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.spoofdpi_args_input.setPlaceholderText("--dns-mode https --dns-https-url https://1.1.1.1/dns-query --https-split-mode chunk --https-chunk-size 1 --silent true")
        self._settings_inputs.append(self.spoofdpi_args_input)
        spoofdpi_form.addRow("SpoofDPI args", self.spoofdpi_args_input)

        self.zapret_box = QWidget()
        self.zapret_box.setObjectName("SettingsFormPanel")
        self.zapret_box.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._surface_panels.append(self.zapret_box)
        zapret_form = QFormLayout(self.zapret_box)
        zapret_form.setSpacing(10)
        zapret_form.setHorizontalSpacing(20)
        zapret_form.setVerticalSpacing(14)
        zapret_form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        zapret_form.setFormAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        zapret_form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.zapret_host_input = QLineEdit(settings.zapret_host)
        self.zapret_host_input.setMinimumHeight(28)
        self.zapret_host_input.setMinimumWidth(300)
        self._settings_inputs.append(self.zapret_host_input)
        zapret_form.addRow("ByeDPI host", self.zapret_host_input)

        self.zapret_port_input = QLineEdit(str(int(settings.zapret_port)))
        self.zapret_port_input.setValidator(QIntValidator(1, 65535, self))
        self.zapret_port_input.setMinimumHeight(28)
        self.zapret_port_input.setMinimumWidth(300)
        self.zapret_port_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._settings_inputs.append(self.zapret_port_input)
        zapret_form.addRow("ByeDPI port", self.zapret_port_input)

        self.zapret_args_input = QLineEdit(settings.zapret_args)
        self.zapret_args_input.setMinimumHeight(28)
        self.zapret_args_input.setMinimumWidth(300)
        self.zapret_args_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.zapret_args_input.setPlaceholderText("-d 1+s")
        self._settings_inputs.append(self.zapret_args_input)
        zapret_form.addRow("ByeDPI args", self.zapret_args_input)

        self.spoofdpi_box.setVisible(settings.traffic_engine_id == "spoofdpi")
        self.zapret_box.setVisible(settings.traffic_engine_id == "zapret")
        engine_section.body_layout.addWidget(self.spoofdpi_box)
        engine_section.body_layout.addWidget(self.zapret_box)
        layout.addWidget(engine_section)

        credits = QFrame()
        credits.setObjectName("SettingsSection")
        credits.setProperty("class", "settingsSection")
        credits.setProperty("uiRole", "settingsSection")
        credits.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._section_frames.append(credits)
        credits_layout = QVBoxLayout(credits)
        credits_layout.setContentsMargins(16, 14, 16, 16)
        credits_layout.setSpacing(6)
        credits_title = QLabel(self._t("Авторы", "Credits"))
        credits_title.setProperty("class", "title")
        credits_layout.addWidget(credits_title)
        credits_layout.addWidget(QLabel("PulseRoute Engine: goshkow"))
        credits_layout.addWidget(QLabel("TG WS Proxy core: Flowseal"))
        credits_layout.addWidget(QLabel("SpoofDPI core: xvzc"))
        credits_layout.addWidget(QLabel("ByeDPI core: ollesss / ciadpi"))
        layout.addWidget(credits)
        effective_theme = settings.theme if settings.theme in {"light", "oled"} else "oled"
        if parent is not None and hasattr(parent, "context"):
            try:
                effective_theme = parent.context.settings.detect_effective_theme()
            except Exception:
                pass
        self._apply_surface_theme(effective_theme)
        self._apply_combo_theme(effective_theme)
        self._apply_input_theme(effective_theme)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def _form_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setMinimumHeight(26)
        return label

    def _t(self, ru: str, en: str) -> str:
        return ru if self._language == "ru" else en

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is getattr(self, "_traffic_hover_cluster", None) or watched in getattr(self, "_traffic_buttons", []):
            if event.type() in {QEvent.Type.Enter, QEvent.Type.HoverEnter}:
                self._set_traffic_symbols_visible(True)
            elif event.type() in {QEvent.Type.Leave, QEvent.Type.HoverLeave}:
                self._set_traffic_symbols_visible(False)
        if watched.objectName() in {"DialogTitleBar", "DialogTitleDragSurface"}:
            if event.type() == QEvent.Type.MouseButtonPress and isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if event.type() == QEvent.Type.MouseMove and isinstance(event, QMouseEvent) and self._drag_pos is not None:
                if event.buttons() & Qt.MouseButton.LeftButton:
                    self.move(event.globalPosition().toPoint() - self._drag_pos)
                    return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_pos = None
                return True
        return super().eventFilter(watched, event)

    def _set_traffic_symbols_visible(self, visible: bool) -> None:
        for button in getattr(self, "_traffic_buttons", []):
            if button.property("showSymbol") == visible:
                continue
            button.setProperty("showSymbol", visible)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def values(self) -> dict[str, object]:
        tg_port_text = self.tg_port_input.text().strip()
        tg_port = int(tg_port_text) if tg_port_text.isdigit() else 1443
        spoofdpi_port_text = self.spoofdpi_port_input.text().strip()
        spoofdpi_port = int(spoofdpi_port_text) if spoofdpi_port_text.isdigit() else 11080
        zapret_port_text = self.zapret_port_input.text().strip()
        zapret_port = int(zapret_port_text) if zapret_port_text.isdigit() else 11080
        return {
            "theme": str(self.theme_combo.currentData()),
            "language": str(self.language_combo.currentData()),
            "tg_proxy_host": self.tg_host_input.text().strip() or "127.0.0.1",
            "tg_proxy_port": tg_port,
            "tg_proxy_secret": self.tg_secret_input.text().strip(),
            "spoofdpi_host": self.spoofdpi_host_input.text().strip() or "127.0.0.1",
            "spoofdpi_port": spoofdpi_port,
            "spoofdpi_args": self.spoofdpi_args_input.text().strip() or "--dns-mode https --dns-https-url https://1.1.1.1/dns-query --https-split-mode chunk --https-chunk-size 1 --silent true",
            "zapret_host": self.zapret_host_input.text().strip() or "127.0.0.1",
            "zapret_port": zapret_port,
            "zapret_args": self.zapret_args_input.text().strip() or "-d 1+s",
            "launch_at_login": self.launch_at_login.isChecked(),
            "launch_hidden": self.launch_hidden.isChecked(),
            "auto_run_components": self.auto_run_components.isChecked(),
            "notifications_enabled": True,
            "check_updates_on_start": self.check_updates.isChecked(),
            "tg_auto_prompt_on_start": True,
        }

    def _apply_combo_theme(self, theme: str) -> None:
        for combo in self.findChildren(AdaptiveComboBox):
            combo.apply_theme(theme)

    def _apply_input_theme(self, theme: str) -> None:
        palette = resolve_palette(theme)
        bg = "#1b1d21" if palette.is_dark else "#ffffff"
        border = "#373c44" if palette.is_dark else "#b6c6db"
        divider = "#373c44" if palette.is_dark else "#bfd0e2"
        text = palette.text_primary
        for widget in self._settings_inputs:
            if isinstance(widget, AdaptiveComboBox):
                widget.setStyleSheet(
                    f"""
                    QComboBox {{
                        background: {bg};
                        border: 1px solid {border};
                        border-radius: 10px;
                        color: {text};
                        font-size: 13pt;
                        padding: 3px 10px;
                        min-height: 24px;
                        padding-right: 34px;
                    }}
                    QComboBox::drop-down {{
                        width: 34px;
                        border: none;
                        border-left: 1px solid {divider};
                        background: transparent;
                        border-top-right-radius: 10px;
                        border-bottom-right-radius: 10px;
                    }}
                    """
                )
            elif isinstance(widget, QLineEdit):
                widget.setStyleSheet(
                    f"""
                    QLineEdit {{
                        background: {bg};
                        border: 1px solid {border};
                        border-radius: 10px;
                        color: {text};
                        font-size: 13pt;
                        padding: 3px 10px;
                        min-height: 24px;
                    }}
                    """
                )

    def _apply_surface_theme(self, theme: str) -> None:
        palette = resolve_palette(theme)
        section_bg = "#181a1d" if palette.is_dark else "#edf3fa"
        section_border = "#2d3137" if palette.is_dark else "#d4deec"
        body_bg = "#1b1d21" if palette.is_dark else "#ffffff"
        body_border = "#373c44" if palette.is_dark else "#d7e1ef"
        for frame in self._section_frames:
            selector = frame.metaObject().className()
            frame.setStyleSheet(
                f"{selector}#{frame.objectName()} {{ background: {section_bg}; border: 1px solid {section_border}; border-radius: 18px; }}"
            )
        for frame in self._section_bodies:
            selector = frame.metaObject().className()
            frame.setStyleSheet(
                f"{selector}#{frame.objectName()} {{ background: {body_bg}; border: 1px solid {body_border}; border-radius: 14px; }}"
            )
        for panel in self._surface_panels:
            selector = panel.metaObject().className()
            panel.setStyleSheet(
                f"{selector}#{panel.objectName()} {{ background: transparent; border: none; }}"
            )


class MainWindow(QMainWindow):
    def __init__(self, context: ApplicationContext) -> None:
        super().__init__()
        self.context = context
        self._drag_pos: QPoint | None = None
        self._drag_active = False
        self._page_transition: QPropertyAnimation | None = None
        self._nav_buttons: list[QToolButton] = []
        self._status_labels: dict[str, QLabel] = {}
        self._status_title_labels: dict[str, QLabel] = {}
        self._component_cards: dict[str, QFrame] = {}
        self._power_running = False
        self._power_target_running: bool | None = None
        self._pending_click_wave: str | None = None
        self._power_caption_base = ""
        self._power_caption_dots_phase = 0
        self._power_caption_timer = QTimer(self)
        self._power_caption_timer.setInterval(320)
        self._power_caption_timer.timeout.connect(self._advance_power_caption_dots)
        self._tray_icon = None
        self._traffic_buttons: list[QToolButton] = []
        self._traffic_hover_cluster = None
        self._force_quit = False
        self._log_offsets: dict[str, int] = {}
        self._activate_regular = None
        self._activate_accessory = None
        self._tray_menu_updater = None
        self._tray_initializer = None
        self._bridge = MainWindowBridge(self)
        self._bridge.refresh_requested.connect(self.refresh_all)
        self._bridge.runtime_failed.connect(self._show_runtime_error)
        self._nav_items = [
            NavItem("dashboard", "home.svg", self._t("Главная", "Home")),
            NavItem("components", "components.svg", self._t("Компоненты", "Components")),
            NavItem("logs", "logs.svg", self._t("Логи", "Logs")),
        ]

        self.setWindowTitle("Zapret Hub")
        self.setFixedSize(860, 520)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowFlag(Qt.WindowType.WindowMinimizeButtonHint, True)

        self._build_menu()
        self._build_ui()
        self._apply_theme()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(1100)
        self.refresh_timer.timeout.connect(self.refresh_passive)
        self.refresh_timer.start()
        self.refresh_all()

    def _t(self, ru: str, en: str) -> str:
        return ru if self.context.settings.get().language == "ru" else en

    def _build_menu(self) -> None:
        menu_bar = self.menuBar()
        menu_bar.setNativeMenuBar(True)

        app_menu = menu_bar.addMenu(self._t("Приложение", "Application"))
        refresh_action = QAction(self._t("Обновить", "Refresh"), self)
        refresh_action.triggered.connect(self.refresh_all)
        app_menu.addAction(refresh_action)

        settings_action = QAction(self._t("Настройки", "Settings"), self)
        settings_action.triggered.connect(self._open_settings_dialog)
        app_menu.addAction(settings_action)

        control_menu = menu_bar.addMenu(self._t("Управление", "Control"))
        start_action = QAction(self._t("Запустить включённые компоненты", "Start Enabled Components"), self)
        start_action.triggered.connect(self._start_enabled)
        stop_action = QAction(self._t("Остановить все компоненты", "Stop All Components"), self)
        stop_action.triggered.connect(self._stop_all)
        control_menu.addAction(start_action)
        control_menu.addAction(stop_action)

        help_menu = menu_bar.addMenu(self._t("Помощь", "Help"))
        tg_action = QAction(self._t("Открыть Telegram proxy-ссылку", "Open Telegram Proxy Link"), self)
        tg_action.triggered.connect(self.context.processes.prompt_telegram_proxy_link)
        help_menu.addAction(tg_action)

    def _build_ui(self) -> None:
        shell = QWidget()
        shell.setObjectName("WindowShell")
        root = QVBoxLayout(shell)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(0)

        frame = QFrame()
        frame.setObjectName("RootFrame")
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)
        frame_layout.addWidget(self._build_title_bar())

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_content(), 1)
        frame_layout.addLayout(body)

        root.addWidget(frame)
        self.setCentralWidget(shell)

    def _build_title_bar(self) -> QWidget:
        bar = QFrame()
        bar.setObjectName("TitleBar")
        bar.setFixedHeight(48)
        bar.installEventFilter(self)
        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 10, 12, 8)
        row.setSpacing(8)

        traffic_cluster = QWidget(bar)
        traffic_cluster.setProperty("class", "transparentPane")
        traffic_cluster.setProperty("uiRole", "trafficCluster")
        traffic_cluster.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        traffic_cluster_layout = QHBoxLayout(traffic_cluster)
        traffic_cluster_layout.setContentsMargins(0, 0, 0, 0)
        traffic_cluster_layout.setSpacing(10)
        traffic_cluster.installEventFilter(self)
        self._traffic_hover_cluster = traffic_cluster

        for role, handler in (("close", self.close), ("min", self.showMinimized)):
            btn = QToolButton(bar)
            btn.setProperty("class", "traffic")
            btn.setProperty("role", role)
            btn.setProperty("showSymbol", False)
            btn.setFixedSize(13, 13)
            btn.installEventFilter(self)
            btn.clicked.connect(handler)
            traffic_cluster_layout.addWidget(btn)
            self._traffic_buttons.append(btn)
        row.addWidget(traffic_cluster)

        row.addSpacing(6)
        self._drag_surface = QWidget(bar)
        self._drag_surface.setObjectName("TitleDragSurface")
        self._drag_surface.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._drag_surface.installEventFilter(self)
        row.addWidget(self._drag_surface, 1)

        self.author_label = QLabel("by goshkow", bar)
        self.author_label.setProperty("class", "toolbarMeta")
        row.addWidget(self.author_label)

        tools_btn = QToolButton(bar)
        tools_btn.setProperty("class", "action")
        tools_btn.setIcon(self._icon("tool.svg"))
        tools_btn.setIconSize(QSize(16, 16))
        tools_btn.setToolTip(self._t("Инструменты", "Tools"))
        tools_btn.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        tools_btn.setMenu(self._build_tools_menu())
        row.addWidget(tools_btn)

        settings_btn = QToolButton(bar)
        settings_btn.setProperty("class", "action")
        settings_btn.setIcon(self._icon("settings.svg"))
        settings_btn.setIconSize(QSize(16, 16))
        settings_btn.setToolTip(self._t("Настройки", "Settings"))
        settings_btn.clicked.connect(self._open_settings_dialog)
        row.addWidget(settings_btn)

        title = QLabel("Zapret Hub", bar)
        title.setProperty("class", "title")
        row.addWidget(title)

        icon = QLabel(bar)
        icon.setPixmap(self._icon("app.png").pixmap(20, 20))
        row.addWidget(icon)
        return bar

    def _build_tools_menu(self) -> QMenu:
        menu = QMenu(self)
        rebuild = QAction(self._t("Пересобрать runtime-состояние", "Rebuild runtime state"), self)
        rebuild.triggered.connect(self._rebuild_runtime)
        menu.addAction(rebuild)

        tg_link = QAction(self._t("Открыть ссылку Telegram", "Open Telegram link"), self)
        tg_link.triggered.connect(self.context.processes.prompt_telegram_proxy_link)
        menu.addAction(tg_link)
        return menu

    def _build_sidebar(self) -> QWidget:
        self.sidebar_panel = SidebarPanel()
        self.sidebar_panel.setObjectName("Sidebar")
        self.sidebar_panel.setFixedWidth(78)
        col = QVBoxLayout(self.sidebar_panel)
        col.setContentsMargins(12, 12, 12, 12)
        col.setSpacing(10)

        for index, item in enumerate(self._nav_items):
            btn = AnimatedNavButton()
            btn.setProperty("class", "nav")
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setIcon(self._icon(item.icon_file))
            btn.setIconSize(QSize(26, 26))
            btn.setToolTip(item.tooltip)
            btn.clicked.connect(lambda _=False, i=index: self._switch_page(i))
            self._nav_buttons.append(btn)
            col.addWidget(btn)
        col.addStretch(1)
        if self._nav_buttons:
            self._nav_buttons[0].setChecked(True)
        QTimer.singleShot(0, lambda: self._sync_nav_highlight(animated=False))
        return self.sidebar_panel

    def _build_content(self) -> QWidget:
        pane = QFrame()
        pane.setObjectName("Content")
        layout = QVBoxLayout(pane)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        body = QFrame()
        body.setObjectName("ContentSurface")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(12, 12, 12, 12)
        body_layout.setSpacing(8)

        pages_host = QWidget()
        pages_host.setProperty("class", "pageCanvas")
        host_layout = QVBoxLayout(pages_host)
        host_layout.setContentsMargins(0, 0, 0, 0)
        host_layout.setSpacing(0)

        self.pages = QStackedWidget()
        self.pages.setObjectName("PagesStack")
        self.pages.setProperty("class", "pageCanvas")
        self.pages.addWidget(self._build_dashboard_page())
        self.pages.addWidget(self._build_components_page())
        self.pages.addWidget(self._build_logs_page())
        host_layout.addWidget(self.pages)

        self._page_opacity_effect = QGraphicsOpacityEffect(pages_host)
        self._page_opacity_effect.setOpacity(1.0)
        pages_host.setGraphicsEffect(self._page_opacity_effect)
        body_layout.addWidget(pages_host)
        layout.addWidget(body, 1)
        return pane

    def _card(self, css_class: str = "card") -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setProperty("class", css_class)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)
        return card, layout

    def _build_dashboard_page(self) -> QWidget:
        page = QWidget()
        page.setProperty("class", "pageRoot")
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        top, top_layout = self._card("hero")
        title = QLabel(self._t("Быстрый доступ", "Quick access"))
        title.setObjectName("DashboardTitle")
        title.setProperty("class", "title")
        top_layout.addWidget(title)

        power_block = QWidget()
        power_block.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        power_block.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        power_layout = QVBoxLayout(power_block)
        power_layout.setContentsMargins(0, 8, 0, 0)
        power_layout.setSpacing(6)

        self.power_aura = PowerAuraWidget(top)
        self.power_aura.lower()

        power_stage = QWidget(power_block)
        power_stage.setFixedSize(224, 194)
        power_stage.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        power_stage.setStyleSheet("background: transparent;")

        self.power_button = AnimatedPowerButton(power_stage)
        self.power_button.setProperty("class", "power")
        self.power_button.setIcon(self._icon("power.svg"))
        self.power_button.setIconSize(QSize(42, 42))
        self.power_button.setGeometry(46, 28, 132, 132)
        self.power_button.clicked.connect(self._toggle_master)

        self.power_caption = QLabel("ВЫКЛ")
        self.power_caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.power_caption.setProperty("class", "title")
        self.power_caption.setFixedWidth(power_stage.width())

        power_layout.addWidget(power_stage, 0, Qt.AlignmentFlag.AlignHCenter)
        power_layout.addWidget(self.power_caption, 0, Qt.AlignmentFlag.AlignHCenter)
        top_layout.addStretch(1)
        top_layout.addWidget(power_block, 0, Qt.AlignmentFlag.AlignHCenter)
        top_layout.addStretch(1)
        self._power_stage = power_stage
        QTimer.singleShot(0, self._sync_power_aura_geometry)

        badges_row = QHBoxLayout()
        badges_row.setSpacing(10)
        for key, icon_name, title_text in [
            ("app", "status_ok.svg", self._t("Приложение", "Application")),
            ("proxy", "component_zapret.svg", self._t("Прокси", "Proxy")),
            ("tg", "component_tg.svg", "Telegram"),
            ("engine", "tool.svg", "ByeDPI"),
            ("theme", "status_theme.svg", self._t("Тема", "Theme")),
        ]:
            badge_card, badge_title, badge_label = self._build_status_badge(icon_name, title_text)
            self._status_title_labels[key] = badge_title
            self._status_labels[key] = badge_label
            badges_row.addWidget(badge_card)

        root.addWidget(top)
        top_layout.addLayout(badges_row)
        return page

    def _build_status_badge(self, icon_name: str, title: str) -> tuple[QFrame, QLabel, QLabel]:
        card, layout = self._card("statusCard")
        card.setMinimumHeight(102)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        head = QHBoxLayout()
        icon_label = QLabel()
        icon_label.setPixmap(self._icon(icon_name).pixmap(18, 18))
        text_label = QLabel(title)
        text_label.setProperty("class", "muted")
        head.addWidget(icon_label)
        head.addWidget(text_label)
        head.addStretch(1)
        layout.addLayout(head)

        value = QLabel("...")
        value.setProperty("class", "title")
        layout.addWidget(value)
        return card, text_label, value

    def _build_components_page(self) -> QWidget:
        page = QWidget()
        page.setProperty("class", "pageRoot")
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        title = QLabel(self._t("Компоненты", "Components"))
        title.setProperty("class", "title")
        root.addWidget(title)
        root.addSpacing(8)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setProperty("class", "transparentPane")

        self.components_cards_root = QWidget()
        self.components_cards_root.setProperty("class", "transparentPane")
        self.components_cards_root.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.components_cards_layout = QGridLayout(self.components_cards_root)
        self.components_cards_layout.setContentsMargins(0, 0, 0, 0)
        self.components_cards_layout.setHorizontalSpacing(12)
        self.components_cards_layout.setVerticalSpacing(12)
        self.components_cards_layout.setColumnStretch(0, 1)
        self.components_cards_layout.setColumnStretch(1, 1)
        scroll.setWidget(self.components_cards_root)
        root.addWidget(scroll, 1)
        return page

    def _build_component_card(self, component_id: str, title: str, description: str, icon_name: str) -> QFrame:
        card, layout = self._card("card")
        card.setMinimumHeight(300)
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        icon = QLabel()
        icon.setPixmap(self._icon(icon_name).pixmap(34, 34))
        layout.addWidget(icon)

        header = QLabel(title)
        header.setProperty("class", "title")
        layout.addWidget(header)

        body = QLabel(description)
        body.setProperty("class", "muted")
        body.setWordWrap(True)
        layout.addWidget(body)

        state = next((item for item in self.context.processes.list_states() if item.component_id == component_id), None)
        component = next((item for item in self.context.processes.list_components() if item.id == component_id), None)
        status_value = QLabel(f"{self._t('Статус', 'Status')}: {self._localize_state(state.status if state else 'unknown')}")
        status_value.setProperty("class", "chip")
        layout.addWidget(status_value)

        if component and component.author:
            author_label = QLabel(f"{self._t('Автор', 'Author')}: {component.author}")
            author_label.setProperty("class", "muted")
            layout.addWidget(author_label)

        if component_id == "backend":
            pass
        elif component_id == "tg-ws-proxy":
            connect_btn = QPushButton(self._t("Подключить к Telegram", "Connect to Telegram"))
            connect_btn.clicked.connect(self.context.processes.prompt_telegram_proxy_link)
            layout.addWidget(connect_btn)
        elif component_id == "traffic-engine":
            settings = self.context.settings.get()
            engine_label = QLabel(self._t("Движок обхода", "Traffic engine"))
            engine_label.setProperty("class", "muted")
            layout.addWidget(engine_label)

            engine_combo = AdaptiveComboBox()
            selected_engine = settings.traffic_engine_id if settings.traffic_engine_id in {"zapret", "spoofdpi"} else "zapret"
            other_engine = "spoofdpi" if selected_engine == "zapret" else "zapret"
            labels = {"zapret": "ByeDPI", "spoofdpi": "SpoofDPI"}
            engine_combo.addItem(labels[selected_engine], selected_engine)
            engine_combo.addItem(labels[other_engine], other_engine)
            engine_combo.setCurrentIndex(0)
            engine_combo.apply_theme(self.context.settings.detect_effective_theme())
            engine_combo.activated.connect(lambda _=0, box=engine_combo: self._select_traffic_engine(box.currentData()))
            layout.addWidget(engine_combo)

            if settings.traffic_engine_id == "zapret":
                info_text = f"SOCKS5: {settings.zapret_host}:{settings.zapret_port}"
            else:
                info_text = f"HTTP: {settings.spoofdpi_host}:{settings.spoofdpi_port}"
            info = QLabel(f"{self._t('Точка подключения', 'Endpoint')}: {info_text}")
            info.setProperty("class", "muted")
            layout.addWidget(info)

        if state and state.last_error:
            error = QLabel(state.last_error)
            error.setWordWrap(True)
            error.setProperty("class", "muted")
            layout.addWidget(error)

        layout.addStretch(1)
        if component and component.can_toggle:
            action_btn = QPushButton(self._t("Выключить", "Disable") if component.enabled else self._t("Включить", "Enable"))
            action_btn.setProperty("class", "danger" if component.enabled else "primary")
            action_btn.clicked.connect(lambda _=False, cid=component_id: self._toggle_component_enabled(cid))
            layout.addWidget(action_btn)
        return card

    def _build_logs_page(self) -> QWidget:
        page = QWidget()
        page.setProperty("class", "pageRoot")
        root = QVBoxLayout(page)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel(self._t("Логи", "Logs"))
        title.setProperty("class", "title")
        top.addWidget(title)
        self.logs_source_combo = QComboBox()
        self.logs_source_combo.addItem(self._t("Приложение", "Application"), "app")
        self.logs_source_combo.addItem(self._t("Локальный backend", "Backend"), "backend")
        self.logs_source_combo.addItem("TG WS Proxy", "tg")
        self.logs_source_combo.addItem("SpoofDPI", "spoofdpi")
        self.logs_source_combo.addItem("ByeDPI", "zapret")
        self.logs_source_combo.currentIndexChanged.connect(self._reset_logs_view)
        top.addWidget(self.logs_source_combo)
        top.addStretch(1)
        refresh = QPushButton(self._t("Обновить", "Refresh"))
        refresh.clicked.connect(self._reset_logs_view)
        top.addWidget(refresh)
        root.addLayout(top)

        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        root.addWidget(self.logs_text, 1)
        return page

    def refresh_all(self) -> None:
        self._refresh_dashboard()
        self._refresh_components()
        self._refresh_logs()
        self._sync_nav_highlight(animated=False)

    def refresh_passive(self) -> None:
        self._refresh_dashboard()
        self._refresh_logs()
        self._sync_nav_highlight(animated=False)

    def _refresh_dashboard(self) -> None:
        states = {state.component_id: state for state in self.context.processes.list_states()}
        any_running = any(state.status == "running" for state in states.values())
        any_busy = any(state.status in {"starting", "stopping"} for state in states.values())
        busy_is_connecting = self._power_target_running if self._power_target_running is not None else (not any_running)

        if any_running and not self._power_running:
            if self._pending_click_wave == "on":
                self._pending_click_wave = None
            else:
                self.power_aura.play_activation_wave()
        elif not any_running and self._power_running:
            if self._pending_click_wave == "off":
                self._pending_click_wave = None
            else:
                self.power_aura.play_shutdown_wave()

        self.power_aura.set_idle_pulse_enabled(any_running and not any_busy)

        self._power_running = any_running
        self.power_button.set_active_state(any_running, animate=True)
        self.power_button.set_loading_state(any_busy, animate=True)
        self.power_button.setEnabled(not any_busy)
        if any_busy:
            busy_base = self._t("Подключение", "Connecting") if busy_is_connecting else self._t("Отключение", "Disconnecting")
            self._start_power_caption_busy(busy_base)
        else:
            self._stop_power_caption_busy()
            caption = "ВКЛ" if any_running else "ВЫКЛ"
            self._power_target_running = None
            self.power_caption.setText(caption)

        effective_theme = self.context.settings.detect_effective_theme()
        if any_busy:
            self._status_labels["app"].setText(self._t("Подключение", "Connecting") if busy_is_connecting else self._t("Отключение", "Disconnecting"))
        else:
            self._status_labels["app"].setText(self._t("Работает", "Working") if any_running else self._t("Остановлено", "Stopped"))
        proxy_state = states.get("backend")
        proxy_status = self._localize_state(proxy_state.status if proxy_state else "unknown")
        self._status_labels["proxy"].setText(proxy_status)
        tg_state = states.get("tg-ws-proxy")
        self._status_labels["tg"].setText(self._localize_state(tg_state.status if tg_state else "unknown"))
        engine_name = "ByeDPI" if self.context.settings.get().traffic_engine_id == "zapret" else "SpoofDPI"
        if "engine" in self._status_title_labels:
            self._status_title_labels["engine"].setText(engine_name)
        engine_state = states.get("traffic-engine")
        engine_status = self._localize_state(engine_state.status if engine_state else "unknown")
        self._status_labels["engine"].setText(engine_status)
        if effective_theme == "oled":
            self._status_labels["theme"].setText(self._t("Тёмная", "Dark"))
        elif effective_theme == "light":
            self._status_labels["theme"].setText(self._t("Светлая", "Light"))
        else:
            self._status_labels["theme"].setText(self._t("Системная", "System"))
        self._sync_power_icon(effective_theme, any_running=any_running, any_busy=any_busy)

    def _refresh_components(self) -> None:
        while self.components_cards_layout.count():
            item = self.components_cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.components_cards_layout.addWidget(
            self._build_component_card(
                "traffic-engine",
                self._t("Движок обхода", "Traffic Engine"),
                self._t("Встроенный движок обхода DPI для локального web-трафика. Можно выбрать SpoofDPI или ByeDPI.", "Selectable bundled DPI bypass engine for local web traffic. Choose SpoofDPI or ByeDPI."),
                "tool.svg",
            ),
            0,
            0,
        )
        self.components_cards_layout.addWidget(
            self._build_component_card(
                "backend",
                "PulseRoute Engine",
                self._t(
                    "Автоматически запускается вместе с выбранным движком обхода и проксирует TCP и UDP трафик в macOS. UDP может не работать в некоторых программах, которые это не поддерживают.",
                    "Automatically starts with the selected traffic engine and proxies both TCP and UDP traffic in macOS. UDP may not work in some apps that do not support it.",
                ),
                "component_zapret.svg",
            ),
            1,
            0,
        )
        self.components_cards_layout.addWidget(
            self._build_component_card(
                "tg-ws-proxy",
                "TG WS Proxy",
                self._t("Встроенный Telegram bridge proxy с локальным контролем состояния и жизненного цикла.", "Telegram bridge proxy bundled for the macOS runtime with local health and lifecycle control."),
                "component_tg.svg",
            ),
            0,
            1,
        )

    def _refresh_logs(self) -> None:
        source_id = str(self.logs_source_combo.currentData()) if hasattr(self, "logs_source_combo") else "app"
        path = self._log_path_for_source(source_id)
        offset = self._log_offsets.get(source_id, 0)
        if not path.exists():
            if offset == 0:
                return
            self._log_offsets[source_id] = 0
            self.logs_text.clear()
            return
        raw = path.read_bytes()
        if offset > len(raw):
            offset = 0
            self.logs_text.clear()
        chunk = raw[offset:]
        if not chunk:
            return
        scrollbar = self.logs_text.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 4
        cursor = self.logs_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk.decode("utf-8", errors="ignore"))
        self.logs_text.setTextCursor(cursor)
        self._log_offsets[source_id] = len(raw)
        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def _reset_logs_view(self) -> None:
        source_id = str(self.logs_source_combo.currentData()) if hasattr(self, "logs_source_combo") else "app"
        self._log_offsets[source_id] = 0
        self.logs_text.clear()
        self._refresh_logs()

    def _log_path_for_source(self, source_id: str) -> Path:
        mapping = {
            "app": self.context.logging.path,
            "backend": self.context.paths.logs_dir / "backend.log",
            "tg": self.context.paths.logs_dir / "tg-ws-proxy.log",
            "spoofdpi": self.context.paths.logs_dir / "spoofdpi.log",
            "zapret": self.context.paths.logs_dir / "zapret-macos.log",
        }
        return mapping.get(source_id, self.context.logging.path)

    def _apply_theme(self) -> None:
        theme = self.context.settings.detect_effective_theme()
        self.setStyleSheet(
            build_stylesheet(
                theme,
                chevron_icon=str(self._icon_path("chevron_down.svg")),
                check_icon=str(self._icon_path("check.svg")),
                close_icon=str(self._icon_path("window_close_dark.svg")),
                min_icon=str(self._icon_path("window_min_dark.svg")),
            )
        )
        self.sidebar_panel.set_theme(theme)
        for btn in self._nav_buttons:
            if isinstance(btn, AnimatedNavButton):
                btn.set_nav_theme(theme)
        for combo in self.findChildren(AdaptiveComboBox):
            combo.apply_theme(theme)
        self.power_button.set_power_theme(theme)
        self.power_aura.set_power_theme(theme)

    def _set_theme(self, theme_id: str) -> None:
        self.context.settings.update(theme=theme_id)
        self._apply_theme()
        self.refresh_all()

    def _rebuild_translated_ui(self) -> None:
        current_page = self.pages.currentIndex() if hasattr(self, "pages") else 0
        old_central = self.takeCentralWidget()
        if old_central is not None:
            old_central.deleteLater()
        self.menuBar().clear()
        self._nav_buttons = []
        self._status_labels = {}
        self._status_title_labels = {}
        self._component_cards = {}
        self._traffic_buttons = []
        self._traffic_hover_cluster = None
        self._nav_items = [
            NavItem("dashboard", "home.svg", self._t("Главная", "Home")),
            NavItem("components", "components.svg", self._t("Компоненты", "Components")),
            NavItem("logs", "logs.svg", self._t("Логи", "Logs")),
        ]
        self._build_menu()
        self._build_ui()
        if hasattr(self, "pages"):
            page_index = max(0, min(current_page, self.pages.count() - 1))
            self.pages.setCurrentIndex(page_index)
            for i, btn in enumerate(self._nav_buttons):
                btn.setChecked(i == page_index)
        self._apply_theme()
        self.refresh_all()
        if callable(self._tray_menu_updater):
            self._tray_menu_updater()

    def _open_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.context.settings.get(), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        previous = asdict(self.context.settings.get())
        changes = dialog.values()
        self.context.settings.update(**changes)
        current = self.context.settings.get()
        self.context.autostart.set_enabled(current.launch_at_login)

        language_changed = previous.get("language") != current.language
        theme_changed = previous.get("theme") != current.theme
        runtime_keys = {
            "tg_proxy_host",
            "tg_proxy_port",
            "tg_proxy_secret",
            "spoofdpi_host",
            "spoofdpi_port",
            "spoofdpi_args",
            "zapret_host",
            "zapret_port",
            "zapret_args",
            "backend_profile_id",
            "traffic_engine_id",
            "enabled_component_ids",
            "autostart_component_ids",
        }
        runtime_changed = any(previous.get(key) != getattr(current, key) for key in runtime_keys)

        if language_changed:
            self._rebuild_translated_ui()
        else:
            if theme_changed:
                self._apply_theme()
            self.refresh_all()
            if callable(self._tray_menu_updater):
                self._tray_menu_updater()

        if runtime_changed:
            self._rebuild_runtime()

    def prompt_update_available(self, tag_name: str, release_name: str, release_url: str) -> None:
        release_title = release_name.strip() or tag_name.strip()
        message = QMessageBox(self)
        message.setIcon(QMessageBox.Icon.Information)
        message.setWindowTitle(self._t("Доступно обновление", "Update available"))
        message.setText(self._t("Найдена новая версия Zapret Hub.", "A new Zapret Hub version is available."))
        message.setInformativeText(
            self._t(
                f"Текущая версия: {__version__}\n"
                f"Новая версия: {release_title}\n"
                f"Открыть страницу релиза?",
                f"Current version: {__version__}\n"
                f"New version: {release_title}\n"
                f"Open release page?",
            )
        )
        open_button = message.addButton(self._t("Перейти к релизу", "Open release"), QMessageBox.ButtonRole.AcceptRole)
        message.addButton(self._t("Позже", "Later"), QMessageBox.ButtonRole.RejectRole)
        message.exec()
        if message.clickedButton() is open_button and release_url:
            QDesktopServices.openUrl(QUrl(release_url))

    def _toggle_master(self) -> None:
        states = self.context.processes.list_states()
        if any(state.status in {"starting", "stopping"} for state in states):
            return
        running = any(state.status == "running" for state in states)
        if running:
            self._pending_click_wave = "off"
            self.power_aura.set_idle_pulse_enabled(False)
            self.power_aura.stop_wave_immediately()
            self.power_aura.play_shutdown_wave()
            self.power_button.set_loading_state(True)
            self._power_target_running = False
            self.context.processes.stop_all()
        else:
            self._pending_click_wave = "on"
            self.power_aura.stop_wave_immediately()
            self.power_aura.play_activation_wave()
            self.power_button.set_loading_state(True)
            self._power_target_running = True
            self._run_after_runtime(self.context.processes.start_enabled_components)

    def _start_enabled(self) -> None:
        self.power_button.set_loading_state(True)
        self._power_target_running = True
        self._run_after_runtime(self.context.processes.start_enabled_components)

    def _stop_all(self) -> None:
        self.power_button.set_loading_state(True)
        self._power_target_running = False
        self.context.processes.stop_all()

    def _component_action(self, component_id: str, running: bool) -> None:
        if running:
            if component_id in {"backend", "traffic-engine"}:
                self.power_aura.play_shutdown_wave()
                self.context.processes.stop_component("backend")
            else:
                self.context.processes.stop_component(component_id)
            return
        if component_id in {"backend", "traffic-engine"}:
            self.power_aura.play_activation_wave()
            self._power_target_running = True
            self._run_after_runtime(lambda: self.context.processes.start_component("backend"))
        else:
            self.context.processes.start_component(component_id)

    def _toggle_component_enabled(self, component_id: str) -> None:
        self.context.processes.toggle_component_enabled(component_id)
        self.refresh_all()

    def _select_traffic_engine(self, engine_id: str | None) -> None:
        if not engine_id:
            return
        future = self.context.processes.set_traffic_engine_async(str(engine_id))

        def on_done(done) -> None:
            try:
                done.result()
            except Exception as exc:
                self._bridge.runtime_failed.emit(str(exc))
                return
            self._bridge.refresh_requested.emit()

        future.add_done_callback(on_done)
        self.refresh_all()

    def _select_profile(self, profile_id: str | None) -> None:
        if not profile_id:
            return
        self.context.settings.update(backend_profile_id=str(profile_id))
        self._rebuild_runtime()

    def _rebuild_runtime(self) -> None:
        self._run_after_runtime(lambda: None)

    def _run_after_runtime(self, callback: Callable[[], object]) -> None:
        future = self.context.processes.rebuild_runtime()

        def on_done(done) -> None:
            try:
                done.result()
            except Exception as exc:
                self._bridge.runtime_failed.emit(str(exc))
                return
            callback()
            self._bridge.refresh_requested.emit()

        future.add_done_callback(on_done)

    def _show_runtime_error(self, message: str) -> None:
        QMessageBox.warning(self, "Runtime", message)

    def _switch_page(self, index: int) -> None:
        if index == self.pages.currentIndex():
            self._sync_nav_highlight(animated=True)
            return
        if index == 1:
            self._refresh_components()
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == index)
        self._animate_page_switch(index)
        self._sync_nav_highlight(animated=True)

    def _animate_page_switch(self, index: int) -> None:
        if self._page_transition is not None:
            self._page_transition.stop()
        fade_out = QPropertyAnimation(self._page_opacity_effect, b"opacity", self)
        fade_out.setDuration(90)
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QEasingCurve.Type.InOutCubic)

        def on_faded() -> None:
            self.pages.setCurrentIndex(index)
            fade_in = QPropertyAnimation(self._page_opacity_effect, b"opacity", self)
            fade_in.setDuration(190)
            fade_in.setStartValue(0.0)
            fade_in.setEndValue(1.0)
            fade_in.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self._page_transition = fade_in
            fade_in.start()

        fade_out.finished.connect(on_faded)
        self._page_transition = fade_out
        fade_out.start()

    def _sync_nav_highlight(self, *, animated: bool) -> None:
        for btn in self._nav_buttons:
            if btn.isChecked():
                self.sidebar_panel.move_highlight(btn.geometry(), animated=animated)
                break

    def _sync_power_aura_geometry(self) -> None:
        stage = getattr(self, "_power_stage", None)
        if stage is None:
            return
        host = self.power_aura.parentWidget()
        if host is None:
            return
        self.power_aura.setGeometry(host.rect())
        top_left = stage.mapTo(host, QPoint(0, 0))
        center = QPointF(float(top_left.x()) + stage.width() / 2.0, float(top_left.y()) + 94.0)
        self.power_aura.set_center_point(center)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if watched is getattr(self, "_traffic_hover_cluster", None) or watched in getattr(self, "_traffic_buttons", []):
            if event.type() in {QEvent.Type.Enter, QEvent.Type.HoverEnter}:
                self._set_traffic_symbols_visible(True)
            elif event.type() in {QEvent.Type.Leave, QEvent.Type.HoverLeave}:
                self._set_traffic_symbols_visible(False)
        if watched in {getattr(self, "_drag_surface", None), self.findChild(QFrame, "TitleBar")}:
            if event.type() == QEvent.Type.MouseButtonPress and isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
                self._drag_active = True
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if event.type() == QEvent.Type.MouseMove and isinstance(event, QMouseEvent) and self._drag_active and self._drag_pos is not None:
                if event.buttons() & Qt.MouseButton.LeftButton:
                    self.move(event.globalPosition().toPoint() - self._drag_pos)
                    return True
            if event.type() == QEvent.Type.MouseButtonRelease:
                self._drag_active = False
                self._drag_pos = None
                return True
        return super().eventFilter(watched, event)

    def _set_traffic_symbols_visible(self, visible: bool) -> None:
        for button in self._traffic_buttons:
            if button.property("showSymbol") == visible:
                continue
            button.setProperty("showSymbol", visible)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._sync_power_aura_geometry()
        self._sync_nav_highlight(animated=False)

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._force_quit and self.context.processes.any_bypass_running():
            if self.hide_to_tray():
                event.ignore()
                return
            self.context.logging.log("error", "Tray transition failed; keeping window open to avoid dropping active bypass stack")
            event.ignore()
            return
        self._force_quit = True
        if self._tray_icon is not None:
            self._tray_icon.hide()
        event.accept()
        app = QApplication.instance()
        if app is not None:
            QTimer.singleShot(0, app.quit)
        super().closeEvent(event)

    def _localize_state(self, status: str) -> str:
        normalized = (status or "").strip().lower()
        language = self.context.settings.get().language
        ru = {
            "running": "Работает",
            "stopped": "Остановлено",
            "starting": "Подключение",
            "stopping": "Отключение",
            "error": "Ошибка",
            "unknown": "Неизвестно",
        }
        en = {
            "running": "Working",
            "stopped": "Stopped",
            "starting": "Connecting",
            "stopping": "Disconnecting",
            "error": "Error",
            "unknown": "Unknown",
        }
        mapping = ru if language == "ru" else en
        return mapping.get(normalized, mapping["unknown"])

    def _start_power_caption_busy(self, base_text: str) -> None:
        if self._power_caption_base != base_text:
            self._power_caption_base = base_text
            self._power_caption_dots_phase = 0
        if not self._power_caption_timer.isActive():
            self._power_caption_timer.start()
        self._advance_power_caption_dots()

    def _stop_power_caption_busy(self) -> None:
        self._power_caption_timer.stop()
        self._power_caption_base = ""
        self._power_caption_dots_phase = 0

    def _advance_power_caption_dots(self) -> None:
        if not self._power_caption_base:
            return
        sequence = (0, 1, 2, 3, 2, 1)
        dots = sequence[self._power_caption_dots_phase % len(sequence)]
        self._power_caption_dots_phase += 1
        self.power_caption.setText(f"{self._power_caption_base}{'.' * dots}")

    def _sync_power_icon(self, effective_theme: str, *, any_running: bool, any_busy: bool) -> None:
        if effective_theme == "light" and (not any_running and not any_busy):
            icon_name = "power_dark.svg"
        else:
            icon_name = "power.svg"
        self.power_button.setIcon(self._icon(icon_name))

    def _icon(self, name: str) -> QIcon:
        return QIcon(str(self._icon_path(name)))

    def _icon_path(self, name: str) -> Path:
        return self.context.paths.resources_dir / "ui_assets" / "icons" / name

    def set_tray_icon(self, tray_icon) -> None:
        self._tray_icon = tray_icon

    def set_tray_menu_updater(self, updater: Callable[[], None]) -> None:
        self._tray_menu_updater = updater

    def set_tray_initializer(self, initializer: Callable[[], object]) -> None:
        self._tray_initializer = initializer

    def set_activation_policy_handlers(self, activate_regular: Callable[[], None], activate_accessory: Callable[[], None]) -> None:
        self._activate_regular = activate_regular
        self._activate_accessory = activate_accessory

    def hide_to_tray(self) -> bool:
        if self._tray_icon is None and callable(self._tray_initializer):
            try:
                self._tray_icon = self._tray_initializer()
            except Exception as exc:
                self.context.logging.log("error", "Failed to initialize native status item", error=str(exc))
                self._bridge.runtime_failed.emit(str(exc))
                self._tray_icon = None
                return False
        if self._tray_icon is None:
            self.context.logging.log("error", "Native status item is unavailable; cannot hide to tray")
            return False
        if self._tray_icon is not None:
            try:
                self._tray_icon.refresh_labels()
            except Exception as exc:
                self.context.logging.log("warning", "Failed to refresh tray labels", error=str(exc))
            try:
                self._tray_icon.show()
            except Exception as exc:
                self.context.logging.log("error", "Failed to show native status item", error=str(exc))
                self._bridge.runtime_failed.emit(str(exc))
                return False
        if callable(self._activate_accessory):
            self._activate_accessory()
        self.hide()
        return True

    def show_from_tray(self) -> None:
        if self._tray_icon is not None:
            self._tray_icon.hide()
        if callable(self._activate_regular):
            self._activate_regular()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def on_tray_activated(self, reason) -> None:
        from PySide6.QtWidgets import QSystemTrayIcon
        if reason in {QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick}:
            self.show_from_tray()

    def quit_application(self) -> None:
        self._force_quit = True
        if self._tray_icon is not None:
            self._tray_icon.hide()
        self.close()
