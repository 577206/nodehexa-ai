# R06 外形与分件评审记录

本页图像来自实际 FreeCAD 零件经 Blender 渲染。没有用 AI 概念图替换建模结果。当前尚未精确复原概念参考，未发布整套打印包。

## 实际修改

- 重做灰色舱罩护轨：五边截面形成真实倒角面，并前移到主壳前方；上下护轨分别保留为独立件。
- 过渡颊甲沿前侧转角延伸到肩下，增加浅刻线、孔位及贴面螺钉；下边沿抬到格栅屋脊以上，避免遮挡橙鳍。
- 橙肩甲厚度3.5→2.35 mm，灰压甲2.6→1.75 mm，降低叠层的突兀程度。
- 12片透明舱罩保持分件；新增0.8 mm纵筋，三件接缝扣包含双销座、盲孔、中央槽和连接舌。
- 手机背托顶面名义Z95→Z86，上沿收肩，整体Y前移8 mm，保留10°后倾；缩短连接肋。
- 打孔前颊顶部尖角收平，与下段护轨分开。
- 为格栅、舱罩、镜头内衬、侧甲、手机下托和后检修模块设计接收避让。每次裁切保留完整结果，只有有效单实体才接受，不丢弃碎片。
- 后检修框/手机下托与上壳保留0.20 mm名义间隙。上护轨接收轮廓XY外扩0.30 mm、Z端部延长0.20 mm，实测最小法向间距约0.1733 mm；这些是评审参数，不是已经试装的打印公差。

## 迭代依据

06a发现颊甲遮挡格栅，06b抬高颊甲并补舱罩内部结构；06c把被主壳遮挡的护轨前移，并完成相应接收槽与网格修复。R05及a/b中间图保留，原始R06c未通过的检查留在checkpoints/R06c_before_rail_seat，最终结论以本目录及重新读取的CAD检查为准。

## 最终检查

- 125/125件有效单实体；保存后重新读取核对通过，清单体积与分件文件齐全。
- 分类：69件不透明打印件类别、2件导光件、12片透明片、42件硬件占位。分类不代表已验证打印/采购清单。
- Blender render QA：0错误、33警告，116,886三角形；逐件统计见blender_qa.json。
- 非硬件件交叠大于0.05 mm³：R05的64对降至0对。硬件螺钉/磁铁占位不包含在该交叠统计中。
- 已查看斜前、正面、侧面、后部、舱罩内部、分色和线框视图。07_canopy_structure仅为结构检查临时隐藏透明片，正常外观图保留透明片。

## 网格修复与接受范围

扣件原有微型圆孔相切、极小三角面已从CAD源修改：连接舌收窄，销座/孔使用明确多边形边界，去掉0.01 mm细唇边。P46/P47全边倒角无法通过网格检查，已从CAD取消，保留源轮廓折角。

P62/P63在CAD源中为镜像件；P63独立三角化出现两对自重叠，评审场景改用P62的镜像三角化。双向顶点/三角中心采样最大表面差约0.0161 mm，小于0.065 mm网格弦差；单件print QA通过。该采样不是严格Hausdorff距离证明。CAD实体和原始review STL未用此方法修改，细节见mirror_tessellation_qa.json。

以下警告仅为本轮外观评审接受，不构成打印许可：

1. 少量近距顶点来自CAD曲面三角化，当前没有开边或非流形错误；不扩大焊接距离，以免破坏薄边。
2. 包角颊甲的极小三角面，以及沿用R03桌面脚的小面积面，仍需打印网格专门处理；桌面底座不在主外观渲染中显示。
3. 独立闭合零件的相向接触面保留，以维持分件；没有为了减少面数把甲板或底座合并。
4. 最低点Z=-18.5 mm来自桌面底座的装配坐标；没有做打印落床或排版。

完整警告列表：

