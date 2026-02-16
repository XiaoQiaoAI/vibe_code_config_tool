"""
按键绑定编辑器 — 快捷键/宏编辑 + 描述字段
"""

from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QGroupBox, QStackedWidget, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QSpinBox,
)
from PySide6.QtCore import Signal, Qt

from ...core.keycodes import (
    KeyType, KEYCODES_BY_CATEGORY, get_keycode_name,
)
from ...core.keymap import KeyBinding, MAX_DESCRIPTION_LEN
from ...comm.protocol import MacroAction


class KeyEditor(QFrame):
    """按键绑定编辑面板"""

    binding_changed = Signal(object)  # KeyBinding

    def __init__(self, parent=None):
        super().__init__(parent)
        self._binding = KeyBinding()
        self._updating = False
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # ========== 描述 ==========
        desc_group = QGroupBox("按键描述")
        desc_layout = QVBoxLayout(desc_group)
        desc_hint = QLabel("显示在键盘屏幕上 (max 20 ASCII字符)")
        desc_hint.setStyleSheet("color: #888; font-size: 11px;")
        desc_layout.addWidget(desc_hint)
        self.desc_edit = QLineEdit()
        self.desc_edit.setMaxLength(MAX_DESCRIPTION_LEN)
        self.desc_edit.setPlaceholderText("例: Ctrl+C, open CMD...")
        self.desc_edit.textChanged.connect(self._on_desc_changed)
        desc_layout.addWidget(self.desc_edit)
        layout.addWidget(desc_group)

        # ========== 类型选择 ==========
        type_group = QGroupBox("按键类型")
        type_layout = QVBoxLayout(type_group)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["快捷键", "宏"])
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        type_layout.addWidget(self.type_combo)
        layout.addWidget(type_group)

        # ========== 堆叠编辑区 ==========
        self.stack = QStackedWidget()

        # --- 快捷键面板 ---
        self.shortcut_panel = QFrame()
        sc_layout = QVBoxLayout(self.shortcut_panel)
        sc_layout.addWidget(QLabel("键码列表 (修饰键在前, 普通键在后):"))

        self.shortcut_list = QListWidget()
        self.shortcut_list.setMaximumHeight(120)
        sc_layout.addWidget(self.shortcut_list)

        sc_btn_row = QHBoxLayout()
        self.sc_add_combo = QComboBox()
        self.sc_add_combo.setMinimumWidth(150)
        self._populate_all_keys(self.sc_add_combo)
        sc_btn_row.addWidget(self.sc_add_combo)

        sc_add_btn = QPushButton("添加")
        sc_add_btn.clicked.connect(self._add_shortcut_key)
        sc_btn_row.addWidget(sc_add_btn)

        sc_remove_btn = QPushButton("删除")
        sc_remove_btn.clicked.connect(self._remove_shortcut_key)
        sc_btn_row.addWidget(sc_remove_btn)

        sc_layout.addLayout(sc_btn_row)
        sc_layout.addStretch()
        self.stack.addWidget(self.shortcut_panel)

        # --- 宏面板 ---
        self.macro_panel = QFrame()
        mc_layout = QVBoxLayout(self.macro_panel)
        mc_layout.addWidget(QLabel("宏步骤 (动作 + 参数):"))

        self.macro_list = QListWidget()
        self.macro_list.setMaximumHeight(150)
        mc_layout.addWidget(self.macro_list)

        # 添加步骤行
        mc_add_row = QHBoxLayout()
        mc_add_row.addWidget(QLabel("动作:"))
        self.mc_action_combo = QComboBox()
        self.mc_action_combo.addItem("按下键", MacroAction.DOWN_KEY)
        self.mc_action_combo.addItem("释放键", MacroAction.UP_KEY)
        self.mc_action_combo.addItem("释放所有", MacroAction.UP_ALLKEY)
        self.mc_action_combo.addItem("延迟", MacroAction.DELAY)
        self.mc_action_combo.currentIndexChanged.connect(self._on_macro_action_changed)
        mc_add_row.addWidget(self.mc_action_combo)
        mc_layout.addLayout(mc_add_row)

        # 参数行 (键码或延迟值)
        mc_param_row = QHBoxLayout()
        mc_param_row.addWidget(QLabel("参数:"))
        self.mc_key_combo = QComboBox()
        self.mc_key_combo.setMinimumWidth(120)
        self._populate_all_keys(self.mc_key_combo)
        mc_param_row.addWidget(self.mc_key_combo)

        self.mc_delay_spin = QSpinBox()
        self.mc_delay_spin.setRange(1, 255)
        self.mc_delay_spin.setValue(100)
        self.mc_delay_spin.setSuffix(" (×3ms)")
        self.mc_delay_spin.setVisible(False)
        mc_param_row.addWidget(self.mc_delay_spin)

        mc_layout.addLayout(mc_param_row)

        mc_btn_row = QHBoxLayout()
        mc_add_btn = QPushButton("添加步骤")
        mc_add_btn.clicked.connect(self._add_macro_step)
        mc_btn_row.addWidget(mc_add_btn)

        mc_remove_btn = QPushButton("删除步骤")
        mc_remove_btn.clicked.connect(self._remove_macro_step)
        mc_btn_row.addWidget(mc_remove_btn)

        mc_layout.addLayout(mc_btn_row)
        mc_layout.addStretch()
        self.stack.addWidget(self.macro_panel)

        layout.addWidget(self.stack)

    def _populate_all_keys(self, combo: QComboBox):
        """填充所有键码到下拉框 (含修饰键)"""
        combo.clear()
        for cat_name, display_name in [
            ("modifier", "--- 修饰键 ---"),
            ("alpha", "--- 字母 ---"), ("number", "--- 数字 ---"),
            ("basic", "--- 基础 ---"), ("function", "--- F键 ---"),
            ("control", "--- 控制 ---"), ("arrow", "--- 方向 ---"),
            ("numpad", "--- 小键盘 ---"),
        ]:
            items = KEYCODES_BY_CATEGORY.get(cat_name, [])
            if not items:
                continue
            combo.addItem(display_name, -1)
            for name, code in items:
                combo.addItem(f"  {name} (0x{code:02X})", code)

    def set_binding(self, binding: KeyBinding):
        """设置当前编辑的绑定"""
        self._updating = True
        self._binding = binding

        self.desc_edit.setText(binding.description)
        self.type_combo.setCurrentIndex(binding.key_type)
        self.stack.setCurrentIndex(binding.key_type)

        # 刷新快捷键列表
        self.shortcut_list.clear()
        for code in binding.keycodes:
            self.shortcut_list.addItem(f"{get_keycode_name(code)} (0x{code:02X})")

        # 刷新宏列表
        self._refresh_macro_list()

        self._updating = False

    def _refresh_macro_list(self):
        self.macro_list.clear()
        data = self._binding.macro_data
        action_names = {
            MacroAction.NO_OP: "NOP",
            MacroAction.DOWN_KEY: "按下",
            MacroAction.UP_KEY: "释放",
            MacroAction.DELAY: "延迟",
            MacroAction.UP_ALLKEY: "释放所有",
        }
        for i in range(0, len(data) - 1, 2):
            action, param = data[i], data[i + 1]
            act_name = action_names.get(action, f"?{action}")
            if action == MacroAction.DELAY:
                self.macro_list.addItem(f"{act_name} {param}×3ms")
            elif action == MacroAction.UP_ALLKEY:
                self.macro_list.addItem(f"{act_name}")
            else:
                self.macro_list.addItem(f"{act_name} {get_keycode_name(param)}")

    def _emit_change(self):
        if not self._updating:
            self.binding_changed.emit(self._binding)

    # ========== 描述 ==========

    def _on_desc_changed(self, text: str):
        # 只允许 ASCII
        ascii_text = text.encode("ascii", errors="ignore").decode("ascii")
        if ascii_text != text:
            self._updating = True
            self.desc_edit.setText(ascii_text)
            self._updating = False
        self._binding.description = ascii_text[:MAX_DESCRIPTION_LEN]
        self._emit_change()

    # ========== 类型切换 ==========

    def _on_type_changed(self, index: int):
        self.stack.setCurrentIndex(index)
        self._binding.key_type = index
        self._emit_change()

    # ========== 快捷键编辑 ==========

    def _add_shortcut_key(self):
        code = self.sc_add_combo.currentData()
        if code is not None and code >= 0:
            self._binding.keycodes.append(code)
            self.shortcut_list.addItem(f"{get_keycode_name(code)} (0x{code:02X})")
            self._emit_change()

    def _remove_shortcut_key(self):
        row = self.shortcut_list.currentRow()
        if row >= 0:
            self._binding.keycodes.pop(row)
            self.shortcut_list.takeItem(row)
            self._emit_change()

    # ========== 宏编辑 ==========

    def _on_macro_action_changed(self, index: int):
        action = self.mc_action_combo.currentData()
        is_delay = (action == MacroAction.DELAY)
        is_no_param = (action == MacroAction.UP_ALLKEY)
        self.mc_key_combo.setVisible(not is_delay and not is_no_param)
        self.mc_delay_spin.setVisible(is_delay)

    def _add_macro_step(self):
        action = self.mc_action_combo.currentData()
        if action is None:
            return

        if action == MacroAction.DELAY:
            param = self.mc_delay_spin.value()
        elif action == MacroAction.UP_ALLKEY:
            param = 0
        else:
            param = self.mc_key_combo.currentData()
            if param is None or param < 0:
                return

        self._binding.macro_data.extend([action, param])
        self._refresh_macro_list()
        self._emit_change()

    def _remove_macro_step(self):
        row = self.macro_list.currentRow()
        if row >= 0:
            idx = row * 2
            if idx + 1 < len(self._binding.macro_data):
                del self._binding.macro_data[idx:idx + 2]
                self._refresh_macro_list()
                self._emit_change()
