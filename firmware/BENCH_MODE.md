# USB 联调模式（舵机 PWM 关闭）

NodeHexa 的 USB 口适合下载固件、调试串口和通信联调，不适合带着整机舵机运行。没有合规格电池时，舵机可能因供电不足而随机嗡鸣或抖动。开发灵机板与机器人板之间的 UART 链路时，可先给机器人刷入独立的联调固件，让两块板继续安装在机体上，但不驱动任何舵机。

## 固件行为

- `nodehexa-bench` 对应原版六足硬件；`nodehexa-v2-bench` 对应 V2 六足硬件。两者都保留 Wi-Fi、Web、UART2 和状态接口。
- 进入程序时默认关闭舵机 PWM 写入；PCA9685 初始化后发送全通道关闭命令。收到运动指令也不会产生舵机脉冲。
- 不运行电池监测任务，因此 USB 供电时不会把“没有电池”误判为低电量并持续报警。
- `GET /api/caps` 返回 `firmware.benchMode: true`、`power.servoPwmWriteAllowed: false`、`power.servoPwmReleased: true` 和 `power.batteryMonitoringActive: false`。UART v2 HELLO 也返回 `benchMode: true` 与 `servo_output_disabled` 能力。

## 使用步骤

1. 断开机器人电池、USB 和灵机板电源。第一次刷联调固件前，原有固件仍会控制舵机；为避免刷机期间运动，**先断开舵机供电或拔下舵机插头**。不要带电插拔舵机插头。
2. 确认机器人硬件版本，选择 `nodehexa-bench` 或 `nodehexa-v2-bench`，通过 PlatformIO 编译、烧录。macOS 可用 `~/.platformio/penv/bin/pio run -d firmware -e nodehexa-v2-bench -t upload --upload-port /dev/cu.<实际端口>`；将环境名和端口替换为实际值。
3. 只用 USB 给机器人主控供电，打开 `http://192.168.4.1/api/caps` 核对上述字段。若 `servoPwmReleased` 不是 `true`，不要重新接入舵机，先检查 PCA9685/I²C。
4. 两板都断电后，再按 [两板接线说明](lingji-xjwb03/ROBOT_LINK_WIRING.md)连接 UART TX、RX 与 GND。两板分别供电，不连接 5V/3V3。此时可以测试握手、状态、语音和视觉触发，但机器人不会做动作。
5. 电池修好后，先确认电池规格、极性和接口与机器人板匹配，再刷回普通 `nodehexa-v2` 或 `nodemcu-32s` 固件做运动测试。不要把电池直接接 ESP32 的 USB/5V 针脚。

联调固件是一道软件保护；上电瞬间、接线错误、PCA9685 故障或舵机信号线浮空仍可能造成异常动作。需要绝对静止时，物理断开舵机供电。没有合适电池时不要用 USB 驱动整机行走。
