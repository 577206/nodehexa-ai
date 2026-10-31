NOCTURNE EDGE50 白蓝工程草模

当前模型：review/index.html；可重建源代码：source/model.py。
上板 134.809×124.343×3mm；中央开口及两处中央固定孔原位保留。
下板（普通/18650-2S二选一）130.343×128.343×9mm；原中央结构保留，腿根向外各移25mm。9mm是最大厚度，新增边框基板3mm。
下板原内部座位暂留作原结构的一部分，腿部使用外侧安装座。
验证：validation/edge_frame_checks.json。
下板重建：先用FreeCAD执行source/build_edge_bottom_freecad.py，再运行build_review.py。下板BRep保持原STL表面精度，不等于解析CAD恢复。
旧outputs/step及parts_DRAFT_NOT_FULL_KIT未重新导出，不能用于当前EDGE50方案。
尚未验证：整腿活动干涉、侧墙配套、实物装配和承载。

本次更新：两种下板均删除内侧六个旧座的凸起，保留 3 mm 底板、中央开口和外侧六个腿座。
