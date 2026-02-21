"""
模式配置页 — 单个模式的按键映射 + 动画管理
"""

import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox,
    QLabel, QPushButton, QSpinBox, QFileDialog, QListWidget,
    QListWidgetItem, QAbstractItemView, QMessageBox, QProgressDialog,
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QIcon

from ..widgets.keyboard_view import KeyboardView
from ..widgets.key_editor import KeyEditor
from ..widgets.image_preview import ImagePreview
from ...core.keymap import ModeConfig, KeyBinding, MAX_KEY_DATA_LEN, MAX_DESCRIPTION_LEN
from ...core.keycodes import KeyType
from ...comm.protocol import KeySubType
from ...core.image_processor import (
    process_image, extract_gif_frames, load_image,
    DISPLAY_WIDTH, DISPLAY_HEIGHT, FRAME_SLOT_SIZE, MAX_TOTAL_FRAMES,
)


class UploadWorker(QThread):
    """后台上传线程"""
    progress = Signal(int, int)  # sent, total
    finished = Signal(bool, str)  # success, message

    def __init__(self, service, mode_id, frames_data, start_index, fps):
        super().__init__()
        self._service = service
        self._mode_id = mode_id
        self._frames_data = frames_data
        self._start_index = start_index
        self._fps = fps

    def run(self):
        try:
            total = len(self._frames_data)
            for i, frame_bytes in enumerate(self._frames_data):
                addr = (self._start_index + i) * FRAME_SLOT_SIZE
                self._service.write_large_data(addr, frame_bytes)
                self.progress.emit(i + 1, total)

            self._service.update_pic(
                self._mode_id, self._start_index, total, fps=self._fps
            )
            self.finished.emit(True, "上传完成")
        except Exception as e:
            self.finished.emit(False, str(e))


