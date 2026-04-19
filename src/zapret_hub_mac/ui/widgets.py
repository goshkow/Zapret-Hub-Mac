from __future__ import annotations

from PySide6.QtCore import QEasingCurve, QEvent, QPointF, Property, QRect, QRectF, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPen, QPixmap, QRadialGradient
from PySide6.QtWidgets import QFrame, QLayout, QToolButton, QWidget, QWidgetItem

from zapret_hub_mac.ui.theme import is_light_theme


class SidebarPanel(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._border_color = QColor("#24304a")
        self._highlight_rect = QRect()
        self._highlight_fill = QColor(79, 115, 179, 68)
        self._highlight_border = QColor("#4f73b3")
        self._highlight_animation: QPropertyAnimation | None = None

    def set_theme(self, theme: str) -> None:
        if is_light_theme(theme):
            self._border_color = QColor("#d2ddeb")
            self._highlight_fill = QColor(191, 211, 243, 118)
            self._highlight_border = QColor("#9cb7ea")
        else:
            self._border_color = QColor("#24304a")
            self._highlight_fill = QColor(79, 115, 179, 68)
            self._highlight_border = QColor("#4f73b3")
        self.update()

    def paintEvent(self, event: QEvent) -> None:
        super().paintEvent(event)
        if self._highlight_rect.isNull():
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(self._highlight_border, 1))
        painter.setBrush(self._highlight_fill)
        painter.drawRoundedRect(QRectF(self._highlight_rect), 12, 12)

    def _get_highlight_rect(self) -> QRect:
        return QRect(self._highlight_rect)

    def _set_highlight_rect(self, rect: QRect) -> None:
        self._highlight_rect = QRect(rect)
        self.update()

    highlightRect = Property(QRect, _get_highlight_rect, _set_highlight_rect)

    def move_highlight(self, rect: QRect, *, animated: bool = True) -> None:
        target = QRect(rect)
        if target.isNull():
            return
        if self._highlight_animation is not None:
            self._highlight_animation.stop()
        if not animated or self._highlight_rect.isNull():
            self._highlight_rect = target
            self.update()
            return
        animation = QPropertyAnimation(self, b"highlightRect", self)
        animation.setDuration(260)
        animation.setStartValue(self._highlight_rect)
        animation.setEndValue(target)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        animation.start()
        self._highlight_animation = animation


