# 灵犀驾驶舱 · FreeCAD 分件项目

**当前版本：R06 外形与分件评审样机。尚未精确复原参考图，也未批准整套打印。** FreeCAD实体与构建脚本是几何依据；Blender用于同源CAD网格的材质、多角度和网格评审。硬件尺寸仍未实测。

## 当前文件

| 内容 | 路径 |
|---|---|
| CAD总装 | `03_assembly/Lingxi_Cockpit_R06.FCStd` |
| Blender评审场景 | `03_assembly/Lingxi_Cockpit_R06_review.blend` |
| 独立零件 | `02_parts/R06/`：各件FCStd、review STL、part.json |
| 新旧对照页 | `04_review/comparison_R05_R06.html` |
| 全角度渲染、内部结构图、检查说明 | `04_review/iteration_06c/` |
| 零件与独立验证 | `03_assembly/manifest_R06.json`、`interference_R06.json` |
| 接收槽证据 | `interface_resolution_R06.json`、`rear_clearance_R06.json`、`rail_clearance_R06.json`（均在03_assembly） |
| 决策与参数记录 | `01_specification/revision_R06.json` |
| 构建/渲染源码 | `06_tools/build_r06.py`、`render_r06.py`及其导入的R06辅助模块 |

R06共125件：69件不透明打印件类别、2件导光件、12片透明片、42件硬件占位。编号仍为P01–P71、G01–G12和保留空号的H系列。类别不等于已验证的打印或采购清单。

## 本轮修改

重建包角颊甲、降低肩部叠层、让灰色舱罩护轨完整外露；补实体纵筋、双销座接缝扣和孔位；手机托架降低、收肩、前移；修正格栅遮挡并增加对应接收槽。全部结构继续分件，旧R05总装、分件与渲染保留。

## 检查结果和边界

125/125件CAD有效单实体，保存后独立读取核对通过。非硬件零件大于0.05 mm³的交叠为0对（R05为64对）。Blender render QA为0错误、33警告，共116,886三角形。警告的逐类接受理由、三角化修复证据与剩余差距见`04_review/iteration_06c/REVIEW_NOTES.md`。

零交叠不代表已可打印装配。电子器件定位、壁厚、紧固、透明片固定、装配路径和公差尚未验证。CAD保存真实实体和零件身份，通过Python脚本调整参数；不提供每件完整原生草图约束历史。review STL是总装坐标下的CAD网格，Blender评审包含保守网格清理及有偏差检查的P63对称三角化。

## 目录约定

`00_reference/`外观参考；`01_specification/`参数与决策；`02_parts/`按版本/零件分文件夹；`03_assembly/`总装；`04_review/`真实渲染与检查；`05_print_release/`仅接收以后通过验证的打印包；`06_tools/`构建与检查脚本；`checkpoints/`保留迭代。

R03总装仍是暂用桌面底座和接触盒的来源，不可删除。历史STEP/落床STL不代表R06发布。本轮没有输出整套打印包。

## 重建

在项目目录依次执行；检查BUILD_COMPLETE后再渲染：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd 06_tools/build_r06.py
/Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd 06_tools/check_r06.py
/Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup --python 06_tools/render_r06.py -- --all
python3 06_tools/summarize_r06.py
```

修改前保留版本检查点。脚本覆盖当前R06产物，既有R05不变。`revision_R06.json`记录设计决策，实际参数在Python源码；`parameters.json`属于R03历史流程。
