# BF3901 → 千问视觉：当前接入状态

2026-10-26：BF3901 已通过 I²C 识别为 `0x3901`。首次接线时官方帧校验失败，临时诊断照片有条纹与偏色；重新接线后官方帧校验通过，连续取到可辨认的新画面。诊断用的校验绕过已从源码撤回。当前板上运行摄像头诊断固件，云端语音暂未同时运行；镜头还没有对准人，因此**现在不应自动播报坐姿提醒**。实时预览见 [CAMERA_PREVIEW.md](CAMERA_PREVIEW.md)。

`vision_qwen.py` 已按用户提供的千问AI平台 OpenAI 兼容地址接入 `qwen3.8-flash`。它在本机读取单张 JPEG，用 HTTPS 发送给千问，让模型用自然语言描述画面中可见的内容，不做坐姿分类或生成提醒。它不会向灵机 Agent、机器人或小程序自动发送消息。

首次真实调用已成功：旧诊断照片的结构化识别结果为画质 `poor`、姿势 `unknown`。重新接线后，摄像头已能持续取到清晰新画面；当前预览页按钮只请求通用画面描述。

## 本机试通模型

打开本目录的 `.env.local`，把 `DASHSCOPE_API_KEY=REPLACE_WITH_YOUR_KEY` 这一行的占位值换成你所用平台颁发的 API Key。默认地址是你提供的 `https://cn-beijing.maas.qianwenaiapi.com/compatible-mode/v1`，模型是 `qwen3.8-flash`；密钥需与这个服务及地域匹配。`.env.local` 已被 Git 忽略并设为仅当前用户可读写。不要把 Key 发到聊天、写入固件或提交 Git。

在本目录的 macOS 终端执行：

```bash
python3 vision_qwen.py captures/latest.jpg --dry-run
python3 vision_qwen.py captures/latest.jpg
```

`--dry-run` 只校验本地 JPEG 和请求配置，不联网，也不会计费。第二次命令会把指定照片上传到你配置的模型服务并产生调用费用，输出自然语言画面描述。`captures/latest.jpg` 是首次接线时的失真诊断画面；想看当前内容，请打开实时预览页点“描述当前画面”。若你的密钥对应另一地址或视觉模型，可在 `.env.local` 修改 `DASHSCOPE_BASE_URL` 和 `DASHSCOPE_VISION_MODEL`；调用程序仅允许已核对的千问AI平台北京地址或阿里云兼容地址。

## 端到端接入还差两步

1. 用当前清晰画面验证通用描述；随后编译、烧录并验证云端语音 + 摄像头合并固件。当前诊断固件可以串口取图，但云端语音 Agent 未运行。
2. 视觉事件到语音 Agent：官方 SDK 的 `agent_app_user_corpus()` 可把应用提供的文字送给云端 Agent 发声，但需要在板端实现受控的“视觉观察”入口。不要把千问 API Key 放在 ESP32 固件里；正式架构应由可信的本机/服务端中继调用千问，只把经过验证、限频后的结果发给板端。接入后需确认多帧一致、用户显式偏好和提醒冷却时间，再允许发声或动作。

接口参考：[千问AI平台视觉理解](https://platform.qianwenai.com/docs/developer-guides/multimodal/vision)、[Qwen3.8-Flash](https://platform.qianwenai.com/docs/developer-guides/getting-started/latest-model)。
