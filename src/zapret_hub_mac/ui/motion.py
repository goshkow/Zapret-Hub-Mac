from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QEasingCurve, QParallelAnimationGroup, QPropertyAnimation, QRect
from PySide6.QtWidgets import QGraphicsOpacityEffect, QStackedWidget, QWidget


def ensure_opacity_effect(widget: QWidget) -> QGraphicsOpacityEffect:
    effect = widget.graphicsEffect()
    if isinstance(effect, QGraphicsOpacityEffect):
        return effect
    opacity = QGraphicsOpacityEffect(widget)
    opacity.setOpacity(1.0)
    widget.setGraphicsEffect(opacity)
    return opacity


def fade_widget(
    widget: QWidget,
    *,
    start: float = 0.0,
    end: float = 1.0,
    duration: int = 220,
    easing: QEasingCurve.Type = QEasingCurve.Type.OutCubic,
    finished: Callable[[], None] | None = None,
) -> QPropertyAnimation:
    effect = ensure_opacity_effect(widget)
    effect.setOpacity(start)
    animation = QPropertyAnimation(effect, b"opacity", widget)
    animation.setDuration(duration)
    animation.setStartValue(start)
    animation.setEndValue(end)
    animation.setEasingCurve(easing)
    if finished is not None:
        animation.finished.connect(finished)
    animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
    return animation


def cross_fade_stacked_widget(
    stacked: QStackedWidget,
    index: int,
    *,
    duration: int = 260,
    slide_offset: int = 18,
) -> None:
    if index == stacked.currentIndex():
        return

    current = stacked.currentWidget()
    target = stacked.widget(index)
    container = stacked.parentWidget()
    if current is None or target is None or container is None:
        stacked.setCurrentIndex(index)
        return

    target_rect = stacked.geometry()
    shifted_rect = QRect(target_rect)
    shifted_rect.moveTop(target_rect.top() + slide_offset)

    target.setParent(container)
    target.setGeometry(shifted_rect)
    target.show()
    target.raise_()

    current_effect = ensure_opacity_effect(current)
    target_effect = ensure_opacity_effect(target)
    current_effect.setOpacity(1.0)
    target_effect.setOpacity(0.0)

    group = QParallelAnimationGroup(stacked)

    fade_out = QPropertyAnimation(current_effect, b"opacity", group)
    fade_out.setDuration(duration)
    fade_out.setStartValue(1.0)
    fade_out.setEndValue(0.0)
    fade_out.setEasingCurve(QEasingCurve.Type.OutCubic)
    group.addAnimation(fade_out)

    fade_in = QPropertyAnimation(target_effect, b"opacity", group)
    fade_in.setDuration(duration)
    fade_in.setStartValue(0.0)
    fade_in.setEndValue(1.0)
    fade_in.setEasingCurve(QEasingCurve.Type.OutCubic)
    group.addAnimation(fade_in)

    slide_in = QPropertyAnimation(target, b"pos", group)
    slide_in.setDuration(duration)
    slide_in.setStartValue(shifted_rect.topLeft())
    slide_in.setEndValue(target_rect.topLeft())
    slide_in.setEasingCurve(QEasingCurve.Type.OutCubic)
    group.addAnimation(slide_in)

    def finalize() -> None:
        stacked.setCurrentIndex(index)
        target.setParent(stacked)
        target.setGeometry(stacked.rect())
        target_effect.setOpacity(1.0)
        current_effect.setOpacity(1.0)
        current.hide()

    group.finished.connect(finalize)
    group.start(QParallelAnimationGroup.DeletionPolicy.DeleteWhenStopped)


class FadeStackedWidget(QStackedWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._fade_duration = 260
        self._slide_offset = 18

    def set_transition_duration(self, duration: int) -> None:
        self._fade_duration = max(80, duration)

    def set_transition_offset(self, offset: int) -> None:
        self._slide_offset = max(0, offset)

    def setCurrentIndexAnimated(self, index: int) -> None:
        cross_fade_stacked_widget(
            self,
            index,
            duration=self._fade_duration,
            slide_offset=self._slide_offset,
        )

    def setCurrentWidgetAnimated(self, widget: QWidget) -> None:
        self.setCurrentIndexAnimated(self.indexOf(widget))