class AnimatedNavButton(QToolButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hover_progress = 0.0
        self._icon_dx = 0.0
        self._icon_dy = 0.0
        self._icon_scale = 1.0
        self._glow_pos = QPointF(22.0, 22.0)
        self._light_theme = False
        self._anims: list[QPropertyAnimation] = []

    def set_nav_theme(self, theme: str) -> None:
        self._light_theme = is_light_theme(theme)
        self.update()

    def _animate_property(self, name: bytes, start: float, end: float, duration: int) -> None:
        animation = QPropertyAnimation(self, name, self)
        animation.setStartValue(start)
        animation.setEndValue(end)
        animation.setDuration(duration)
        animation.setEasingCurve(QEasingCurve.Type.InOutCubic)
        animation.finished.connect(lambda: self._anims.remove(animation) if animation in self._anims else None)
        self._anims.append(animation)
        animation.start()

    def enterEvent(self, event: QEvent) -> None:
        self._animate_property(b"hoverProgress", self._hover_progress, 1.0, 220)
        self._animate_property(b"iconScale", self._icon_scale, 1.035, 240)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._animate_property(b"hoverProgress", self._hover_progress, 0.0, 220)
        self._animate_property(b"iconScale", self._icon_scale, 1.0, 220)
        self._animate_property(b"iconDx", self._icon_dx, 0.0, 180)
        self._animate_property(b"iconDy", self._icon_dy, 0.0, 180)
        super().leaveEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        self._glow_pos = QPointF(pos.x(), pos.y())
        center = QPointF(self.width() / 2.0, self.height() / 2.0)
        dx = max(-1.0, min(1.0, (pos.x() - center.x()) / max(8.0, center.x())))
        dy = max(-1.0, min(1.0, (pos.y() - center.y()) / max(8.0, center.y())))
        self._icon_dx += (dx * 1.1 - self._icon_dx) * 0.18
        self._icon_dy += (dy * 1.1 - self._icon_dy) * 0.18
        self.update()
        super().mouseMoveEvent(event)

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        rect = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        radius = 12.0
        checked = self.isChecked()

        if self._light_theme:
            base_fill = QColor(181, 204, 242, 10)
            hover_fill = QColor(194, 214, 245, int(30 * self._hover_progress))
            border = QColor(191, 210, 240, int(88 * self._hover_progress))
            glow_color = QColor(255, 255, 255, int(44 * self._hover_progress))
        else:
            base_fill = QColor(90, 112, 152, 8)
            hover_fill = QColor(95, 124, 177, int(26 * self._hover_progress))
            border = QColor(102, 132, 191, int(84 * self._hover_progress))
            glow_color = QColor(126, 164, 255, int(58 * self._hover_progress))

        fill = QColor(0, 0, 0, 0) if checked else base_fill
        if not checked and self._hover_progress > 0:
            fill = hover_fill
        painter.setPen(QPen(border if (border.alpha() > 0 and not checked) else QColor(0, 0, 0, 0), 1))
        painter.setBrush(fill)
        painter.drawRoundedRect(rect, radius, radius)

        if self._hover_progress > 0:
            glow = QRadialGradient(self._glow_pos, max(self.width(), self.height()) * 0.75)
            glow.setColorAt(0.0, glow_color)
            glow.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawRoundedRect(rect, radius, radius)

        icon_size = max(20, round(26 * self._icon_scale))
        pixmap = self.icon().pixmap(icon_size, icon_size)
        target = QRectF(
            (self.width() - icon_size) / 2.0 + self._icon_dx,
            (self.height() - icon_size) / 2.0 + self._icon_dy,
            icon_size,
            icon_size,
        )
        painter.drawPixmap(target, pixmap, QRectF(0, 0, pixmap.width(), pixmap.height()))

    def _get_hover_progress(self) -> float:
        return self._hover_progress

    def _set_hover_progress(self, value: float) -> None:
        self._hover_progress = float(value)
        self.update()

    def _get_icon_dx(self) -> float:
        return self._icon_dx

    def _set_icon_dx(self, value: float) -> None:
        self._icon_dx = float(value)
        self.update()

    def _get_icon_dy(self) -> float:
        return self._icon_dy

    def _set_icon_dy(self, value: float) -> None:
        self._icon_dy = float(value)
        self.update()

    def _get_icon_scale(self) -> float:
        return self._icon_scale

    def _set_icon_scale(self, value: float) -> None:
        self._icon_scale = float(value)
        self.update()

    hoverProgress = Property(float, _get_hover_progress, _set_hover_progress)
    iconDx = Property(float, _get_icon_dx, _set_icon_dx)
    iconDy = Property(float, _get_icon_dy, _set_icon_dy)
    iconScale = Property(float, _get_icon_scale, _set_icon_scale)


class AnimatedPowerButton(QToolButton):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._light_theme = False
        self._active = False
        self._visual_mode = "off"
        self._visual_scale = 1.0
        self._hover_progress = 0.0
        self._glow_pos = QPointF(66.0, 66.0)
        self._scale_anim: QPropertyAnimation | None = None
        self._hover_anim: QPropertyAnimation | None = None

    def set_power_theme(self, theme: str) -> None:
        self._light_theme = is_light_theme(theme)
        self.update()

    def set_active_state(self, active: bool, *, animate: bool = True) -> None:
        self._active = active
        self._visual_mode = "on" if active else "off"
        target = 1.14 if active else 1.0
        self._animate_scale(target, animate, 220)

    def set_loading_state(self, loading: bool, *, animate: bool = True) -> None:
        self._visual_mode = "loading" if loading else ("on" if self._active else "off")
        target = 1.06 if loading else (1.14 if self._active else 1.0)
        self._animate_scale(target, animate, 190)

    def _animate_scale(self, target: float, animate: bool, duration: int) -> None:
        if self._scale_anim is not None:
            self._scale_anim.stop()
        if not animate:
            self._visual_scale = target
            self.update()
            return
        anim = QPropertyAnimation(self, b"visualScale", self)
        anim.setDuration(duration)
        anim.setStartValue(self._visual_scale)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.start()
        self._scale_anim = anim

    def enterEvent(self, event: QEvent) -> None:
        self._animate_hover(1.0)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._animate_hover(0.0)
        super().leaveEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        self._glow_pos = event.position()
        self.update()
        super().mouseMoveEvent(event)

    def _animate_hover(self, target: float) -> None:
        if self._hover_anim is not None:
            self._hover_anim.stop()
        anim = QPropertyAnimation(self, b"hoverProgress", self)
        anim.setDuration(240)
        anim.setStartValue(self._hover_progress)
        anim.setEndValue(target)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        anim.start()
        self._hover_anim = anim

    def paintEvent(self, event: QEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        rect = QRectF(self.rect())
        center = rect.center()
        base_radius = min(rect.width(), rect.height()) * 0.39
        radius = base_radius * self._visual_scale

        if self._light_theme:
            off_top = QColor("#f7f9ff")
            off_bottom = QColor("#dfe8f7")
            off_border = QColor("#bfd2f0")
            on_top = QColor("#7b86ff")
            on_bottom = QColor("#4c58d8")
            on_border = QColor("#7b87ff")
            loading_top = QColor("#c7d3e6")
            loading_bottom = QColor("#9ba8bd")
            loading_border = QColor("#b9c6db")
        else:
            off_top = QColor("#3a3e44")
            off_bottom = QColor("#282c31")
            off_border = QColor("#4b5058")
            on_top = QColor("#7380ff")
            on_bottom = QColor("#4551cb")
            on_border = QColor("#7b87ff")
            loading_top = QColor("#707785")
            loading_bottom = QColor("#565d69")
            loading_border = QColor("#8b94a3")

        gradient = QRadialGradient(center.x(), center.y() - radius * 0.36, radius * 1.3)
        if self._visual_mode == "loading":
            gradient.setColorAt(0.0, loading_top)
            gradient.setColorAt(1.0, loading_bottom)
            border = loading_border
        elif self._active:
            gradient.setColorAt(0.0, on_top)
            gradient.setColorAt(1.0, on_bottom)
            border = on_border
        else:
            gradient.setColorAt(0.0, off_top)
            gradient.setColorAt(1.0, off_bottom)
            border = off_border
        painter.setPen(QPen(border, 2))
        painter.setBrush(gradient)
        painter.drawEllipse(center, radius, radius)

        if self._hover_progress > 0.001:
            glow_color = QColor(148, 206, 255, int(34 * self._hover_progress))
            dx = self._glow_pos.x() - center.x()
            dy = self._glow_pos.y() - center.y()
            distance = max(1.0, (dx * dx + dy * dy) ** 0.5)
            max_offset = radius * 0.34
            focus = QPointF(
                center.x() + dx / distance * min(distance, max_offset),
                center.y() + dy / distance * min(distance, max_offset),
            )
            button_path = QPainterPath()
            button_path.addEllipse(center, radius, radius)
            painter.save()
            painter.setClipPath(button_path)
            glow = QRadialGradient(focus, radius * 0.98)
            glow.setColorAt(0.0, glow_color)
            glow.setColorAt(0.65, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), max(0, glow_color.alpha() // 2)))
            glow.setColorAt(1.0, QColor(glow_color.red(), glow_color.green(), glow_color.blue(), 0))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(glow)
            painter.drawEllipse(center, radius, radius)
            painter.restore()

        icon_size = 48 if self._active else 44
        if self._visual_mode == "loading":
            icon_size = 46
        pixmap = self.icon().pixmap(icon_size, icon_size)
        target = QRectF(center.x() - icon_size / 2.0, center.y() - icon_size / 2.0, icon_size, icon_size)
        painter.drawPixmap(target, pixmap, QRectF(0, 0, pixmap.width(), pixmap.height()))

    def _get_visual_scale(self) -> float:
        return self._visual_scale

    def _set_visual_scale(self, value: float) -> None:
        self._visual_scale = float(value)
        self.update()

    def _get_hover_progress(self) -> float:
        return self._hover_progress

    def _set_hover_progress(self, value: float) -> None:
        self._hover_progress = float(value)
        self.update()

    visualScale = Property(float, _get_visual_scale, _set_visual_scale)
    hoverProgress = Property(float, _get_hover_progress, _set_hover_progress)


class PowerAuraWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self._light_theme = False
        self._wave_progress = 0.0
        self._wave_strength = 0.0
        self._wave_direction = 1.0
        self._center_point = QPointF()
        self._wave_base_radius = 62.0
        self._wave_travel_radius = 62.0
        self._idle_pulse_timer = QTimer(self)
        self._idle_pulse_timer.setInterval(1480)
        self._idle_pulse_timer.timeout.connect(self._play_idle_pulse)
        self._wave_progress_anim: QPropertyAnimation | None = None
        self._wave_strength_anim: QPropertyAnimation | None = None

    def set_power_theme(self, theme: str) -> None:
        self._light_theme = is_light_theme(theme)
        self.update()

    def set_center_point(self, point: QPointF) -> None:
        self._center_point = QPointF(point)
        self.update()

    def set_idle_pulse_enabled(self, enabled: bool) -> None:
        if enabled:
            if not self._idle_pulse_timer.isActive():
                self._idle_pulse_timer.start()
        else:
            self._idle_pulse_timer.stop()
            if self._wave_strength <= 0.30:
                self._wave_strength = 0.0
                self._wave_progress = 0.0
                self.update()

    def _play_idle_pulse(self) -> None:
        self._play_wave_internal(strength=0.24, duration=1450, base_radius=62.0, travel_radius=54.0, direction=1.0)

    def play_wave(self) -> None:
        self.play_activation_wave()

    def play_activation_wave(self) -> None:
        self._play_wave_internal(strength=0.48, duration=820, base_radius=74.0, travel_radius=118.0, direction=1.0)

    def play_shutdown_wave(self) -> None:
        self._play_wave_internal(strength=0.40, duration=720, base_radius=148.0, travel_radius=84.0, direction=-1.0)

    def _play_wave_internal(
        self,
        *,
        strength: float,
        duration: int,
        base_radius: float,
        travel_radius: float,
        direction: float,
    ) -> None:
        if self._wave_progress_anim is not None:
            self._wave_progress_anim.stop()
        if self._wave_strength_anim is not None:
            self._wave_strength_anim.stop()
        self._wave_progress = 0.0
        self._wave_strength = strength
        self._wave_direction = direction
        self._wave_base_radius = base_radius
        self._wave_travel_radius = travel_radius
        prog = QPropertyAnimation(self, b"waveProgress", self)
        prog.setDuration(duration)
        prog.setStartValue(0.0)
        prog.setEndValue(1.0)
        prog.setEasingCurve(QEasingCurve.Type.OutCubic)
        fade = QPropertyAnimation(self, b"waveStrength", self)
        fade.setDuration(duration)
        fade.setStartValue(strength)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.OutCubic)
        prog.start()
        fade.start()
        self._wave_progress_anim = prog
        self._wave_strength_anim = fade

    def stop_wave_immediately(self) -> None:
        if self._wave_progress_anim is not None:
            self._wave_progress_anim.stop()
        if self._wave_strength_anim is not None:
            self._wave_strength_anim.stop()
        self._wave_progress = 0.0
        self._wave_strength = 0.0
        self.update()

    def paintEvent(self, event: QEvent) -> None:
        if self._wave_strength <= 0.001:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        clip = QPainterPath()
        clip.addRoundedRect(QRectF(self.rect()).adjusted(2.0, 2.0, -2.0, -2.0), 18.0, 18.0)
        painter.setClipPath(clip)
        center = self._center_point if not self._center_point.isNull() else QRectF(self.rect()).center()
        color = QColor(64, 116, 255, int(176 * self._wave_strength)) if self._light_theme else QColor(122, 214, 255, int(168 * self._wave_strength))
        base = self._wave_base_radius
        travel = self._wave_travel_radius * self._wave_progress
        for factor, width, alpha_factor in ((1.0, 14.0, 1.0), (0.8, 9.0, 0.78), (0.62, 5.5, 0.52)):
            if self._wave_direction >= 0:
                radius = base * factor + travel
            else:
                radius = max(24.0, base * factor - travel)
            ring = QColor(color)
            ring.setAlpha(int(color.alpha() * alpha_factor))
            pen = QPen(ring, max(1.4, width * self._wave_strength))
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(center, radius, radius)

    def _get_wave_progress(self) -> float:
        return self._wave_progress

    def _set_wave_progress(self, value: float) -> None:
        self._wave_progress = float(value)
        self.update()

    def _get_wave_strength(self) -> float:
        return self._wave_strength

    def _set_wave_strength(self, value: float) -> None:
        self._wave_strength = float(value)
        self.update()

    waveProgress = Property(float, _get_wave_progress, _set_wave_progress)
    waveStrength = Property(float, _get_wave_strength, _set_wave_strength)


AuraRings = PowerAuraWidget


class SidebarHighlight:
    """Compatibility shim: SidebarPanel renders and animates its own highlight."""


class FlowLayout(QLayout):
    def __init__(self, parent: QWidget | None = None, margin: int = 0, spacing: int = 8) -> None:
        super().__init__(parent)
        self._items: list[QWidgetItem] = []
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item) -> None:
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self) -> Qt.Orientations:
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect: QRect) -> None:
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        from PySide6.QtCore import QSize
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _do_layout(self, rect: QRect, test_only: bool) -> int:
        margins = self.contentsMargins()
        effective = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x = effective.x()
        y = effective.y()
        line_height = 0
        for item in self._items:
            hint = item.sizeHint()
            next_x = x + hint.width() + self.spacing()
            if line_height > 0 and next_x - self.spacing() > effective.right() + 1:
                x = effective.x()
                y += line_height + self.spacing()
                next_x = x + hint.width() + self.spacing()
                line_height = 0
            if not test_only:
                item.setGeometry(QRect(x, y, hint.width(), hint.height()))
            x = next_x
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + margins.bottom()


class ClickableCard(QFrame):
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setProperty("class", "fileModeCard")
        self.setProperty("hovered", False)

    def enterEvent(self, event: QEvent) -> None:
        self.setProperty("hovered", True)
        self.style().unpolish(self)
        self.style().polish(self)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self.setProperty("hovered", False)
        self.style().unpolish(self)
        self.style().polish(self)
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)
