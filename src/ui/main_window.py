"""
主窗口 — 顶部连接栏 + 模式选择器 + 内容区（标签页）
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QStackedWidget,
    QTabWidget, QMessageBox, QFileDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction

from .widgets.connection_bar import ConnectionBar
from .widgets.mode_selector import ModeSelector
from .widgets.device_info_bar import DeviceInfoBar
from .pages.mode_page import ModePage
from .pages.device_page import DevicePage
from ..core.device_state import DeviceState
from ..core.keymap import KeyboardConfig
from ..core.config_manager import ConfigManager


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("4键键盘配置工具")
        self.setMinimumSize(900, 700)

        self._state = DeviceState(self)
        self._config_manager = ConfigManager()

        self._setup_menu()
        self._setup_ui()
        self._connect_signals()

    def _setup_menu(self):
        menu = self.menuBar()

        file_menu = menu.addMenu("文件")

        new_action = QAction("新建配置", self)
        new_action.triggered.connect(self._new_config)
        file_menu.addAction(new_action)

        open_action = QAction("打开配置", self)
        open_action.triggered.connect(self._open_config)
        file_menu.addAction(open_action)

        save_action = QAction("保存配置", self)
        save_action.triggered.connect(self._save_config)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        save_device_action = QAction("写入设备并保存", self)
        save_device_action.triggered.connect(self._save_to_device)
        file_menu.addAction(save_device_action)

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 连接栏
        self.connection_bar = ConnectionBar()
        main_layout.addWidget(self.connection_bar)

        # 设备信息栏
        self.device_info_bar = DeviceInfoBar()
        main_layout.addWidget(self.device_info_bar)

        # 标签页: 模式配置 | 设备信息
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # --- 模式配置标签页 ---
        mode_widget = QWidget()
        mode_layout = QVBoxLayout(mode_widget)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(0)

        # 模式选择器
        self.mode_selector = ModeSelector()
        mode_layout.addWidget(self.mode_selector)

        # 模式页堆叠
        self.mode_stack = QStackedWidget()
        self._mode_pages: list[ModePage] = []
        for i in range(3):
            page = ModePage(self._state.config.modes[i])
            page.config_changed.connect(self._on_config_changed)
            self._mode_pages.append(page)
            self.mode_stack.addWidget(page)

        mode_layout.addWidget(self.mode_stack)

        self.tabs.addTab(mode_widget, "模式配置")

        # --- 设备信息标签页 ---
        self.device_page = DevicePage()
        self.tabs.addTab(self.device_page, "设备信息")

        main_layout.addWidget(self.tabs)

    def _connect_signals(self):
        # 连接栏
        self.connection_bar.connect_requested.connect(self._on_connect)
        self.connection_bar.disconnect_requested.connect(self._on_disconnect)

        # 设备信息栏
        self.device_info_bar.refresh_requested.connect(self._refresh_device_info)

        # 模式选择器
        self.mode_selector.mode_changed.connect(self._on_mode_changed)

        # 设备状态信号
        self._state.connection_changed.connect(self._on_connection_changed)
        self._state.ble_status_updated.connect(self._on_ble_status)
        self._state.device_info_updated.connect(self._on_device_info)
        self._state.error_occurred.connect(self._on_error)

    # ==============================
    # 连接管理
    # ==============================

    def _on_connect(self, host: str, port: int):
        self._state.connect_device(host, port)

    def _on_disconnect(self):
        self._state.disconnect_device()

    def _on_connection_changed(self, connected: bool):
        self.connection_bar.set_connected(connected)
        if connected:
            self.device_page.log("已连接到桥接器", "info")
            self._refresh_device_info()
            # 注入设备服务到模式页
            for page in self._mode_pages:
                page._device_service = self._state.service
        else:
            self.device_page.log("连接已断开", "error")
            for page in self._mode_pages:
                page._device_service = None

    def _refresh_device_info(self):
        self._state.query_status()
        self._state.query_info()

    def _on_ble_status(self, info: dict):
        self.device_info_bar.update_ble_status(info)
        self.device_page.update_ble_status(info)
        self.device_page.log(f"BLE状态: {info}", "recv")

    def _on_device_info(self, info: dict):
        self.device_info_bar.update_device_info(info)
        self.device_page.update_device_info(info)
        self.device_page.log(f"设备信息: {info}", "recv")

    def _on_error(self, msg: str):
        self.device_page.log(msg, "error")
        QMessageBox.warning(self, "错误", msg)

    # ==============================
    # 模式切换
    # ==============================

    def _on_mode_changed(self, mode_id: int):
        self.mode_stack.setCurrentIndex(mode_id)
        self._state.current_mode = mode_id

    # ==============================
    # 配置管理
    # ==============================

    def _on_config_changed(self):
        """当任意模式的配置发生变化"""
        pass  # 可用于标记"未保存"状态

    def _new_config(self):
        self._state.config = KeyboardConfig()
        for i, page in enumerate(self._mode_pages):
            page.set_config(self._state.config.modes[i])

    def _open_config(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "打开配置", "",
            "配置文件 (*.json);;All Files (*)"
        )
        if path:
            try:
                config = self._config_manager.load(path)
                self._state.config = config
                for i, page in enumerate(self._mode_pages):
                    page.set_config(config.modes[i])
            except Exception as e:
                QMessageBox.warning(self, "打开失败", str(e))

    def _save_config(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "保存配置", "keyboard_config.json",
            "配置文件 (*.json);;All Files (*)"
        )
        if path:
            try:
                self._config_manager.save(self._state.config, path)
            except Exception as e:
                QMessageBox.warning(self, "保存失败", str(e))

    def _save_to_device(self):
        """将所有模式的按键配置和动画上传到设备并保存"""
        if not self._state.connected:
            QMessageBox.warning(self, "提示", "请先连接设备")
            return

        try:
            # 0. 查询设备状态，获取最大帧数限制
            state0 = self._state.service.read_pic_state(0)
            max_frames = state0.get("all_mode_max_pic", 74)

            # 计算各模式的帧数
            frame_counts = [len(page.mode_config.display.frame_paths) for page in self._mode_pages]
            total_frames = sum(frame_counts)

            # 检查是否超出容量
            if total_frames > max_frames:
                QMessageBox.warning(
                    self, "容量不足",
                    f"总帧数 {total_frames} 超过设备最大容量 {max_frames}。\n"
                    f"模式0: {frame_counts[0]} 帧\n"
                    f"模式1: {frame_counts[1]} 帧\n"
                    f"模式2: {frame_counts[2]} 帧\n\n"
                    "请减少部分模式的帧数后重试。"
                )
                return

            # 1. 上传按键配置
            for page in self._mode_pages:
                page.upload_keys_to_device(self._state.service)

            # 2. 上传动画帧（从 start_index=0 开始顺序分配）
            start_index = 0
            for page in self._mode_pages:
                start_index = page.upload_to_device(self._state.service, start_index)

            # 3. 保存到设备 Flash
            self._state.service.save_config()
            QMessageBox.information(self, "成功", "配置已写入设备")
        except Exception as e:
            QMessageBox.warning(self, "写入失败", str(e))
