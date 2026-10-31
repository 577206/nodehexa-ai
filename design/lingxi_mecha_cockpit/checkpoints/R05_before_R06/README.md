# 灵犀驾驶舱 · FreeCAD 分件项目

**当前版本：R05 外形评审样机，尚未完成参考图复原，也未通过整套打印装配验证。** FreeCAD 实体和构建脚本是建模依据；Blender 导入同一批 CAD 网格，用于外形、材质与多角度评审。硬件尺寸仍未实测。

## 当前文件

| 内容 | 路径 |
|---|---|
| CAD 总装 | `03_assembly/Lingxi_Cockpit_R05.FCStd` |
| Blender 场景 | `03_assembly/Lingxi_Cockpit_R05_review.blend` |
| 独立分件 | `02_parts/R05/`，各件有 FCStd、review STL、part.json |
| 构建脚本 | `06_tools/build_r05.py`、`cad_edge_break_r05.py` |
| 零件与验证清单 | `03_assembly/manifest_R05.json`、`interference_R05.json` |
| 最新渲染和说明 | `04_review/iteration_05c/` |
| 新旧对照页 | `04_review/comparison_R04_R05.html` |
| 决策与参数记录 | `01_specification/revision_R05.json` |

R05 共 121 件：69 件不透明打印件分类、2 件导光件、12 件透明片、38 件外购件占位。编号 P01–P71、G01–G12，以及含保留空号的 H 系列。**分类清单不等于已经验证的打印或采购清单。**

## 本轮变化

主体收窄、手机架降低后倾、眼睛与镜头上移、前颊拆分、侧甲贴合壳面并增加真实分缝和检修条、侧格栅改斜楔并缩小、镜筒增加凹槽，以及有效外沿倒角。原 R04 总装、分件、渲染与 README 快照均保留在原版本目录和 `checkpoints/R04_before_R05/`。

## 目录约定

`00_reference/` 为外观参考，`01_specification/` 为决策，`02_parts/` 按版本及零件分文件夹，`03_assembly/` 为总装，`04_review/` 为真实模型渲染和检查，`05_print_release/` 仅接收以后通过验证的打印包，`06_tools/` 为建模与检查源码，`checkpoints/` 留存迭代状态。

R03 总装仍是暂用桌面底座和接触盒的来源，不能删除。R03 的 STEP/落床 STL 不代表 R05 发布。R05 的 `_review.stl` 保留总装坐标。

## 验证与限制

121/121 件 CAD 有效单实体；最终 render QA 0 错误、31 警告；103,360 三角形；23 件实体倒角。仍有 64 对非硬件件体积交叠。警告逐类接受理由、失败倒角回退和剩余外形差距见 `04_review/iteration_05c/REVIEW_NOTES.md`。

当前 FCStd 保存真实实体和零件身份，参数通过 Python 脚本修改；不提供每件完整原生草图约束历史。电子器件固定、装配间隙、薄壁、强度、透明片固定与公差尚未验证。

## 重建

在项目目录依次执行，检查 BUILD_COMPLETE 后再渲染：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd 06_tools/build_r05.py
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd 06_tools/check_r05.py
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python 06_tools/render_r05.py
```

修改前先保留版本检查点。脚本会覆盖当前 R05 产物；`revision_R05.json` 是决策记录，实际参数在构建脚本中。`parameters.json` 属于 R03 历史流程。
