# Lingxi Mecha · AI Companion and Hexapod Robot

[中文](README.md)

Lingxi combines a detachable voice-and-vision head with a six-legged motion chassis. The head handles wake-up, conversation, on-demand visual descriptions, and two OLED eyes. The chassis handles preset motions, battery status, and motion safety. UART integration has been tested; the magnetic interface and final assembly still require physical fit checks.

This is our ongoing integrated robot project. It combines an existing hexapod motion-control baseline and the XJWB03 SDK with our interaction service, board-to-board protocol, enclosure, and assembly work. See [NOTICE.md](NOTICE.md) for provenance and license information.

## Start here

| Task | Document |
| --- | --- |
| Product goals and board responsibilities | [Product requirements](PRODUCT_REQUIREMENTS.md) |
| Voice, vision, and local control workstation | [Qwen direct mode](firmware/lingji-xjwb03/QWEN_DIRECT.md) |
| Motion-board firmware | [Firmware interface](FIRMWARE_REFERENCE.md), [bench mode](firmware/BENCH_MODE.md) |
| Wiring between the boards | [UART wiring](firmware/lingji-xjwb03/ROBOT_LINK_WIRING.md) |
| Print and assemble the head | [Head CAD](design/lingxi_head_simplified/brief.md) |
| Chassis and legs | [Mechanism](mechanism/README.md), [widened chassis](design/nocturne_hexapod/README.txt) |
| Navigate the repository | [Project map](docs/PROJECT_MAP.md) |

The workstation starts with `./lingji.sh omni` in `firmware/lingji-xjwb03/` and serves `http://127.0.0.1:8765/`. Build and flashing instructions for each board are in the linked documents. Printed parts are fit-test prototypes; digital checks do not establish physical fit.

The repository retains source and license records for imported code, models, and SDK files in [NOTICE.md](NOTICE.md).
