import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {Presentation,PresentationFile} from '@oai/artifact-tool';
const DIR=path.dirname(fileURLToPath(import.meta.url)), WORK=path.dirname(DIR), A=path.join(WORK,'assets/v2');
const SKILL='/Users/ashley/.codex/plugins/cache/openai-primary-runtime/presentations/26.1029.11837/skills/presentations';
const PY='/Users/ashley/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3';
process.env.RUNTIME_NODE_MODULES='/Users/ashley/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules';
const FINAL=path.join(WORK,'output-v2/灵犀-黑红机库-产品展示-V2-长期陪伴版.pptx');
const p=Presentation.create({slideSize:{width:1280,height:720}});
const C={bg:'#101010',red:'#f04737',white:'#f5f2ec',muted:'#b4afaa'};
const FONT='Hiragino Sans GB';
function text(s,value,x,y,w,h,size=24,color=C.white,bold=false){
 const t=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 t.text=value;t.text.style={fontSize:size,typeface:FONT,color,bold,autoFit:'none',insets:0,wrap:'square',verticalAlignment:'top'};return t;
}
async function image(s,name,x,y,w,h,fit='contain'){
 const file=name.startsWith('/')?name:path.join(A,name);
 return s.images.add({blob:new Uint8Array(await fs.readFile(file)),contentType:file.endsWith('.jpg')?'image/jpeg':'image/png',alt:path.basename(file),fit,position:{left:x,top:y,width:w,height:h}});
}
async function slide(n,{hangar=false}={}){
 const s=p.slides.add();s.background.fill=C.bg;
 if(hangar)await image(s,'hangar-aigc.png',0,0,1280,720,'cover');
 if([3,6,8].includes(n))s.shapes.add({geometry:'rect',position:{left:0,top:0,width:1280,height:720},fill:'rgba(12,12,12,0.62)',line:{fill:'none',width:0}});
 text(s,'灵犀',56,32,150,42,28,C.white,true);
 text(s,String(n).padStart(2,'0'),1180,38,44,28,14,C.muted);
 return s;
}
function notes(s,body){s.speakerNotes.text=body+'\n视觉：AIGC 生成空机库背景，机甲本体使用本项目已确认模型与参照。背景生成提示词与资产来源见 design/lingxi_product/assets/v2/asset-manifest.json。';}
{
 const s=await slide(1,{hangar:true});
 text(s,'灵犀',56,160,470,190,144,C.white,true);
 text(s,'陪你一生。',62,370,530,65,45,C.white,true);
 text(s,'十岁学习，二十牛马；\n三十谋划，四十喝茶。',64,477,475,90,23,'#d8cfc6');
 await image(s,'head-hero.png',575,55,650,650);
 notes(s,'产品定位：长期陪伴的桌面机甲伙伴，陪你长大，也陪你变老。R06 驾驶舱当前冻结网格，非整机已装配照片。双眼图案为概念覆盖，不代表已测量的实际显示区。');
}
{
 const s=await slide(2);
 text(s,'你的声音，\n它的回应',60,128,600,145,54,C.white,true);
 const rows=[['语音对话','聊生活、拆解目标，也可以多轮追问。'],['按需视觉','需要时看一眼，不持续上传视频。'],['动作与表情','用姿态和眼神，为回应补上一点温度。']];
 rows.forEach((r,i)=>{text(s,r[0],64,320+i*104,400,36,25,C.white,true);text(s,r[1],64,362+i*104,470,42,19,C.muted);});
 await image(s,'head-front.png',620,100,620,620);
 notes(s,'保留原版完整产品能力中的语音、视觉、动作与表情。人格与偏好见第四页，安全与控制见第七页。视觉按需调用，不宣称情绪识别。');
}
{
 const s=await slide(3,{hangar:true});
 text(s,'长期陪伴，陪你一生',60,130,1160,88,54,C.white,true);
 text(s,'十岁学习，二十牛马；三十谋划，四十喝茶。',64,235,860,44,25,'#ddd3ca');
 const rows=[['陪你学习','一起讨论问题，\n也保护你的好奇心。','学习与探索'],['陪你度过牛马生活','听你下班后的吐槽，\n也陪你整理明天的目标。','工作与倾诉'],['陪你出谋划策','梳理难题、讨论选择，\n决定仍由你做。','思考与规划'],['陪你养生喝茶','聊健康生活，喝茶放松，\n继续折腾喜欢的事。','日常与兴趣']];
 rows.forEach((r,i)=>{let x=64+i*304;text(s,['10 岁','20 岁','30 岁','40 岁以后'][i],x,350,278,66,39,C.red);text(s,r[0],x,443,278,60,i===1?25:28,C.white,true);text(s,r[1],x,509,278,80,20,'#ddd3ca');text(s,r[2],x,630,276,28,16,C.muted);});
 notes(s,'用户确认的长期陪伴理念：十岁学习、二十岁工作倾诉、三十岁出谋划策、四十岁以后养生喝茶。年龄用于讲述人生阶段，不构成角色限制。健康生活指日常交流与兴趣陪伴。');
}
{
 const s=await slide(4);
 await image(s,'head-side.png',0,110,650,600);
 text(s,'熟悉的陪伴，\n跟随你的变化',680,128,555,150,48,C.white,true);
 text(s,'称呼、语气与风格',684,360,520,44,29,C.red,true);
 text(s,'延续你认可的称呼与偏好。\n不同阶段，回应不同的需要。',684,423,500,90,23,C.muted);
 text(s,'偏好可以修改，也可以清除。',684,584,520,42,20,C.white);
 notes(s,'人格与偏好来自现有产品内容：称呼、表达风格与互动频率由用户设置。侧视渲染来自当前 R06 冻结网格。');
}
{
 const s=await slide(5);
 text(s,'动作、眼睛、台词，一起表演',60,123,1160,88,48,C.white,true);
 const root=path.resolve(WORK,'../robot_theater/actions_r03');
 const items=[['hold_that_compliment','head_0055.png','被夸后努力绷住','想装淡定，眼睛却先投降。'],['gossip_radar','head_0060.png','八卦雷达上线','刚说不爱听，已经凑近了。'],['compliment_receipt','head_0064.png','夸奖签收','一本正经地，把夸奖存起来。']];
 for(let i=0;i<items.length;i++){const r=items[i],x=48+i*410;await image(s,path.join(root,r[0],'renders',r[1]),x,232,385,330);text(s,r[2],x+12,585,375,40,25,C.white,true);text(s,r[3],x+12,638,375,36,18,C.muted);}
 notes(s,'三种独特反应保留既定动作与台词。图像来自已确认 R03 概念表演渲染。无独立颈部，头部朝向跟随机身目标姿态。双 OLED 表情图案为概念覆盖。');
}
{
 const s=await slide(6,{hangar:true});
 text(s,'25 秒机甲小剧场',60,126,1160,88,54,C.white,true);
 text(s,'同一条时间轴，协调动作、双眼与配音。',64,225,1100,46,24,'#ddd3ca');
 const root=path.resolve(WORK,'../robot_theater/actions_r03');
 await image(s,path.join(root,'compliment_receipt/renders/head_0034.png'),52,296,530,380);
 [['09 秒','被夸后努力绷住'],['08 秒','八卦雷达上线'],['08 秒','夸奖签收']].forEach((r,i)=>{let y=330+i*106;text(s,r[0],650,y,160,60,41,C.red);text(s,r[1],840,y+8,390,46,27,C.white,true);});
 text(s,'软件预演，真实腿部动态装配待校准',648,653,590,30,17,C.muted);
 notes(s,'25 秒由 9 + 8 + 8 秒组成。视频保留在本地网页动作区，不嵌入 PPT。真实腿部不使用通用杆件骨架替代，装配动画仍待校准。视频路径：design/robot_theater/actions_r03/unique_actions_reel.mp4。');
}
{
 const s=await slide(7);
 text(s,'互动控制台',60,124,1000,80,58,C.white,true);
 text(s,'表演、眼神与固定动作，都有清楚的入口。',64,222,1080,44,24,C.muted);
 await image(s,'console-preview.png',60,300,1160,328,'contain');
 text(s,'停止并禁用始终可用。离线时显示真实连接状态。',64,653,1130,36,20,C.white);
 notes(s,'现有接口与行为保留：三段表演、五种眼睛控制、四个固定动作、运动开关、停止按钮。截图为本地离线状态，不伪造机器人在线。当前展示不触发任何真实机器人动作。');
}
{
 const s=await slide(8,{hangar:true});
 text(s,'API 连接能力，陪伴继续生长',60,122,1160,90,48,C.white,true);
 text(s,'已接入对话与视觉 API，以下为陪伴场景的扩展方向',64,227,1120,40,23,C.red);
 const rows=[['主动坐姿提醒','连续确认状态后再提醒'],['专注与休息','按你的时间安排提醒'],['陪伴日报','根据认可的对话生成回顾'],['自定义表演','有限时长的具名预设'],['天气与日程','配置服务并单独授权'],['远程陪伴','认证与加密完成后接入']];
 rows.forEach((r,i)=>{let x=64+(i%3)*407,y=350+Math.floor(i/3)*168;text(s,r[0],x,y,370,48,29,C.white,true);text(s,r[1],x,y+64,370,58,20,'#d8cfc6');});
 notes(s,'全部为规划，尚未上线。天气、日程和远程能力需要相应授权与服务配置。当前控制接口仅面向可信局域网，不将规划能力写作已交付功能。');
}
{
 const s=await slide(9);
 text(s,'真实结构，逐步验证',60,120,1160,84,52,C.white,true);
 await image(s,'chassis-reference.png',60,250,660,410,'contain');
 text(s,'软件预演',786,270,430,50,30,C.red,true);
 text(s,'动作、眼睛与配音已有编排。\n模型与零件有明确来源。',786,337,430,100,22,C.muted);
 text(s,'实机待验收',786,476,430,50,30,C.white,true);
 text(s,'完整装配、腿部碰撞、舵机载荷，\n以及 OLED 显示与实体同步。',786,543,430,100,22,C.muted);
 text(s,'红黑底盘形态参照，非 R06 与 EDGE50 完整装配验收图',64,672,1100,28,16,C.muted);
 notes(s,'底盘使用已确认红黑形态参照原图。当前 R06 驾驶舱与 EDGE50 的完整装配尚待校准，不能把参照图当成现版本整机已装配的证据。不复述未重新核实的测试或固件编译计数。');
}
{
 const s=await slide(10,{hangar:true});
 text(s,'灵犀',60,150,460,180,132,C.white,true);
 text(s,'赛博永生',64,360,560,90,60,C.white,true);
 text(s,'硬件可以更换，熟悉的陪伴继续。',64,480,590,50,25,'#d8cfc6');
 text(s,'让共同经历的记忆与相处方式，\n跨越硬件更替而延续。',64,562,590,90,22,C.muted);
 text(s,'长期陪伴的产品愿景',64,674,590,30,16,C.red);
 await image(s,'head-detail.png',674,125,570,570);
 notes(s,'结束页展示经用户确认的赛博永生愿景：硬件可更换，记忆与熟悉的相处方式延续。长期记忆的迁移、查看与删除由用户掌握，随功能建设逐步实现，不承诺人的意识永生。AIGC 仅生成环境背景。');
}
await fs.mkdir(path.join(DIR,'slides'),{recursive:true});
for(let i=0;i<p.slides.items.length;i++){
 const png=await p.export({slide:p.slides.items[i],format:'png',scale:1});
 await fs.writeFile(path.join(DIR,'slides',`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await png.arrayBuffer()));
 console.log(`RENDERED ${i+1}`);
}
const candidate=path.join(DIR,'candidate.pptx');await(await PresentationFile.exportPptx(p)).save(candidate);
const {finalizePresentation}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')).href);
const result=await finalizePresentation({workspaceDir:WORK,candidatePath:candidate,finalPath:FINAL,pythonExecutable:PY,integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],explicitTotalSlideCount:10,fontPolicy:{basis:'design',families:[FONT]},verifyArtifactToolImport:true,receiptPath:path.join(DIR,'validation-companion.json')});
console.log(JSON.stringify(result));
