# 仓库地图

入口文档保留在根目录，可编译工程与 CAD 工程保持原路径，避免影响脚本和已有链接。

| 区域 | 内容 | 当前入口 |
| --- | --- | --- |
| `firmware/src/`、`firmware/data/` | 运动板逻辑和板载控制网页 | [运动板接口](../FIRMWARE_REFERENCE.md) |
| `firmware/lingji-xjwb03/` | 灵机板应用、电脑端服务与厂商 SDK | [语音视觉工程](../firmware/lingji-xjwb03/README.md) |
| `design/lingxi_head_simplified/` | 头部、OLED 支架与打印导出 | [头部说明](../design/lingxi_head_simplified/brief.md) |
| `design/lingxi_magnetic_bowl_mount/` | 机身连接用磁吸碗底 | [设计说明](../design/lingxi_magnetic_bowl_mount/brief.md) |
| `design/nocturne_hexapod/` | 腿部配色、零件和加宽机身 | [设计说明](../design/nocturne_hexapod/README.txt) |
| `design/robot_theater/` | 动作展示与整机可视化验证 | [展示记录](../design/robot_theater/README.md) |
| `mechanism/`、`hardware/` | 底盘结构和电路参考 | [结构件](../mechanism/README.md)、[硬件](../hardware/README.md) |
| `resource/` | 导入的底盘图片和参考素材 | [来源说明](../NOTICE.md) |
| `workspace/` | 辅助开发工具 | [工具说明](../workspace/pathTool/README.md) |

`design/` 内的 `checkpoints/`、`review/cache/`、`validation/` 分别是历史、预览缓存和检查记录；`outputs/` 是导出件。不同修订号的打印件应按相应工程的清单区分。

来源与权利信息见 [NOTICE.md](../NOTICE.md)；导入源码及 SDK 自带的许可证保留在原位置。
