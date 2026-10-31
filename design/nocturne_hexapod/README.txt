NOCTURNE 六足机甲工程改版

已确认：机身左右总加宽30mm，各侧15mm；黑红蜘蛛风；红色饰件不发光；主板+语音板组合约120×50mm。

当前交付范围：第一批4件工程草模，不是完整机器人打印包。
1. N001 上框架，134.809×104.343×3mm。
2. N111 小腿正面甲片，39.5×65.048×4.2mm，其中原接口与芯板厚3mm。
3–4. N112 左/右红色饰条，各约8.182×34.602×0.55mm。

outputs/parts_DRAFT_NOT_FULL_KIT/：每件独立文件夹，STEP+STL+尺寸JSON。
outputs/drawings/first_draft_comparison.png：真实CAD和尺寸对照。
source/model.py：可重建的参数化CAD源代码。
parameters.yaml：当前参数；spec/current.yaml：要求、坐标与待核实项。
spec/part_register.json：所有原零件及新零件进度，pending表示未完成。
validation/first_draft_checks.json：当前实体、接口区域和相交检查证据。

检查结果不等于实物试装通过。仍缺整腿运动包络、红色饰条固定验证、配套底架及侧墙、其余腿部甲片和驾驶舱工程件。
头部只有板件组合约120×50mm的粗尺寸，尚缺最高点/连接器/喇叭/摄像头转接板/电池/磁吸触点规格。
上框架不能单独与原宽度底架混装。STL单位按mm导入。
