"""
连接栏控件 — IP/端口/连接按钮/状态指示
"""

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton,
)
from PySide6.QtCore import Signal


class ConnectionBar(QFrame):
    """顶部连接栏"""

    connect_requested = Signal(str, int)   # host, port
    disconnect_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("connectionBar")
        self._connected = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)

        layout.addWidget(QLabel("IP:"))
        self.host_edit = QLineEdit("127.0.0.1")
        self.host_edit.setFixedWidth(120)
        layout.addWidget(self.host_edit)

        layout.addWidget(QLabel("Port:"))
        self.port_edit = QLineEdit("9000")
        self.port_edit.setFixedWidth(60)
        layout.addWidget(self.port_edit)

        self.connect_btn = QPushButton("连接")
        self.connect_btn.setFixedWidth(80)
        self.connect_btn.clicked.connect(self._on_click)
        layout.addWidget(self.connect_btn)

        self.status_label = QLabel("  未连接")
        self.status_label.setStyleSheet("color: gray; font-weight: bold;")
        layout.addWidget(self.status_label)

        layout.addStretch()

    def _on_click(self):
        if self._connected:
            self.disconnect_requested.emit()
        else:
            host = self.host_edit.text().strip()
            port = int(self.port_edit.text().strip())
            self.connect_requested.emit(host, port)

    def set_connected(self, connected: bool):
        self._connected = connected
        if connected:
            self.connect_btn.setText("断开")
            self.status_label.setText("  已连接")
            self.status_label.setStyleSheet("color: #4caf50; font-weight: bold;")
            self.host_edit.setEnabled(False)
            self.port_edit.setEnabled(False)
        else:
            self.connect_btn.setText("连接")
            self.status_label.setText("  未连接")
            self.status_label.setStyleSheet("color: gray; font-weight: bold;")
            self.host_edit.setEnabled(True)
            self.port_edit.setEnabled(True)
