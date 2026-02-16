"""
通信协议定义 — 包类型、设备帧构建/解析、常量
"""

import struct
from enum import IntEnum


# ==============================
# TCP Packet Types (桥接层)
# ==============================

PKT_WRITE_DATA   = 0x01  # App -> Bridge: raw data -> BLE Write (char 0x7341)
PKT_WRITE_CMD    = 0x02  # App -> Bridge: command frame -> BLE Write (char 0x7343)
PKT_QUERY_STATUS = 0x03  # App -> Bridge: query BLE connection status
PKT_QUERY_INFO   = 0x04  # App -> Bridge: query device info
PKT_BLE_NOTIFY   = 0x81  # Bridge -> App: BLE Notify data (char 0x7344)
PKT_STATUS_RESP  = 0x82  # Bridge -> App: BLE status response
PKT_INFO_RESP    = 0x83  # Bridge -> App: device info response

PKT_NAMES = {
    PKT_WRITE_DATA:   "WriteData",
    PKT_WRITE_CMD:    "WriteCmd",
    PKT_QUERY_STATUS: "QueryStatus",
    PKT_QUERY_INFO:   "QueryInfo",
    PKT_BLE_NOTIFY:   "BleNotify",
    PKT_STATUS_RESP:  "StatusResp",
    PKT_INFO_RESP:    "InfoResp",
}


# ==============================
# Device Frame Protocol
# ==============================

FRAME_HEAD = b"\xAA\xBB"
FRAME_TAIL = b"\xCC\xDD"


class DeviceCmd(IntEnum):
    SAVE_CONFIG        = 0x04  # 保存动图及按键配置信息
    UPDATE_CUSTOME_KEY = 0x73  # 更新自定义按键
    PREPARE_WRITE      = 0x80  # 大数据写准备
    WRITE_RESULT       = 0x81  # 数据写结果
    UPDATE_PIC         = 0x82  # 图片数据更新
    READ_PIC_STATE     = 0x83  # 读取图片状态


class KeySubType(IntEnum):
    """UPDATE_CUSTOME_KEY 的子类型"""
    SHORTCUT    = 0x73  # 快捷键 (HID keycodes列表, max 98 bytes)
    MACRO       = 0x74  # 宏 (action+param对, max 98 bytes)
    DESCRIPTION = 0x75  # 描述 (ASCII, max 20 bytes)


class MacroAction(IntEnum):
    """宏步骤动作类型"""
    NO_OP      = 0  # 无操作
    DOWN_KEY   = 1  # 按下键
    UP_KEY     = 2  # 释放键
    DELAY      = 3  # 延迟 (value × 3ms, max 255)
    UP_ALLKEY  = 4  # 释放所有键


# ==============================
# TCP Packet Build/Parse
# ==============================

def build_tcp_packet(pkt_type: int, data: bytes = b"") -> bytes:
    """构建 TCP 包: [Type:1][Length:2 LE][Data:N]"""
    return struct.pack("<BH", pkt_type, len(data)) + data


# ==============================
# Device Frame Build/Parse
# ==============================

def build_device_frame(cmd_type: int, data: bytes = b"") -> bytes:
    """构建设备帧: [0xAABB][Cmd:1][Data:N][0xCCDD]"""
    return FRAME_HEAD + bytes([cmd_type]) + data + FRAME_TAIL


def parse_device_frame(raw: bytes):
    """解析设备帧, 返回 (cmd_type, data) 或 None"""
    if len(raw) < 6:
        return None
    if not (raw.startswith(FRAME_HEAD) and raw.endswith(FRAME_TAIL)):
        return None
    cmd_type = raw[2]
    data = raw[3:-2]
    return cmd_type, data


# ==============================
# Response Parsers
# ==============================

def parse_status_response(data: bytes) -> dict:
    """解析 BLE 状态响应 (PKT_STATUS_RESP)"""
    if not data:
        return {}
    offset = 0
    connected = data[offset]; offset += 1
    name_len = data[offset]; offset += 1
    name = data[offset:offset + name_len].decode("utf-8", errors="replace"); offset += name_len
    mac_len = data[offset]; offset += 1
    mac = data[offset:offset + mac_len].decode("utf-8", errors="replace"); offset += mac_len
    is_target = data[offset] if offset < len(data) else 0
    return {
        "connected": bool(connected),
        "name": name,
        "mac": mac,
        "is_target": bool(is_target),
    }


def parse_info_response(data: bytes) -> dict:
    """解析设备信息响应 (PKT_INFO_RESP)"""
    fields = [
        "BatteryLevel", "SignalStrength", "FwMain", "FwSub",
        "WorkMode", "LightMode", "SwitchState", "Reserve",
    ]
    result = {}
    for i, name in enumerate(fields):
        result[name] = data[i] if i < len(data) else 0
    return result


def parse_pic_state_response(data: bytes) -> dict:
    """解析图片状态响应 (READ_PIC_STATE)
    返回: {mode, start_index, pic_length, frame_interval, all_mode_max_pic}
    """
    if len(data) < 9:
        return {}
    mode, start_index, pic_length, frame_interval, all_mode_max_pic = struct.unpack("<BHHHH", data)
    return {
        "mode": mode,
        "start_index": start_index,
        "pic_length": pic_length,
        "frame_interval": frame_interval,
        "all_mode_max_pic": all_mode_max_pic,
    }
