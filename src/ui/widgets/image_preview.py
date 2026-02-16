"""
图片预览控件 — 显示单帧或动画预览
"""

from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, QTimer
from PIL import Image


def pil_to_qpixmap(img: Image.Image, scale: int = 2) -> QPixmap:
    """将 PIL Image 转换为 QPixmap"""
    img_rgb = img.convert("RGB")
    data = img_rgb.tobytes()
    w, h = img_rgb.size
    qimg = QImage(data, w, h, w * 3, QImage.Format_RGB888)
    pixmap = QPixmap.fromImage(qimg)
    if scale != 1:
        pixmap = pixmap.scaled(
            w * scale, h * scale,
            Qt.KeepAspectRatio,
            Qt.FastTransformation,
        )
    return pixmap


class ImagePreview(QFrame):
    """图片/动画预览控件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._frames: list[Image.Image] = []
        self._current_frame = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._next_frame)

        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self._label = QLabel()
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setMinimumSize(320, 160)
        self._label.setStyleSheet("background-color: #1a1a1a; border: 1px solid #333; border-radius: 4px;")
        layout.addWidget(self._label)

        self._info_label = QLabel("无图片")
        self._info_label.setAlignment(Qt.AlignCenter)
        self._info_label.setStyleSheet("color: #888; font-size: 11px;")
        layout.addWidget(self._info_label)

    def set_single_image(self, img: Image.Image):
        """显示单张图片"""
        self._timer.stop()
        self._frames = [img]
        self._current_frame = 0
        self._show_frame(0)
        self._info_label.setText("1 帧")

    def set_animation(self, frames: list[Image.Image], fps: int = 10):
        """设置动画帧并开始播放"""
        self._timer.stop()
        self._frames = frames
        self._current_frame = 0
        if frames:
            self._show_frame(0)
            self._info_label.setText(f"{len(frames)} 帧 @ {fps} FPS")
            if len(frames) > 1:
                self._timer.start(int(1000 / fps))
        else:
            self._label.clear()
            self._info_label.setText("无图片")

    def clear(self):
        self._timer.stop()
        self._frames = []
        self._label.clear()
        self._info_label.setText("无图片")

    def _show_frame(self, index: int):
        if 0 <= index < len(self._frames):
            pixmap = pil_to_qpixmap(self._frames[index], scale=2)
            self._label.setPixmap(pixmap)

    def _next_frame(self):
        if self._frames:
            self._current_frame = (self._current_frame + 1) % len(self._frames)
            self._show_frame(self._current_frame)