class ModePage(QWidget):
    """单个模式的完整配置页面"""

    config_changed = Signal()

    def __init__(self, mode_config: ModeConfig, parent=None):
        super().__init__(parent)
        self._config = mode_config
        self._processed_frames = []  # list of ProcessedFrame
        self._upload_worker = None
        self._setup_ui()
        self._refresh_ui()

    @property
    def mode_config(self) -> ModeConfig:
        return self._config

    def set_config(self, config: ModeConfig):
        self._config = config
        self._refresh_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Vertical)

        # ========== 上半部分: 按键映射 ==========
        keymap_group = QGroupBox("按键映射")
        keymap_outer = QVBoxLayout(keymap_group)
        keymap_layout = QHBoxLayout()

        # 左: 键盘视图
        self.keyboard_view = KeyboardView()
        self.keyboard_view.key_selected.connect(self._on_key_selected)
        keymap_layout.addWidget(self.keyboard_view, stretch=3)

        # 右: 编辑面板
        self.key_editor = KeyEditor()
        self.key_editor.binding_changed.connect(self._on_binding_changed)
        keymap_layout.addWidget(self.key_editor, stretch=2)

        keymap_outer.addLayout(keymap_layout)

        # 应用按键按钮（居中布局）
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        apply_keys_btn = QPushButton("应用按键到设备")
        apply_keys_btn.setStyleSheet(
            "background-color: #2e7d32; color: white; font-weight: bold; "
            "padding: 8px 24px; min-width: 150px;"
        )
        apply_keys_btn.clicked.connect(self._apply_keys_to_device)
        btn_layout.addWidget(apply_keys_btn)
        btn_layout.addStretch(1)
        btn_layout.setContentsMargins(0, 8, 0, 4)
        keymap_outer.addLayout(btn_layout)

        splitter.addWidget(keymap_group)

        # ========== 下半部分: 动画管理 ==========
        display_group = QGroupBox("动画管理")
        display_layout = QHBoxLayout(display_group)

        # 左: 帧列表
        frame_list_layout = QVBoxLayout()

        self.frame_list = QListWidget()
        self.frame_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.frame_list.currentRowChanged.connect(self._on_frame_selected)
        frame_list_layout.addWidget(self.frame_list)

        # 按钮行
        btn_row = QHBoxLayout()
        add_img_btn = QPushButton("添加图片")
        add_img_btn.clicked.connect(self._add_images)
        btn_row.addWidget(add_img_btn)

        add_gif_btn = QPushButton("添加 GIF")
        add_gif_btn.clicked.connect(self._add_gif)
        btn_row.addWidget(add_gif_btn)

        remove_btn = QPushButton("删除")
        remove_btn.clicked.connect(self._remove_frame)
        btn_row.addWidget(remove_btn)

        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._clear_frames)
        btn_row.addWidget(clear_btn)

        frame_list_layout.addLayout(btn_row)

        # FPS 设置
        fps_row = QHBoxLayout()
        fps_row.addWidget(QLabel("FPS:"))
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 30)
        self.fps_spin.setValue(10)
        self.fps_spin.valueChanged.connect(self._on_fps_changed)
        fps_row.addWidget(self.fps_spin)
        fps_row.addStretch()

        self.frame_count_label = QLabel("0 帧")
        fps_row.addWidget(self.frame_count_label)

        frame_list_layout.addLayout(fps_row)

        display_layout.addLayout(frame_list_layout, stretch=2)

        # 右: 预览
        preview_layout = QVBoxLayout()
        self.image_preview = ImagePreview()
        preview_layout.addWidget(self.image_preview)

        preview_btn_row = QHBoxLayout()
        play_btn = QPushButton("播放预览")
        play_btn.clicked.connect(self._play_preview)
        preview_btn_row.addWidget(play_btn)

        upload_btn = QPushButton("上传到设备")
        upload_btn.setStyleSheet("background-color: #1565c0; color: white; font-weight: bold; padding: 6px 16px;")
        upload_btn.clicked.connect(self._upload_to_device)
        preview_btn_row.addWidget(upload_btn)

        preview_layout.addLayout(preview_btn_row)

        display_layout.addLayout(preview_layout, stretch=3)

        splitter.addWidget(display_group)

        # 设置初始大小比例：按键映射区域占更多空间
        splitter.setSizes([500, 300])
        splitter.setStretchFactor(0, 3)  # 按键映射区域
        splitter.setStretchFactor(1, 2)  # 动画管理区域

        layout.addWidget(splitter)

    def _refresh_ui(self):
        """从配置刷新 UI"""
        # 更新键盘视图标签
        labels = [k.label for k in self._config.keys]
        self.keyboard_view.update_key_labels(labels)

        # 更新当前选中键的编辑器
        key_idx = self.keyboard_view.selected_key()
        if 0 <= key_idx < len(self._config.keys):
            self.key_editor.set_binding(self._config.keys[key_idx])

        # 更新 FPS
        self.fps_spin.setValue(self._config.display.fps)

        # 更新帧列表
        self._update_frame_list()

    def _on_key_selected(self, key_index: int):
        if 0 <= key_index < len(self._config.keys):
            self.key_editor.set_binding(self._config.keys[key_index])

    def _on_binding_changed(self, binding: KeyBinding):
        key_idx = self.keyboard_view.selected_key()
        if 0 <= key_idx < len(self._config.keys):
            self._config.keys[key_idx] = binding
            labels = [k.label for k in self._config.keys]
            self.keyboard_view.update_key_labels(labels)
            self.config_changed.emit()

    def _on_fps_changed(self, value: int):
        self._config.display.fps = value
        self.config_changed.emit()

    # ==============================
    # 帧管理
    # ==============================

    def _update_frame_list(self):
        self.frame_list.clear()
        self._processed_frames.clear()
        for path in self._config.display.frame_paths:
            if os.path.exists(path):
                item = QListWidgetItem(os.path.basename(path))
                item.setData(Qt.UserRole, path)
                self.frame_list.addItem(item)
        self.frame_count_label.setText(f"{self.frame_list.count()} 帧")

    def _add_images(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择图片", "",
            "Images (*.png *.jpg *.jpeg *.bmp);;All Files (*)"
        )
        if files:
            self._config.display.frame_paths.extend(files)
            self._update_frame_list()
            self.config_changed.emit()

    def _add_gif(self):
        file, _ = QFileDialog.getOpenFileName(
            self, "选择 GIF", "",
            "GIF Files (*.gif);;All Files (*)"
        )
        if file:
            try:
                frames = extract_gif_frames(file)
                # 将 GIF 帧保存为临时 PNG
                import tempfile
                temp_dir = tempfile.mkdtemp(prefix="kb_frames_")
                for i, frame in enumerate(frames):
                    path = os.path.join(temp_dir, f"frame_{i:04d}.png")
                    frame.save(path)
                    self._config.display.frame_paths.append(path)
                self._update_frame_list()
                self.config_changed.emit()
            except Exception as e:
                QMessageBox.warning(self, "错误", f"GIF 解析失败: {e}")

    def _remove_frame(self):
        row = self.frame_list.currentRow()
        if row >= 0:
            self._config.display.frame_paths.pop(row)
            self._update_frame_list()
            self.config_changed.emit()

    def _clear_frames(self):
        self._config.display.frame_paths.clear()
        self._update_frame_list()
        self.image_preview.clear()
        self.config_changed.emit()

    def _on_frame_selected(self, row: int):
        if row >= 0 and row < len(self._config.display.frame_paths):
            path = self._config.display.frame_paths[row]
            if os.path.exists(path):
                try:
                    img = load_image(path)
                    processed = process_image(img)
                    self.image_preview.set_single_image(processed.preview_image)
                except Exception:
                    pass

    def _play_preview(self):
        """播放所有帧的动画预览"""
        preview_images = []
        for path in self._config.display.frame_paths:
            if os.path.exists(path):
                try:
                    img = load_image(path)
                    processed = process_image(img)
                    preview_images.append(processed.preview_image)
                except Exception:
                    continue
        if preview_images:
            self.image_preview.set_animation(preview_images, self._config.display.fps)

    # ==============================
    # 按键配置上传
    # ==============================

    def upload_keys_to_device(self, service):
        """上传当前模式的所有按键配置到设备"""
        mode_id = self._config.mode_id
        for key_idx, binding in enumerate(self._config.keys):
            # 1. 发送快捷键或宏数据
            if binding.key_type == KeyType.SHORTCUT:
                data = bytes(binding.keycodes[:MAX_KEY_DATA_LEN])
                service.update_custom_key(mode_id, key_idx, KeySubType.SHORTCUT, data)
            elif binding.key_type == KeyType.MACRO:
                data = bytes(binding.macro_data[:MAX_KEY_DATA_LEN])
                service.update_custom_key(mode_id, key_idx, KeySubType.MACRO, data)

            # 2. 发送描述
            desc_bytes = binding.description.encode("ascii", errors="ignore")[:MAX_DESCRIPTION_LEN]
            service.update_custom_key(mode_id, key_idx, KeySubType.DESCRIPTION, desc_bytes)

    def _apply_keys_to_device(self):
        """UI 按钮触发的按键配置上传"""
        # _device_service 由 main_window 注入
        if not hasattr(self, '_device_service') or self._device_service is None:
            QMessageBox.information(self, "提示", "请先连接设备")
            return
        try:
            self.upload_keys_to_device(self._device_service)
            QMessageBox.information(self, "成功", "按键配置已写入设备")
        except Exception as e:
            QMessageBox.warning(self, "写入失败", str(e))

    # ==============================
    # 动画上传到设备
    # ==============================

    def upload_to_device(self, service, start_index: int):
        """准备并上传帧数据到设备（由外部调用）"""
        total_frames = len(self._config.display.frame_paths)

        if total_frames == 0:
            QMessageBox.information(self, "提示", "没有可上传的帧")
            return start_index

        # 立即创建并显示进度条
        progress = QProgressDialog("正在准备图片数据...", "取消", 0, total_frames, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)  # 立即显示，不等待
        progress.setValue(0)  # 强制立即显示

        # 处理图片数据
        frames_data = []
        for i, path in enumerate(self._config.display.frame_paths):
            if progress.wasCanceled():
                return start_index

            if os.path.exists(path):
                try:
                    img = load_image(path)
                    processed = process_image(img)
                    frames_data.append(processed.rgb565_data)
                except Exception:
                    continue

        if not frames_data:
            progress.close()
            QMessageBox.information(self, "提示", "没有可上传的帧")
            return start_index

        # 更新进度条文本
        progress.setLabelText("正在上传到设备...")
        progress.setMaximum(len(frames_data))
        progress.setValue(0)

        self._upload_worker = UploadWorker(
            service, self._config.mode_id, frames_data, start_index, self._config.display.fps
        )

        self._upload_worker.progress.connect(lambda sent, total: progress.setValue(sent))
        self._upload_worker.finished.connect(lambda ok, msg: self._on_upload_done(ok, msg, progress))
        self._upload_worker.start()

        return start_index + len(frames_data)

    def _upload_to_device(self):
        """UI 按钮触发的动画上传（查询设备当前状态后上传）"""
        if not hasattr(self, '_device_service') or self._device_service is None:
            QMessageBox.information(self, "提示", "请先连接设备")
            return

        try:
            # 1. 查询所有模式的状态
            all_states = []
            max_capacity = 0
            for mode_id in range(3):
                state = self._device_service.read_pic_state(mode_id)
                all_states.append(state)
                max_capacity = state.get("all_mode_max_pic", MAX_TOTAL_FRAMES)

            # 2. 获取当前要上传的模式和帧数
            current_mode = self._config.mode_id
            new_count = len(self._config.display.frame_paths)

            if new_count == 0:
                QMessageBox.information(self, "提示", "没有可上传的帧")
                return

            # 3. 构建除当前模式外的占用区域
            occupied_regions = []  # [(start, end, mode_id), ...]
            for state in all_states:
                mode_id = state.get("mode", 0)
                if mode_id == current_mode:
                    continue  # 跳过当前模式
                start = state.get("start_index", 0)
                length = state.get("pic_length", 0)
                if length > 0:
                    occupied_regions.append((start, start + length, mode_id))

            # 按起始位置排序
            occupied_regions.sort(key=lambda x: x[0])

            # 4. 寻找能容纳 new_count 帧的连续空间
            start_index = self._find_free_space(occupied_regions, new_count, max_capacity)

            # 5. 检测是否会覆盖其他模式
            end_index = start_index + new_count
            overlapped_modes = []
            for region_start, region_end, mode_id in occupied_regions:
                # 检查区间是否重叠
                if not (end_index <= region_start or start_index >= region_end):
                    overlapped_modes.append(mode_id)

            # 6. 如果有覆盖，弹出确认对话框
            if overlapped_modes:
                mode_names = [f"模式 {m}" for m in overlapped_modes]
                reply = QMessageBox.question(
                    self, "空间不足",
                    f"没有足够的连续空间存储 {new_count} 帧动画。\n\n"
                    f"上传到位置 {start_index} 将会覆盖以下模式：\n"
                    f"{', '.join(mode_names)}\n\n"
                    f"这些模式的动画将被清空（长度设为0）。\n\n"
                    f"是否继续？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if reply != QMessageBox.Yes:
                    return

                # 7. 用户确认，清空被覆盖的模式
                for mode_id in overlapped_modes:
                    self._device_service.update_pic(mode_id, 0, 0, fps=10)

            # 8. 执行上传
            self.upload_to_device(self._device_service, start_index)

        except Exception as e:
            QMessageBox.warning(self, "上传失败", str(e))

    def _find_free_space(self, occupied_regions, needed_count, max_capacity):
        """寻找能容纳 needed_count 帧的连续空间

        Args:
            occupied_regions: [(start, end, mode_id), ...] 已占用区域列表（已排序）
            needed_count: 需要的帧数
            max_capacity: 设备最大容量

        Returns:
            int: 起始位置
        """
        # 没有任何占用区域，从头开始
        if not occupied_regions:
            return 0

        # 检查开头是否有空间
        first_start = occupied_regions[0][0]
        if first_start >= needed_count:
            return 0

        # 检查相邻区域之间的间隙
        for i in range(len(occupied_regions) - 1):
            gap_start = occupied_regions[i][1]  # 当前区域结束位置
            gap_end = occupied_regions[i + 1][0]  # 下一区域开始位置
            gap_size = gap_end - gap_start

            if gap_size >= needed_count:
                return gap_start

        # 检查末尾是否有空间
        last_end = occupied_regions[-1][1]
        if last_end + needed_count <= max_capacity:
            return last_end

        # 没有足够的连续空间，选择最优覆盖位置：
        # 1. 如果从位置0开始能放下，就从0开始（覆盖第一个模式）
        if needed_count <= max_capacity:
            return 0

        # 2. 如果连容量都不够，从末尾开始（尽量保留前面的）
        return max(0, max_capacity - needed_count)

    def _on_upload_done(self, success: bool, message: str, progress: QProgressDialog):
        progress.close()
        if success:
            QMessageBox.information(self, "成功", message)
        else:
            QMessageBox.warning(self, "上传失败", message)
