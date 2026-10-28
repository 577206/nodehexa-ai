# 灵机平台 Agent 接入

平台已核对：产品“桌面萌宠伴侣”的**产品标识 PID 为 `11684`**；“灵犀”Agent 已关联该产品，V1 显示为当前生效版本。Agent 设置页 `/settings/2596` 中的 `2596` 是页面编号，不是 PID。云端固件已烧录，官方小程序已完成 BLE 配网，板端已获得 Wi-Fi IP 并显示 `cloud connected`；用户已确认完整语音回答和两轮连续对话正常。

## 密钥留在本机

本目录的 `project_identity.local.h` 已填 PID `11684` 和用户自己的产品密钥，权限为仅当前用户可读写，并被 Git 忽略。不要把密钥粘贴到聊天、提交到 Git，或放进命令行参数；构建脚本会拒绝占位值。

## 切换并验证固件

1. 平台侧已确认 Agent V1 生效且关联“桌面萌宠伴侣”。当前合并固件使用 `CONFIG_NODEHEXA_VOICE_SELFTEST=0`、`CONFIG_QM_POSE_SUPPORT=0` 和 `CONFIG_APP_CAMERA_TEST=1`，已实测按需视觉描述、语音回应和一次追问。此前纯云端语音固件的摄像头配置为 `0`。
2. 串口已出现 `no saved wifi, start ble provision` 和 `ready, cloud=on`。官方小程序选择“灵机 ESP32 组合开发板”，通过 BLE 发送 2.4 GHz Wi-Fi 配置后，板端已确认 `wifi got ip`、动态注册和 `cloud connected`。不要把 Wi-Fi 密码写进仓库或聊天。
3. 用 `./lingji.sh monitor /dev/cu.usbmodem...` 检查后续 Agent 会话日志。
4. 已测试“你好，小灵”→完整问答→两轮连续对话及会话内偏好确认；合并固件中用户确认听到视觉相关回答并能追问。打断/退出、跨会话偏好记忆和 NodeHexa 动作链路仍待测试。

平台“长期记忆”目前关闭。它会总结一般对话，不符合本项目只记明确偏好的约束；当前角色定义仅承诺会话内使用明确偏好，跨会话持久化待实现受控的四项偏好存储后再开启。