- SM_P03_canopy_frame: duplicate verts=5 loose verts=0
- SM_P60_front_cheek_shield1: duplicate verts=1 loose verts=0
- SM_P61_front_cheek_shield-1: duplicate verts=1 loose verts=0
- SM_P68_wraparound_cheek_bridge1: degenerate faces=3 zero-len edges=0
- SM_P69_wraparound_cheek_bridge-1: degenerate faces=3 zero-len edges=0
- SM_P31_service_11: duplicate verts=2 loose verts=0
- SM_P30_service_1-1: duplicate verts=2 loose verts=0
- SM_P48_phone_shelf: duplicate verts=2 loose verts=0
- SM_P56_legacy_P38: degenerate faces=10 zero-len edges=0
- SM_P56_legacy_P38: duplicate verts=2 loose verts=0
- SM_P57_legacy_P39: degenerate faces=10 zero-len edges=0
- SM_P57_legacy_P39: duplicate verts=2 loose verts=0
- hidden back-to-back faces: SM_P01_lower_shell<->SM_P52_legacy_P34 (3153 pairs) - delete to save tris
- hidden back-to-back faces: SM_P01_lower_shell<->SM_P49_rear_service_frame (2706 pairs) - delete to save tris
- hidden back-to-back faces: SM_P62_upper_service_inset1<->SM_P68_wraparound_cheek_bridge1 (962 pairs) - delete to save tris
- hidden back-to-back faces: SM_P63_upper_service_inset-1<->SM_P69_wraparound_cheek_bridge-1 (961 pairs) - delete to save tris
- hidden back-to-back faces: SM_P02_upper_shell<->SM_P40_roof_hatch (593 pairs) - delete to save tris
- hidden back-to-back faces: SM_P62_upper_service_inset1<->SM_P24_side_upper_armor1 (580 pairs) - delete to save tris
- hidden back-to-back faces: SM_P63_upper_service_inset-1<->SM_P26_side_upper_armor-1 (579 pairs) - delete to save tris
- hidden back-to-back faces: SM_P71_side_service_backing-1<->SM_P28_service_0-1 (540 pairs) - delete to save tris
- hidden back-to-back faces: SM_P70_side_service_backing1<->SM_P29_service_01 (540 pairs) - delete to save tris
- hidden back-to-back faces: SM_P27_side_lower_armor-1<->SM_P71_side_service_backing-1 (433 pairs) - delete to save tris
- hidden back-to-back faces: SM_P25_side_lower_armor1<->SM_P70_side_service_backing1 (433 pairs) - delete to save tris
- hidden back-to-back faces: SM_P24_side_upper_armor1<->SM_P70_side_service_backing1 (392 pairs) - delete to save tris
- hidden back-to-back faces: SM_P26_side_upper_armor-1<->SM_P71_side_service_backing-1 (392 pairs) - delete to save tris
- hidden back-to-back faces: SM_P70_side_service_backing1<->SM_P31_service_11 (364 pairs) - delete to save tris
- hidden back-to-back faces: SM_P71_side_service_backing-1<->SM_P30_service_1-1 (364 pairs) - delete to save tris
- hidden back-to-back faces: SM_P58_hinge_lower_infill1<->SM_P70_side_service_backing1 (311 pairs) - delete to save tris
- hidden back-to-back faces: SM_P59_hinge_lower_infill-1<->SM_P71_side_service_backing-1 (311 pairs) - delete to save tris
- hidden back-to-back faces: SM_P40_roof_hatch<->SM_H21_screw_21 (249 pairs) - delete to save tris
- hidden back-to-back faces: SM_P40_roof_hatch<->SM_H23_screw_23 (248 pairs) - delete to save tris
- hidden back-to-back faces: SM_P40_roof_hatch<->SM_H24_screw_24 (244 pairs) - delete to save tris
- asset lowest point z=-0.0185 (not resting on ground plane z=0)

## 仍需完成

参考图的曲面比例、肩颊装甲细节密度及隐蔽结构仍有差异，不能称为完全一样。PCB、镜头、扬声器、电池、手机及磁吸连接器未实测；内部支架、紧固件选型、透明片固定、拆装路径、薄壁、强度和打印公差尚未验证。零交叠只证明当前名义实体不互穿。
