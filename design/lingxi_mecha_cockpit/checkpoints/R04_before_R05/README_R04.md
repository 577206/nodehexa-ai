# 灵犀驾驶舱 · FreeCAD 分件项目

主模型使用 FreeCAD 实体几何。Blender 导入同一批 CAD 零件的网格，用于材质、灯光、视角和外形评审。

**当前版本：R04 外形评审样机，尚不可整套打印装配，也尚未完成参考图复原。** 电路板、镜头、电池、手机及磁吸连接器的适配尺寸仍未实测。R03 留作历史，并提供 R04 暂时沿用的底座与接触盒几何。

## 当前文件

- CAD 总装：`03_assembly/Lingxi_Cockpit_R04.FCStd`
- CAD 源脚本：`06_tools/build_r04.py`
- 独立零件：`02_parts/R04/`，各文件夹含 `.FCStd`、`_review.stl` 和 `part.json`
- 零件清单：`03_assembly/manifest_R04.json`
- Blender 评审场景：`03_assembly/Lingxi_Cockpit_R04_review.blend`
- 最新外形图与说明：`04_review/iteration_04c/`
- 本轮决策与状态：`01_specification/revision_R04.json`

R04 共 **103 件**：57 件按不透明打印件分类、12 件透明舱罩片、2 件导光件、32 件外购件占位。这是分件清单，不是已验证的采购或打印清单。

## 固定目录

```text
lingxi_mecha_cockpit/
├── 00_reference/
│   ├── original/approved_concept.png       用户确认的原始外观
│   ├── original/user_markup_2026-10-29.png 用户本轮标注
│   └── turnaround/generated_six_views.png 辅助六视图，隐藏结构属推演
├── 01_specification/
│   ├── revision_R04.json                  当前决策及验证状态
│   └── parameters.json                    R03 历史参数
├── 02_parts/
│   ├── R04/P01_…/ … P59_…/               当前壳体、装甲、托架与底座
│   ├── R04/G01_…/ … G12_…/               当前透明分片
│   ├── R04/H01_…/ … H32_…/               当前外购件占位
│   └── P01_…/ …                           R03 历史零件，保留原结构
├── 03_assembly/
│   ├── Lingxi_Cockpit_R04.FCStd
│   ├── Lingxi_Cockpit_R04_review.blend
│   ├── manifest_R04.json
│   ├── interference_R04.json
│   └── Lingxi_Cockpit_R03.*                历史总装及底座来源
├── 04_review/iteration_01/ … iteration_04c/
├── 05_print_release/                      通过装配及试打印验证后才发布
├── 06_tools/build_r04.py
│             check_r04.py
│             render_r04.py
└── checkpoints/                           历史检查点
```

R03 的 STEP、落床 STL 等历史文件不代表 R04 已发布。当前 R04 的 `_review.stl` 保留总装坐标，用于评审；尚未发布完整 STEP 或经过排版、公差校准的打印包。

## 对本轮反馈的处理

| 用户反馈 | R04 已落实 | 仍需整改 |
|---|---|---|
| 形状、精细度与参考差距大 | 重做收紧下缘与后扫前额；护轨跟随舱罩；侧甲随壳面收缩，分出轴盖下嵌甲；14 处外装甲实体倒角有效应用 | 肩颊仍有大块简化平面，装甲比例、接缝、细部密度与参考有差距；未判定外形完成 |
| 前透明舱罩折面太少 | 改为 4 个纵向坡段 × 中央及左右翼面，共 12 片；每边内退 0.16 mm，名义拼缝约 0.32 mm；加入真实横向接缝承托条 | 折线和边框层次仍需对照；透明片的固定方法、实际缝宽及材料加工未验证 |
| 格栅应位于两侧 | 左右侧前部布置独立灰框、黑百叶、橙色斜鳍片；主壳开出对应侧孔，模块前移至 Y=-29 mm | 格栅与护轨、主壳的衔接及装配避让尚未清理完 |

## 当前分件

| 编号 | 结构 |
|---|---|
| P01–P02 | 上下主壳，电子器件与电池固定结构待定尺 |
| P03–P06、G01–G12 | 舱罩承托框、接缝扣与 12 片透明件 |
| P07–P09 | 灯眼内托板与两条导光件 |
| P10–P13 | 前侧护轨、镜头橙框与内衬 |
| P14–P19 | 左右侧格栅，每侧三件 |
| P20–P23 | 橙色肩架与灰色压甲 |
| P24–P31、P58–P59 | 随壳侧甲、检修盖及轴盖下方独立嵌甲 |
| P32–P37 | 两侧圆形轴盖、橙圈与中心盖 |
| P38–P44 | 后肩导流罩、顶板、凹槽内衬和提手 |
| P45–P51 | 手机托架及后部检修件 |
| P52–P57 | 接触盒、独立桌面底座环和四脚，沿用并调整 R03 样机 |
| H01–H32 | 镜头、螺钉头、磁铁及触点占位，尺寸不等于实物 |

## 参数与源文件

R04 是**脚本驱动的 CAD 实体模型**。当前轮廓、分件和位置参数写在 `06_tools/build_r04.py`；`revision_R04.json` 记录决策与评审状态，不直接驱动建模。`parameters.json` 与 `build_cad.py` 属于 R03 历史流程。

主壳基准包络约 108 × 93 × 78 mm，属于未实测的造型假设；外装甲、镜头框、托架及底座另占空间。FCStd 保存真实实体和零件身份，当前不提供每个零件的完整草图约束和原生特征历史。

## 重建与检查

在本项目目录运行；保留 R03 总装，因为脚本从中读取暂用底座与接触盒：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd 06_tools/build_r04.py
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd 06_tools/check_r04.py
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python 06_tools/render_r04.py -- --all
```

渲染脚本使用独立后台场景，并覆盖当前 R04 的 `.blend` 和 `iteration_04c` 输出。每次改动实体后应顺序重跑三步，让总装、网格、渲染和报告保持同版。

## 最新检查结果

| 检查 | 当前结果 | 含义 |
|---|---|---|
| CAD 分件 | 103/103 件有效、单实体 | 单件几何检查通过，不代表装配通过 |
| 实体倒角 | 14/19 个候选应用成功；13 件 0.45 mm、1 件 0.25 mm | 未通过的候选保持原实体；前护轨因网格质量退回无倒角 |
| Blender render QA | 0 错误、27 警告 | 仍含面方向、退化面、重复顶点及接触面等警告 |
| 非硬件件装配交叠 | 76 对，体积阈值 0.05 mm³ | 尚未通过装配检查；硬件不计入该报告 |

对应原始报告：`03_assembly/manifest_R04.json`、`03_assembly/interference_R04.json`、`04_review/iteration_04c/blender_qa.json`。零网格错误不能替代装配间隙、薄壁、强度、装配路径和电子器件适配验证。

## 发布前仍需完成

1. 继续核对正视、侧视和三分之四视图的轮廓、装甲比例与细节；通过用户外形评审。
2. 逐项处理交叠、网格警告和附件紧固结构，明确透明片及饰件的装拆路径。
3. 实测 XJWB03、LJX40、BF3901 转接板、镜头、扬声器、手机、电池及磁吸连接器，再设计内部支架、走线、USB/充电口和天线净空。
4. 完成公差试片、薄壁检查和分件试装，验证桌面抗倾倒与机器人顶部安装，再编制打印与编号装配说明。

通过上述检查前，`05_print_release/` 不接收 R04 整套打印包。
