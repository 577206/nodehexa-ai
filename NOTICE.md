# 来源与许可说明

本仓库是灵犀整机的持续开发工作区，并非全部代码、结构件和素材的原创首发。原项目的宣传链接不再作为首页或设备网页页脚；来源、版权和许可记录在这里保留。

| 范围 | 来源及记录 |
| --- | --- |
| 六足运动控制基线、部分结构件与参考图片 | [NodeHexa](https://github.com/ViolinLee/NodeHexa)。导入时的 README 标注 **Copyright © 2024 ViolinLee. Licensed under GPL-3.0.**；相关源码标注与历史保留。 |
| 更早的运动学参考 | [hexapod-v2-7697](https://github.com/SmallpTsai/hexapod-v2-7697) 与 [PiHexa18](https://github.com/ViolinLee/PiHexa18)，这是导入项目原说明列出的来源。 |
| 灵机一动 XJWB03 厂商 SDK | [官方开发者仓库](https://gitee.com/xj-open/ljyd_xjwb03_agent_public_developer)，本地导入记录见 [语音板说明](firmware/lingji-xjwb03/README.md)。`firmware/lingji-xjwb03/sdk/` 内含 ESP-IDF、QUMIOS、驱动和其他组件，各目录自带的许可证、声明及版权标头保留。 |
| 其他 Arduino 库 | `firmware/lib/` 中的第三方库保留其自带的许可证和版权信息。 |
| 灵犀新增工作 | 对话与视觉工作台、两板通信集成、运动安全策略、头部/碗底/腿部再设计及验证记录见对应的 `firmware/` 和 `design/` 工程。 |

仓库根目录此前没有统一 `LICENSE` 文件，所以旧首页的 GPL 徽标链接是断开的。这里保留导入项目的许可声明，不把厂商 SDK 或其他库误标为同一种许可证；对外发布前仍需逐项核对适用许可。

Git 提交历史与上游仓库信息也是来源记录。整理目录或改写介绍不改变已有文件的原始归属。
