"""
设备信息页 — 显示设备详情和通信日志
"""

from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout, QLabel,
    QTextEdit, QPushButton, QHBoxLayout,
)
from PySide6.QtCore import Qt


class DevicePage(QWidget):
    """设备信息和调试日志页"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ========== 设备信息 ==========
        info_group = QGroupBox("设备信息")
        info_layout = QGridLayout(info_group)

        self._info_labels = {}
        fields = [
            (0, 0, "battery", "电量"),
            (0, 1, "signal", "信号强度"),
            (0, 2, "fw_main", "固件主版本"),
            (0, 3, "fw_sub", "固件子版本"),
            (1, 0, "work_mode", "工作模式"),
            (1, 1, "light_mode", "灯光模式"),
            (1, 2, "switch_state", "开关状态"),
        ]

        for row, col, key, name in fields:
            lbl_name = QLabel(f"{name}:")
            lbl_name.setStyleSheet("color: #888;")
            lbl_val = QLabel("--")
            lbl_val.setStyleSheet("font-weight: bold;")
            info_layout.addWidget(lbl_name, row, col * 2)
            info_layout.addWidget(lbl_val, row, col * 2 + 1)
            self._info_labels[key] = lbl_val

        layout.addWidget(info_group)

        # ========== BLE 状态 ==========
        ble_group = QGroupBox("BLE 连接状态")
        ble_layout = QGridLayout(ble_group)

        self._ble_labels = {}
        for col, (key, name) in enumerate([
            ("connected", "连接"), ("name", "设备名"),
            ("mac", "MAC地址"), ("is_target", "目标设备"),
        ]):
            lbl_name = QLabel(f"{name}:")
            lbl_name.setStyleSheet("color: #888;")
            lbl_val = QLabel("--")
            lbl_val.setStyleSheet("font-weight: bold;")
            ble_layout.addWidget(lbl_name, 0, col * 2)
            ble_layout.addWidget(lbl_val, 0, col * 2 + 1)
            self._ble_labels[key] = lbl_val

        layout.addWidget(ble_group)

        # ========== 通信日志 ==========
        log_group = QGroupBox("通信日志")
        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("font-family: Consolas, monospace; font-size: 11px;")
        log_layout.addWidget(self.log_text)

        btn_row = QHBoxLayout()
        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self.log_text.clear)
        btn_row.addStretch()
        btn_row.addWidget(clear_btn)
        log_layout.addLayout(btn_row)

        layout.addWidget(log_group)

    def update_device_info(self, info: dict):
        """更新设备信息显示"""
        mapping = {
            "battery": "BatteryLevel",
            "signal": "SignalStrength",
            "fw_main": "FwMain",
            "fw_sub": "FwSub",
            "work_mode": "WorkMode",
            "light_mode": "LightMode",
            "switch_state": "SwitchState",
        }
        for key, info_key in mapping.items():
            val = info.get(info_key, "--")
            self._info_labels[key].setText(str(val))

    def update_ble_status(self, info: dict):
        """更新 BLE 状态显示"""
        self._ble_labels["connected"].setText("已连接" if info.get("connected") else "未连接")
        self._ble_labels["name"].setText(info.get("name", "--"))
        self._ble_labels["mac"].setText(info.get("mac", "--"))
        self._ble_labels["is_target"].setText("是" if info.get("is_target") else "否")

    def log(self, message: str, level: str = "info"):
        """添加日志"""
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        colors = {"info": "#aaa", "send": "#4fc3f7", "recv": "#66bb6a", "error": "#f44336"}
        color = colors.get(level, "#aaa")
        self.log_text.append(f'<span style="color:{color}">{ts} &gt; {message}</span>')
