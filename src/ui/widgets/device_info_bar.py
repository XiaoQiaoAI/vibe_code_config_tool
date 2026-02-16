"""
设备信息栏 — 显示电量、信号、固件等信息
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Signal


class DeviceInfoBar(QFrame):
    """设备信息显示栏"""

    refresh_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)

        self._labels = {}
        fields = [
            ("battery", "电量"),
            ("signal", "信号"),
            ("fw_main", "固件主版本"),
            ("fw_sub", "固件子版本"),
            ("work_mode", "工作模式"),
            ("ble_status", "BLE"),
        ]

        for key, name in fields:
            lbl = QLabel(f"{name}: --")
            lbl.setStyleSheet("font-size: 12px; color: #aaa; margin-right: 12px;")
            self._labels[key] = lbl
            layout.addWidget(lbl)

        layout.addStretch()

        refresh_btn = QPushButton("刷新")
        refresh_btn.setFixedWidth(60)
        refresh_btn.clicked.connect(self.refresh_requested)
        layout.addWidget(refresh_btn)

    def update_device_info(self, info: dict):
        """更新设备信息显示"""
        mapping = {
            "battery": ("BatteryLevel", "电量", "%"),
            "signal": ("SignalStrength", "信号", ""),
            "fw_main": ("FwMain", "固件主版本", ""),
            "fw_sub": ("FwSub", "固件子版本", ""),
            "work_mode": ("WorkMode", "工作模式", ""),
        }
        for key, (info_key, name, unit) in mapping.items():
            val = info.get(info_key, "--")
            self._labels[key].setText(f"{name}: {val}{unit}")

    def update_ble_status(self, info: dict):
        """更新 BLE 连接状态"""
        if info.get("connected"):
            name = info.get("name", "Unknown")
            self._labels["ble_status"].setText(f"BLE: {name} (已连接)")
            self._labels["ble_status"].setStyleSheet("font-size: 12px; color: #4caf50; margin-right: 12px;")
        else:
            self._labels["ble_status"].setText("BLE: 未连接")
            self._labels["ble_status"].setStyleSheet("font-size: 12px; color: #f44336; margin-right: 12px;")
