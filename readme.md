### 注意: 这是一个使用AI生成的工程

vibe code键盘上位机改键程序和hook程序, python开发通过TCP与桥接程序连接, 实现和蓝牙键盘的通信

hook文件夹中为hook的程序代码, 主要与ble_tcp_bridge通信, 发送claude状态给键盘

`install_hook.py`代码已知bug, python路径存在空格时hook失败, hook脚本存在空格时估计也会失败

##### TODO:

1. 配置键盘的ui太扁了, 重新配置一下
