# XJWB03 SDK 配置方案

本文针对用户提供的 `ljyd_xjwb03_agent_public_developer-master.zip`。它的 `README.md`、`qm_config.h`、摄像头驱动、分区表和构建脚本与已下载的官方仓库提交 `06065ce9c5aa1e14cfae5c0ad574bad4aaaae34c` 逐项一致。ZIP 内含 ESP-IDF v5.4.1、QUMIOS、应用代码和模型源文件，但没有手册所述的 `demoflashpack` 成品固件。ZIP 内容仅作为源码与资料；其中的示例产品身份不用于本项目。

## 构建环境

- 主机是 macOS arm64；官方 `dev.bat` / `build.bat` 是 Windows 脚本。已通过 `lingji.sh` 安装 SDK 自带的 ESP-IDF v5.4.1 工具链，并成功编译 ESP32-S3 自检固件。工具链位于 Git 忽略的 `.espressif/`，构建缓存位于 `sdk/apps/build/`。
- 固定上游提交；本项目按要求在 `sdk/` 保存官方源码副本，构建脚本要记录提交、配置摘要、镜像哈希和 `flash_args`。后续修改集中在应用层并标注与上游的差异，避免升级 SDK 时丢失项目代码。
- 云端配置从本机忽略的 `project_identity.local.h` 读取；当前合并固件使用用户已在平台注册的产品身份，不使用源码中的示例产品身份。官方 Windows 脚本的 `-secret` 参数会进入进程参数和 CMake 配置，本项目不用该路径。产品 PID `11684` 已在平台核对。

## 分阶段功能配置

| 阶段 | `CONFIG_QM_POSE_SUPPORT` | `CONFIG_APP_CAMERA_TEST` | 保持启用 | 验证目标 |
| --- | ---: | ---: | --- | --- |
| 0. 本地语音自检（历史） | `0` | `0` | VB701N 音频、开机音、唤醒回调 | 开机音与唤醒日志；无需平台 Agent |
| 1. 云端语音基线 | `0` | `0` | VB701N 音频、BLE 配网、Wi-Fi、云/Agent | 联网、唤醒、至少两轮对话；记录空闲内存 |
| 2. 摄像头与语音合并（当前） | `0` | `1` | 语音基线 | BF3901 取图、按需千问描述、语音回答已实测；长期并行稳定性待测 |
| 3. 姿态推理单测 | `1` | 视测试安排 | 模型分区 | 先验证内置图片，再接入真实帧；量测内存与推理时间 |
| 4. 整机 | 以实测结果定 | 以实测结果定 | UART 机器人链路、互动与偏好 | 语音、视觉、动作并行且不会因内存不足断云 |

当前 SDK 原值是姿态 `1`、摄像头 `0`，而 README 和 PDF 都描述姿态默认为关闭；构建脚本必须显式核对最终值。当前 `example_pose_run()` 只分析嵌入的 `bus.jpg`，摄像头 `cam_stream_task()` 只统计帧；注释中的摄像头到推理函数尚未接入。把视觉结果转成稳定的“坐姿/疲劳/离开等场景”还需要事件阈值、去抖和用户回应逻辑，不能把示例日志当作完成的产品能力。

## 引脚与外设

- 语音板 VB701N：UART1，TX GPIO40、RX GPIO39、流控 GPIO38，SDK 配为 2 Mbaud；保持官方配置。
- 日志/CLI：UART0，TX GPIO43、RX GPIO44，115200；保持官方配置。
- BF3901 摄像头：3.3 V，SDA GPIO21、SCL GPIO47、VSYNC/CS GPIO4、PCLK/SCLK GPIO13、D0 GPIO8、PWDN GPIO41。GPIO4 与灵机板可选舵机、GPIO8 与可选 MPU6050 复用，因此本方案不在灵机板上驱动这些外设。
- 两板链路：灵机板 UART2 TX GPIO17、RX GPIO18，分别接 NodeHexa 板下排丝印 `P16`（GPIO16，UART2 RX）、`P17`（GPIO17，UART2 TX），并共地；已完成只读 HELLO/心跳实机握手。NodeHexa 板没有标 `RX2` / `TX2`；靠右的 `RX` / `TX` 属于 USB 下载/日志串口。波特率 115200，3.3 V 逻辑。机器人供电与灵机板供电分开；动作指令尚未实现。

## 云端与应用代码

- 平台侧建立本项目自己的产品、物模型、Agent 和场景，区分测试/正式环境；设备配网仍使用官方 BLE + 2.4 GHz Wi-Fi 流程。
- 设备侧保留官方语音链路，新增机器人 UART 协议适配、视觉事件、互动状态机和显式偏好存储。云端 Agent 只下发允许列表内的高层动作与说话/提醒意图；NodeHexa 自己执行限幅、停止和低电量保护。
- 官方现有 `iot_control` 表只处理音量，`ljyd_method` 分发聊天退出和播放器等方法。机器人动作需要新增物模型或平台方法并与 Agent 工具/场景配置对齐，不能假设现有 SDK 已支持机器人控制。

## 烧录关口

`lingji.sh flash` 先确认串口为 XJWB03 的 ESP32-S3、Flash 16 MB，并备份现有内容，然后让 ESP-IDF 从本次构建的 `flash_args` 写入完整镜像集。当前构建的 `flash_args` 含 bootloader、应用、分区表、OTA 初始数据、PHY 数据和 ESPDL 模型分区；虽然姿态运行已关闭，构建配置仍包含模型分区。现有完整 Flash 备份已核对时，且分区表未变，可用 `lingji.sh flash-app` 仅更新应用分区。`backups/` 是本机备份，不提交 Git。
