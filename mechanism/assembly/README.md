# NodeHexa 装配模型

> **校正提示（2026-10-28）**：本目录现有 `NodeHexa-Whole-Robot*` 是早期参考拼装，腿部姿态以及躯干中 `BodyCenter`、`BodyBackWall` 的位置没有得到官方装配约束验证，**不要用于打印或扩展件设计**。躯干的已确认结构与尺寸请先看 [`TORSO_STRUCTURE.md`](TORSO_STRUCTURE.md)。

本目录用于核对仓库 STL 的装配关系，并准备后续添加摄像头、语音板和自制外壳的躯干基准。

## 当前应该打开哪个文件

先查看 `NodeHexa-Body-Parts-Overview.png` 和 `TORSO_STRUCTURE.md`。等短立板的位置通过实物确认后，再生成可供 FreeCAD 打开的 `NodeHexa-Torso.FCStd`。

`NodeHexa-Whole-Robot*` 和 `NodeHexa-Whole-Robot-preview.png` 仅作为错误定位记录保留，当前不要使用。

## 装配内容

- 1 套机身框架
- 6 条腿（左前、左中、左后、右前、右中、右后）
- 每条腿 3 个舵机占位体，共 18 个
- 1 个机身电子板占位体
- 仓库中可替换的电池底板与薄型中层板保留在隐藏分组中

## 重要说明

仓库原始文件只有 STL 网格，没有官方整机装配约束、舵机 CAD 或完整尺寸表。因此当前模型是根据仓库照片和零件外形生成的“参考装配”，适合观察、规划和设计扩展件，但还不能直接当成尺寸已经验证的打印总装。

准备设计自制组件前，应实测并校准：

- 机身安装孔孔距与孔径
- 顶板可用安装区域
- 舵机真实外形和输出轴中心位置
- 各关节零位、转动方向和运动干涉
- 摄像头、语音板、电池和走线所需空间

## 重新生成

- `build_nodehexa_assembly.FCMacro`：在 FreeCAD 中运行，生成分组装配与预览图。文件顶部集中放置了机身高度、六个髋关节位置和腿部角度等参数。
- `build_nodehexa_combined_stl.py`：运行后生成单网格 STL，便于兼容性预览。

不要修改 `../hexapod/` 中的仓库原始 STL；后续校准只修改本目录中的装配参数。
