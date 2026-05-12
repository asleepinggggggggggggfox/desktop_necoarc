from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConversationState:
    user_previous: str = ""
    user_current: str = "按左 Alt 开始录音"
    ai_previous: str = ""
    ai_current: str = "等待你的问题"

    def begin_turn(self) -> None:
        if self.user_current and self.user_current not in {
            "按左 Alt 开始录音",
            "正在录音...",
            "正在识别...",
        }:
            self.user_previous = self.user_current
        if self.ai_current and self.ai_current not in {"等待你的问题", "思考中..."}:
            self.ai_previous = self.ai_current
        self.user_current = "正在录音..."
        self.ai_current = "等待你的问题"

    def set_recognizing(self) -> None:
        self.user_current = "正在识别..."

    def set_thinking(self, user_text: str) -> None:
        self.user_current = user_text
        self.ai_current = "思考中..."

    def set_reply(self, reply: str) -> None:
        self.ai_current = reply

    def set_error(self, message: str) -> None:
        self.ai_current = message
