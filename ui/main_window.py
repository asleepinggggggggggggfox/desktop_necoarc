from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, Qt, QTimer
from PySide6.QtWidgets import QApplication, QGraphicsOpacityEffect, QMainWindow, QMenu, QPushButton

from core.audio_recorder import AudioRecorder
from core.config import AppConfig, ROOT
from core.conversation_state import ConversationState
from core.deepseek_client import DeepSeekClient
from core.xunfei_speech_to_text import XunfeiSpeechToText
from ui.bubble_widget import BubbleWidget
from ui.character_widget import CharacterWidget


class MainWindow(QMainWindow):
    def __init__(self, config: AppConfig):
        super().__init__()
        self.config = config
        self.state = ConversationState()
        self.deepseek = DeepSeekClient(config)
        self.speech = XunfeiSpeechToText(config)
        self.recorder = AudioRecorder(config)
        self.executor = ThreadPoolExecutor(max_workers=2)
        self._drag_pos: QPoint | None = None
        self._recording = False

        flags = Qt.FramelessWindowHint | Qt.Tool
        if config.always_on_top:
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(config.window_width, config.window_height)
        self.setFixedSize(config.window_width, config.window_height)

        self.character = CharacterWidget(ROOT / config.character_image, self)
        self.user_prev = BubbleWidget("left", "input", self.state.user_previous, self)
        self.user_current = BubbleWidget("left", "input", self.state.user_current, self)
        self.ai_prev = BubbleWidget("right", "output", self.state.ai_previous, self)
        self.ai_current = BubbleWidget("right", "output", self.state.ai_current, self)

        self._ai_prev_effect = QGraphicsOpacityEffect(self.ai_prev)
        self.ai_prev.setGraphicsEffect(self._ai_prev_effect)
        self._ai_prev_effect.setOpacity(1.0)
        self._fade_anim: QPropertyAnimation | None = None

        self.record_button = QPushButton("录音", self)
        self.record_button.clicked.connect(self.toggle_recording)
        self.record_button.setStyleSheet(
            "QPushButton { background: rgba(255,255,252,210); color: #1f1f1f; "
            "border: 1px solid rgba(20,20,20,210); border-radius: 10px; "
            "padding: 3px 9px; font: 11px 'Microsoft YaHei UI'; }"
            "QPushButton:hover { background: rgba(255,255,255,235); }"
            "QPushButton:pressed { background: rgba(232,232,228,235); }"
            "QPushButton:disabled { color: rgba(40,40,40,150); background: rgba(245,245,240,150); }"
        )

        self.refresh_state()

    def resizeEvent(self, event) -> None:
        self.layout_widgets()

    def layout_widgets(self) -> None:
        width = self.width()
        height = self.height()
        margin_x = int(width * 0.055)
        top_y = 12
        controls_y = height - 25
        max_bubble_w = int(width * 0.35)
        max_prev_h = int(height * 0.34)
        max_current_h = controls_y - top_y - 8

        user_prev_w, user_prev_h = self.user_prev.preferred_size(max_bubble_w, max_prev_h)
        ai_prev_w, ai_prev_h = self.ai_prev.preferred_size(max_bubble_w, max_prev_h)
        user_current_w, user_current_h = self.user_current.preferred_size(max_bubble_w, max_current_h)
        ai_current_w, ai_current_h = self.ai_current.preferred_size(max_bubble_w, max_current_h)

        bottom_h = max(user_current_h, ai_current_h)
        default_bottom_y = int(height * 0.57)
        bottom_y = max(top_y, min(default_bottom_y, controls_y - bottom_h - 8))

        self.user_prev.setGeometry(margin_x, top_y, user_prev_w, user_prev_h)
        self.user_current.setGeometry(margin_x, bottom_y, user_current_w, user_current_h)
        self.ai_prev.setGeometry(width - margin_x - ai_prev_w, top_y, ai_prev_w, ai_prev_h)
        self.ai_current.setGeometry(width - margin_x - ai_current_w, bottom_y, ai_current_w, ai_current_h)

        char_w = int(width * 0.34)
        char_h = int(height * 0.86)
        self.character.setGeometry((width - char_w) // 2, height - char_h - 12, char_w, char_h)

        self.record_button.adjustSize()
        self.record_button.move((width - self.record_button.width()) // 2, controls_y)

    def refresh_state(self) -> None:
        self.user_prev.set_text(self.state.user_previous)
        self.user_current.set_text(self.state.user_current)
        self.ai_prev.set_text(self.state.ai_previous)
        self.ai_current.set_text(self.state.ai_current)
        self.user_prev.setVisible(bool(self.state.user_previous.strip()))
        self.ai_prev.setVisible(bool(self.state.ai_previous.strip()))
        self.layout_widgets()

    def toggle_recording(self) -> None:
        if self._recording or self.recorder.is_recording:
            self.stop_recording()
        else:
            self.start_recording()

    def start_recording(self) -> None:
        if self._recording or self.recorder.is_recording:
            return
        try:
            self.state.begin_turn()
            self.refresh_state()
            self.fade_previous_output()
            self.recorder.start()
            self._recording = True
            self.record_button.setText("停止")
            self.record_button.setEnabled(True)
            self.layout_widgets()
        except Exception as exc:
            self._reset_recording_ui()
            self.state.set_error(str(exc))
            self.restore_previous_output()
            self.refresh_state()

    def stop_recording(self) -> None:
        if not self._recording and not self.recorder.is_recording:
            self._reset_recording_ui()
            return

        self._recording = False
        self.record_button.setText("处理中")
        self.record_button.setEnabled(False)
        self.layout_widgets()

        try:
            wav_path = self.recorder.stop()
            self.state.set_recognizing()
            self.refresh_state()
            future = self.executor.submit(self._voice_pipeline, wav_path)
            self._watch_future(future)
        except Exception as exc:
            self._reset_recording_ui()
            self.state.set_error(str(exc))
            self.restore_previous_output()
            self.refresh_state()

    def _voice_pipeline(self, wav_path: Path) -> tuple[str, str]:
        user_text = self.speech.transcribe(wav_path)
        reply = self.deepseek.chat(user_text)
        return user_text, reply

    def _watch_future(self, future: Future) -> None:
        timer = QTimer(self)
        timer.setInterval(100)

        def check() -> None:
            if not future.done():
                return

            timer.stop()
            timer.deleteLater()
            try:
                recognized, reply = future.result()
                self.state.set_thinking(recognized)
                self.state.set_reply(reply)
                self.restore_previous_output()
            except Exception as exc:
                self.state.set_error(str(exc))
                self.restore_previous_output()
            self._reset_recording_ui()
            self.refresh_state()

        timer.timeout.connect(check)
        timer.start()

    def _reset_recording_ui(self) -> None:
        self._recording = False
        self.recorder.reset()
        self.record_button.setText("录音")
        self.record_button.setEnabled(True)
        self.layout_widgets()

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        quit_action = menu.addAction("退出")
        action = menu.exec(event.globalPos())
        if action == quit_action:
            QApplication.quit()

    def fade_previous_output(self) -> None:
        self._animate_ai_prev_opacity(0.18, 650)

    def restore_previous_output(self) -> None:
        self._animate_ai_prev_opacity(1.0, 450)

    def _animate_ai_prev_opacity(self, target: float, duration: int) -> None:
        if self._fade_anim is not None:
            self._fade_anim.stop()
        self._fade_anim = QPropertyAnimation(self._ai_prev_effect, b"opacity", self)
        self._fade_anim.setDuration(duration)
        self._fade_anim.setStartValue(self._ai_prev_effect.opacity())
        self._fade_anim.setEndValue(target)
        self._fade_anim.setEasingCurve(QEasingCurve.InOutCubic)
        self._fade_anim.start()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_pos is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_pos = None

    def closeEvent(self, event) -> None:
        self.executor.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(event)
