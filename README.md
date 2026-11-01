# 灵犀机甲 · AI 桌宠与六足机器人

[English](README_EN.md)

灵犀由可拆卸的语音视觉头部和六足运动底盘组成。头部负责唤醒、对话、按需看画面与双 OLED 表情；底盘负责预设动作、电池状态与运动安全。两者通过 UART 联调，磁吸结构与完整装配继续按实物试装推进。

这是我们持续开发的整机项目。它集成了现有六足运动控制代码、灵机 XJWB03 SDK 和我们新增的交互服务、连接协议、外壳与装配设计。各部分来源见 [来源说明](NOTICE.md)。

## 从哪里开始

| 想做的事 | 入口 |
| --- | --- |
| 理解产品目标和两板分工 | [产品需求](PRODUCT_REQUIREMENTS.md) |
| 启动对话、视觉和控制工作台 | [千问直连与本地服务](firmware/lingji-xjwb03/QWEN_DIRECT.md) |
| 构建运动板固件 | [运动板接口](FIRMWARE_REFERENCE.md)、[台架模式](firmware/BENCH_MODE.md) |
| 查看两板接线 | [UART 三线连接](firmware/lingji-xjwb03/ROBOT_LINK_WIRING.md) |
| 打印和组装头部 | [头部 CAD 工程](design/lingxi_head_simplified/brief.md) |
| 查看机身与腿部 | [结构件说明](mechanism/README.md)、[加宽底盘工程](design/nocturne_hexapod/README.txt) |
| 浏览全部目录 | [仓库地图](docs/PROJECT_MAP.md) |

## 当前结构

```text
firmware/
  src/                       运动板固件
  data/                      运动板网页
  lingji-xjwb03/             语音视觉板、工作台和 SDK
design/
  lingxi_head_simplified/     头部、透明盖、装饰和 OLED 支架
  lingxi_magnetic_bowl_mount/ 磁吸碗底
  nocturne_hexapod/          腿部及加宽机身
  robot_theater/             动作与展示验证
mechanism/                   底盘结构件与装配参考
hardware/                    电路设计资料
docs/                        仓库地图
```

## 本地联调

在 `firmware/lingji-xjwb03/` 运行 `./lingji.sh omni`，浏览器打开 `http://127.0.0.1:8765/`。这启动电脑侧工作台；语音板和运动板的构建、烧录、供电及网络配置分别见对应文档。

运动板的 PlatformIO 项目位于 `firmware/`。无电池、只用 USB 联调时使用[台架模式](firmware/BENCH_MODE.md)；实体运动前先确认供电、校准和机体架空。打印文件是试装版，CAD 检查不等于实物装配验证。

本仓库保留导入代码、结构件和 SDK 所附的来源及许可信息，详见 [NOTICE.md](NOTICE.md)。
