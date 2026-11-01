const path = require('path');
const fs = require('fs');
const JSZip = require('jszip');
const pptxgen = require('pptxgenjs');

const ROOT = path.resolve(__dirname, '../..');
const asset = (p) => path.join(ROOT, p);
const ASSETS = {
  robot: asset('design/red_black_print_release_20261031/approved_color_reference.png'),
  headViews: asset('design/robot_theater/aligned_r02/current_head_views.png'),
  storyboard: asset('design/robot_theater/actions_r03/three_actions_storyboard.png'),
  hold: asset('design/robot_theater/actions_r03/hold_that_compliment/cover.png'),
  gossip: asset('design/robot_theater/actions_r03/gossip_radar/cover.png'),
  receipt: asset('design/robot_theater/actions_r03/compliment_receipt/cover.png'),
};

const C = {
  silver: 'E7EAED',
  graphite: '24282D',
  white: 'F8FAFB',
  orange: 'E56B23',
  iron: '68727C',
  teal: '7DD3C7',
  black: '121518',
  line: 'CBD1D6',
  pale: 'F0F3F5',
  darkCard: '30353B',
};
const FONT = { head: 'Cambria', body: 'Calibri', cn: 'Arial' };
const SW = 13.333;
const SH = 7.5;

const pptx = new pptxgen();
pptx.layout = 'LAYOUT_WIDE';
pptx.author = 'NodeHexa AI';
pptx.company = 'NodeHexa AI';
pptx.subject = '灵犀：桌面上的机甲伙伴';
pptx.title = '灵犀｜你的桌面机甲伙伴';
pptx.lang = 'zh-CN';
pptx.theme = {
  headFontFace: FONT.head,
  bodyFontFace: FONT.body,
  lang: 'zh-CN',
};
pptx.margin = 0;
pptx.creator = 'NodeHexa AI';
pptx.keywords = '灵犀, 六足机器人, 桌面伙伴, OLED, 机甲';
pptx.defineSlideMaster({
  title: 'BLANK',
  background: { color: C.white },
  objects: [],
});

function txt(slide, text, x, y, w, h, opts = {}) {
  slide.addText(text, {
    x, y, w, h,
    margin: 0,
    fontFace: opts.fontFace || FONT.cn,
    fontSize: opts.fontSize || 14,
    color: opts.color || C.graphite,
    bold: opts.bold || false,
    italic: opts.italic || false,
    align: opts.align || 'left',
    valign: opts.valign || 'mid',
    breakLine: false,
    fit: opts.fit || 'shrink',
    paraSpaceAfter: 0,
    lineSpacingMultiple: opts.lineSpacingMultiple || 1,
    charSpacing: opts.charSpacing || 0,
    rotate: opts.rotate || 0,
    isTextBox: true,
  });
}

function rect(slide, x, y, w, h, fill, line = null, radius = 0) {
  slide.addShape(radius ? pptx.ShapeType.roundRect : pptx.ShapeType.rect, {
    x, y, w, h,
    fill: { color: fill },
    line: line ? { color: line, width: 0.8 } : { color: fill, transparency: 100 },
    rectRadius: radius || undefined,
  });
}

function line(slide, x, y, w, h, color = C.line, width = 1, dash = 'solid') {
  slide.addShape(pptx.ShapeType.line, {
    x, y, w, h,
    line: { color, width, dashType: dash, beginArrowType: 'none', endArrowType: 'none' },
  });
}

const PATTERNS = {
  flat: [
    '00000000', '00000000', '00000000', '11111111',
    '11111111', '00000000', '00000000', '00000000',
  ],
  radar: [
    '00111100', '01000010', '10000001', '10011001',
    '10011001', '10000001', '01000010', '00111100',
  ],
  check: [
    '00000001', '00000010', '00000100', '10001000',
    '11010000', '01100000', '00100000', '00000000',
  ],
  square: [
    '00000000', '00111100', '00111100', '00111100',
    '00111100', '00111100', '00000000', '00000000',
  ],
};

function pixelEye(slide, x, y, size, pattern, pixelColor, plateColor = C.black) {
  rect(slide, x, y, size, size, plateColor, C.iron, 0.04);
  const cell = size / 10;
  const offset = cell;
  const rows = PATTERNS[pattern];
  rows.forEach((row, r) => {
    [...row].forEach((bit, c) => {
      if (bit === '1') {
        rect(slide, x + offset + c * cell, y + offset + r * cell, cell * 0.9, cell * 0.9, pixelColor);
      }
    });
  });
}

function gaze(slide, x, y, size, left = 'flat', right = 'flat', pixelColor = C.teal) {
  pixelEye(slide, x, y, size, left, pixelColor);
  pixelEye(slide, x + size * 1.18, y, size, right, pixelColor);
}

function header(slide, num, kicker, title, dark = false) {
  const main = dark ? C.white : C.graphite;
  const muted = dark ? C.silver : C.iron;
  txt(slide, kicker.toUpperCase(), 0.58, 0.34, 5.4, 0.22, {
    fontFace: FONT.body, fontSize: 9, color: dark ? C.teal : C.orange,
    bold: true, charSpacing: 1.8,
  });
  txt(slide, title, 0.56, 0.67, 10.8, 0.55, {
    fontSize: 34, color: main, bold: true,
  });
  gaze(slide, 11.8, 0.38, 0.34, 'flat', 'flat', dark ? C.teal : C.orange);
  txt(slide, String(num).padStart(2, '0'), 12.55, 0.42, 0.25, 0.22, {
    fontFace: FONT.head, fontSize: 10, color: muted, align: 'right',
  });
}

function footer(slide, text, dark = false) {
  txt(slide, text, 0.58, 7.12, 10.8, 0.16, {
    fontFace: FONT.body, fontSize: 7.5, color: dark ? C.iron : C.iron,
    charSpacing: 0.5,
  });
}

function addImageCrop(slide, image, x, y, w, h, crop) {
  const sourceW = w / crop.w;
  const sourceH = h / crop.h;
  slide.addImage({
    path: image, x, y, w: sourceW, h: sourceH,
    sizing: { type: 'crop', x: crop.x * sourceW, y: crop.y * sourceH, w, h },
  });
}

function tag(slide, textValue, x, y, w, dark = false, accent = false) {
  rect(slide, x, y, w, 0.32, accent ? C.orange : (dark ? C.darkCard : C.silver));
  txt(slide, textValue, x + 0.1, y + 0.02, w - 0.2, 0.27, {
    fontFace: FONT.body, fontSize: 9, bold: true,
    color: accent ? C.white : (dark ? C.silver : C.graphite),
    align: 'center', charSpacing: 0.5,
  });
}

// 01 — Cover
{
  const slide = pptx.addSlide('BLANK');
  slide.background = { color: C.graphite };
  rect(slide, 7.35, 0, 5.983, 7.5, C.silver);
  slide.addImage({ path: ASSETS.robot, x: 7.48, y: 1.22, w: 5.7, h: 4.275 });
  txt(slide, 'LINGXI / 6-LEG DESKTOP COMPANION', 0.62, 0.58, 5.9, 0.26, {
    fontFace: FONT.body, fontSize: 10, color: C.teal, bold: true, charSpacing: 1.6,
  });
  txt(slide, '灵犀', 0.56, 1.35, 5.7, 1.0, {
    fontSize: 58, color: C.white, bold: true,
  });
  txt(slide, '你的桌面机甲伙伴', 0.61, 2.52, 6.25, 0.56, {
    fontSize: 28, color: C.white, bold: true,
  });
  txt(slide, '语音对话、按需视觉、人格与偏好，\n配合动作与表情，提供克制的日常陪伴。', 0.62, 3.28, 5.95, 0.76, {
    fontSize: 16, color: C.silver,
  });
  gaze(slide, 0.64, 4.48, 0.72, 'flat', 'square', C.teal);
  txt(slide, '需要时清晰回应。\n不需要时保持安静。', 2.45, 4.47, 3.9, 0.84, {
    fontSize: 16, color: C.silver, lineSpacingMultiple: 1.05,
  });
  tag(slide, 'VOICE · VISION · PERSONALITY', 0.62, 6.36, 3.15, true);
  txt(slide, 'PRODUCT SHOWCASE / 2026', 0.62, 6.89, 3.4, 0.2, {
    fontFace: FONT.body, fontSize: 8, color: C.iron, charSpacing: 1.2,
  });
  txt(slide, '01', 12.35, 6.9, 0.4, 0.25, {
    fontFace: FONT.head, fontSize: 11, color: C.graphite, align: 'right',
  });
  slide.addNotes('封面整机素材：design/red_black_print_release_20261031/approved_color_reference.png。灵犀定位为桌面机甲伙伴，核心为语音对话、按需视觉、人格与偏好、动作与表情。');
}

// 02 — Complete product form
{
  const slide = pptx.addSlide('BLANK');
  slide.background = { color: C.white };
  header(slide, 2, '01 / COMPLETE PRODUCT FORM', '完整产品形态');

  const modules = [
    ['01', '语音对话', '对话、问答与语音指令', 0.58, 1.52, C.orange],
    ['02', '按需视觉', '需要时查看物体与桌面信息', 0.58, 3.24, C.teal],
    ['03', '人格与偏好', '称呼、表达风格与互动频率', 0.58, 4.96, C.graphite],
    ['04', '动作与表情', '六足姿态、双 OLED 与音频同步', 9.52, 1.52, C.orange],
    ['05', '安全与 API', '停止优先、软件限位、接口集成', 9.52, 3.24, C.teal],
  ];
  modules.forEach((m, i) => {
    rect(slide, m[3], m[4], 3.22, 1.38, i === 1 ? C.silver : C.pale, C.line, 0.04);
    txt(slide, m[0], m[3] + 0.22, m[4] + 0.2, 0.42, 0.3, {
      fontFace: FONT.head, fontSize: 15, color: m[5] === C.graphite ? C.iron : m[5], bold: true,
    });
    txt(slide, m[1], m[3] + 0.76, m[4] + 0.17, 2.15, 0.36, { fontSize: 18, bold: true });
    txt(slide, m[2], m[3] + 0.22, m[4] + 0.76, 2.76, 0.38, { fontSize: 10.5, color: C.iron });
  });

  rect(slide, 4.24, 1.48, 4.86, 5.14, C.graphite, null, 0.05);
  addImageCrop(slide, ASSETS.headViews, 5.1, 1.76, 3.14, 3.14, { x: 0.0, y: 0.12, w: 0.42, h: 0.70 });
  txt(slide, 'LINGXI SYSTEM', 4.62, 5.12, 3.9, 0.26, {
    fontFace: FONT.body, fontSize: 10, color: C.teal, bold: true, align: 'center', charSpacing: 1.4,
  });
  gaze(slide, 4.78, 5.57, 0.48, 'flat', 'square', C.white);
  txt(slide, '按需输入，统一调度，清晰反馈', 5.98, 5.65, 2.55, 0.36, {
    fontSize: 13, color: C.white, bold: true,
  });
  rect(slide, 9.52, 4.96, 3.22, 1.38, C.graphite, C.graphite, 0.04);
  txt(slide, '边界始终存在', 9.76, 5.16, 2.6, 0.3, { fontSize: 15, color: C.orange, bold: true });
  txt(slide, '视觉按需启用\n不宣称情绪识别\n停止指令始终可用', 9.76, 5.58, 2.58, 0.62, { fontSize: 10.5, color: C.silver });
  footer(slide, 'VOICE + VISION + PERSONALITY + MOTION + SAFETY API');
  slide.addNotes('完整产品形态由语音、视觉、人格与偏好、动作与表情、安全与 API 构成。视觉按需，停止优先，不宣称情绪识别。');
}

// 03 — Daily companionship scenes
{
  const slide = pptx.addSlide('BLANK');
  slide.background = { color: C.white };
  header(slide, 3, '02 / DAILY SCENES', '日常陪伴，嵌入工作与休息之间');

  const scenes = [
    { no: '01', title: '开始工作', status: '语音 + 偏好', body: '用语音确认今天的互动方式，\n保持既定称呼与表达风格。', note: '当前能力：语音对话、人格与偏好', planned: false },
    { no: '02', title: '需要看一眼', status: '按需视觉', body: '主动请求灵犀查看物体或桌面信息，\n视觉仅在需要时启用。', note: '当前能力：按需调用视觉', planned: false },
    { no: '03', title: '互动放松', status: '对话 + 彩蛋', body: '短暂语音交流，配合动作与表情；\n三段表演作为可选互动彩蛋。', note: '当前能力：对话、动作与表情', planned: false },
    { no: '04', title: '休息与回顾', status: '计划项 / 尚未上线', body: '规划专注休息提醒与陪伴日报，\n按需回顾互动摘要。', note: '计划能力：专注休息、陪伴日报', planned: true },
  ];
  scenes.forEach((scene, i) => {
    const x = 0.58 + (i % 2) * 6.18;
    const y = 1.5 + Math.floor(i / 2) * 2.62;
    rect(slide, x, y, 5.82, 2.28, scene.planned ? C.graphite : (i === 1 ? C.silver : C.pale), scene.planned ? C.orange : C.line, 0.04);
    rect(slide, x + 0.24, y + 0.25, 0.68, 0.68, scene.planned ? C.darkCard : C.graphite, null, 0.04);
    txt(slide, scene.no, x + 0.24, y + 0.41, 0.68, 0.3, {
      fontFace: FONT.head, fontSize: 16, color: scene.planned ? C.orange : C.teal, bold: true, align: 'center',
    });
    txt(slide, scene.title, x + 1.16, y + 0.25, 2.25, 0.38, {
      fontSize: 20, color: scene.planned ? C.white : C.graphite, bold: true,
    });
    txt(slide, scene.status, x + 3.32, y + 0.31, 2.1, 0.26, {
      fontFace: FONT.body, fontSize: 9.5, color: scene.planned ? C.orange : C.iron, bold: true, align: 'right',
    });
    txt(slide, scene.body, x + 1.16, y + 0.82, 4.18, 0.66, {
      fontSize: 12, color: scene.planned ? C.silver : C.iron,
    });
    txt(slide, scene.note, x + 1.16, y + 1.72, 4.18, 0.28, {
      fontSize: 10.5, color: scene.planned ? C.orange : C.graphite, bold: true,
    });
  });
  footer(slide, 'CURRENT INTERACTIONS + CLEARLY MARKED FUTURE SCENES');
  slide.addNotes('日常场景：开始工作、需要看一眼、互动放松为当前能力组合；休息与回顾中的专注休息、陪伴日报为计划项，尚未上线。');
}

// 04 — Daily companionship capabilities
{
  const slide = pptx.addSlide('BLANK');
  slide.background = { color: C.white };
  header(slide, 4, '03 / DAILY COMPANIONSHIP', '三种能力，进入同一段日常');

  const cards = [
    { no: '01', title: '语音对话', body: '对话、问答与语音指令，\n通过声音完成自然交互。', tags: '对话  /  指令  /  反馈', status: 'VOICE', color: C.orange },
    { no: '02', title: '按需视觉', body: '需要时调用视觉能力，\n辅助查看物体与桌面信息。', tags: '按需启用  /  不持续窥看', status: 'ON DEMAND', color: C.teal },
    { no: '03', title: '人格与偏好', body: '设置称呼、表达风格与互动频率，\n让日常回应保持一致。', tags: '称呼  /  风格  /  频率', status: 'PREFERENCE', color: C.graphite },
  ];
  cards.forEach((card, i) => {
    const x = 0.58 + i * 4.22;
    rect(slide, x, 1.5, 3.82, 5.12, i === 1 ? C.silver : C.pale, C.line, 0.04);
    txt(slide, card.status, x + 0.24, 1.74, 2.3, 0.22, {
      fontFace: FONT.body, fontSize: 9, color: card.color, bold: true, charSpacing: 1.2,
    });
    rect(slide, x + 0.22, 2.15, 3.38, 1.64, C.graphite, null, 0.04);
    if (i === 0) {
      const bars = [0.28, 0.62, 0.94, 0.48, 1.16, 0.72, 0.36, 0.82, 0.5];
      bars.forEach((h, j) => rect(slide, x + 0.58 + j * 0.31, 2.97 - h / 2, 0.12, h, j === 4 ? C.orange : C.teal));
    } else if (i === 1) {
      gaze(slide, x + 0.86, 2.4, 0.88, 'square', 'square', C.white);
    } else {
      [2.52, 2.94, 3.36].forEach((yy, j) => {
        line(slide, x + 0.62, yy, 2.5, 0, C.iron, 1.4);
        slide.addShape(pptx.ShapeType.ellipse, {
          x: x + [1.0, 2.12, 1.48][j], y: yy - 0.11, w: 0.22, h: 0.22,
          fill: { color: j === 1 ? C.orange : C.teal }, line: { color: C.graphite, width: 0.5 },
        });
      });
    }
    txt(slide, card.no, x + 0.24, 4.08, 0.45, 0.3, {
      fontFace: FONT.head, fontSize: 15, color: C.orange, bold: true,
    });
    txt(slide, card.title, x + 0.8, 4.0, 2.65, 0.42, { fontSize: 20, bold: true });
    txt(slide, card.body, x + 0.24, 4.68, 3.3, 0.7, { fontSize: 12.5, color: C.iron });
    txt(slide, card.tags, x + 0.24, 5.72, 3.3, 0.28, { fontSize: 10.5, color: C.graphite, bold: true });
    if (i === 1) txt(slide, '视觉用于按需感知，不用于推断情绪。', x + 0.24, 6.12, 3.3, 0.24, { fontSize: 9.5, color: C.iron });
  });
  footer(slide, 'VOICE + ON-DEMAND VISION + PERSONALITY PREFERENCES');
  slide.addNotes('三种日常陪伴能力：语音对话、按需视觉、人格与偏好。视觉按需调用，不宣称持续情绪识别。');
}

// 05 — Motion and expression
{
  const slide = pptx.addSlide('BLANK');
  slide.background = { color: C.white };
  header(slide, 5, '04 / MOTION + EXPRESSION', '动作与表情，让陪伴更自然');

  rect(slide, 0.58, 1.48, 4.92, 3.52, C.silver);
  addImageCrop(slide, ASSETS.headViews, 1.34, 1.62, 3.4, 3.12, { x: 0.0, y: 0.12, w: 0.42, h: 0.70 });
  txt(slide, 'REAL CAD / 双 OLED / 六足姿态', 0.84, 4.65, 3.9, 0.22, {
    fontFace: FONT.body, fontSize: 9, color: C.iron, bold: true, charSpacing: 0.7,
  });

  const rows = [
    ['01', '姿态', '转向、点头与靠近，为语音回应补充清晰的身体反馈。'],
    ['02', '表情', '双 OLED 用简洁像素图案呈现待机、倾听、回应等状态。'],
    ['03', '同步', '语音、动作与表情由统一调度协调，避免反馈彼此脱节。'],
  ];
  rows.forEach((r, i) => {
    const y = 1.5 + i * 1.18;
    rect(slide, 5.92, y, 6.78, 0.98, i === 1 ? C.silver : C.pale, C.line, 0.04);
    txt(slide, r[0], 6.17, y + 0.27, 0.42, 0.28, {
      fontFace: FONT.head, fontSize: 15, color: i === 0 ? C.orange : C.iron, bold: true,
    });
    txt(slide, r[1], 6.82, y + 0.18, 0.85, 0.32, { fontSize: 17, bold: true });
    txt(slide, r[2], 7.88, y + 0.15, 4.48, 0.56, { fontSize: 11.5, color: C.iron });
  });

  txt(slide, '互动彩蛋 / 非产品核心', 0.62, 5.36, 2.1, 0.28, { fontSize: 12, color: C.orange, bold: true });
  txt(slide, '三段预编排表演，用于展示动作与表情的组合能力。', 0.62, 5.82, 2.25, 0.62, { fontSize: 10.5, color: C.iron });
  const eggs = [
    { img: ASSETS.hold, title: '夸奖回应', sub: '被夸后努力绷住' },
    { img: ASSETS.gossip, title: '八卦雷达', sub: '转向与专注图案' },
    { img: ASSETS.receipt, title: '夸奖签收', sub: '点头与勾选图案' },
  ];
  eggs.forEach((egg, i) => {
    const x = 3.16 + i * 3.2;
    rect(slide, x, 5.22, 2.96, 1.34, i === 1 ? C.silver : C.pale, C.line, 0.04);
    addImageCrop(slide, egg.img, x + 0.1, 5.32, 1.02, 1.02, { x: 0.02, y: 0.13, w: 0.47, h: 0.69 });
    txt(slide, egg.title, x + 1.28, 5.48, 1.45, 0.28, { fontSize: 14, bold: true });
    txt(slide, egg.sub, x + 1.28, 5.91, 1.48, 0.3, { fontSize: 9.5, color: C.iron });
  });
  footer(slide, 'BODY + OLED + VOICE / EASTER EGGS ARE OPTIONAL');
  slide.addNotes('动作与表情服务于自然陪伴。三段表演仅作为互动彩蛋：被夸后努力绷住、八卦雷达上线、夸奖签收，不作为产品核心。');
}

// 06 — Static action storyboard
{
  const slide = pptx.addSlide('BLANK');
  slide.background = { color: C.graphite };
  header(slide, 6, '05 / STATIC ACTION STORYBOARD', '25 秒静态动作分镜', true);
  txt(slide, '三段预编排动作，以静态分镜呈现姿态与双 OLED 的变化。', 0.6, 1.32, 7.6, 0.3, {
    fontSize: 13, color: C.silver,
  });
  txt(slide, '09 + 08 + 08 = 25 SEC', 9.55, 1.32, 3.1, 0.28, {
    fontFace: FONT.head, fontSize: 13, color: C.orange, bold: true, align: 'right', charSpacing: 0.8,
  });

  rect(slide, 0.58, 1.82, 5.25, 4.82, C.silver, null, 0.04);
  addImageCrop(slide, ASSETS.storyboard, 0.72, 1.96, 4.97, 4.25, { x: 0.01, y: 0.075, w: 0.98, h: 0.86 });
  txt(slide, 'STATIC STORYBOARD / 三组动作，每组三个静态状态', 0.82, 6.34, 4.68, 0.22, {
    fontFace: FONT.body, fontSize: 8.5, color: C.iron, bold: true, charSpacing: 0.4,
  });

  const data = [
    { t: '09 s', title: '夸奖回应', seq: '语音回应  /  姿态变化  /  双眼图案', note: '被夸后努力绷住：三段静态姿态。', color: C.orange },
    { t: '08 s', title: '八卦雷达', seq: '转向  /  倾听  /  专注图案', note: '八卦雷达上线：转向与专注图案。', color: C.teal },
    { t: '08 s', title: '夸奖签收', seq: '点头  /  勾选  /  结束姿态', note: '夸奖签收：点头与勾选图案。', color: C.silver },
  ];
  data.forEach((d, i) => {
    const y = 1.82 + i * 1.63;
    rect(slide, 6.18, y, 6.52, 1.42, C.darkCard, C.iron, 0.04);
    txt(slide, d.t, 6.52, y + 0.22, 0.78, 0.34, {
      fontFace: FONT.head, fontSize: 19, color: d.color, bold: true,
    });
    txt(slide, d.title, 7.55, y + 0.18, 2.3, 0.36, { fontSize: 18, color: C.white, bold: true });
    txt(slide, `0${i + 1}`, 11.72, y + 0.22, 0.52, 0.28, {
      fontFace: FONT.head, fontSize: 13, color: d.color, bold: true, align: 'right',
    });
    txt(slide, d.seq, 7.55, y + 0.66, 4.62, 0.28, { fontSize: 11, color: d.color, bold: true });
    txt(slide, d.note, 7.55, y + 1.06, 4.62, 0.24, { fontSize: 10.5, color: C.silver });
  });
  footer(slide, 'STATIC FRAMES / PRE-SCRIPTED ACTIONS / 25 SEC', true);
  slide.addNotes('第 6 页为静态三段动作分镜，时间轴 9+8+8 秒，仅使用真实 CAD 动作分镜图与文字说明。');
}

// 07 — Real capability console
{
  const slide = pptx.addSlide('BLANK');
  slide.background = { color: C.white };
  header(slide, 7, '06 / CAPABILITY CONSOLE', '真实功能控制台');

  const modules = [
    ['01', '语音对话', 'READY', '对话、问答与语音指令', C.orange],
    ['02', '按需视觉', 'ON DEMAND', '仅在需要时调用视觉', C.teal],
    ['03', '人格与偏好', 'CUSTOM', '称呼、风格与互动频率', C.graphite],
  ];
  modules.forEach((m, i) => {
    const x = 0.58 + i * 4.12;
    rect(slide, x, 1.48, 3.78, 1.5, i === 1 ? C.silver : C.pale, C.line, 0.04);
    txt(slide, m[0], x + 0.22, 1.7, 0.42, 0.28, {
      fontFace: FONT.head, fontSize: 15, color: m[4] === C.graphite ? C.iron : m[4], bold: true,
    });
    txt(slide, m[2], x + 1.88, 1.72, 1.58, 0.22, {
      fontFace: FONT.body, fontSize: 8.5, color: m[4] === C.graphite ? C.iron : m[4], bold: true, align: 'right', charSpacing: 0.8,
    });
    txt(slide, m[1], x + 0.22, 2.08, 2.9, 0.34, { fontSize: 18, bold: true });
    txt(slide, m[3], x + 0.22, 2.52, 3.2, 0.26, { fontSize: 11, color: C.iron });
  });

  rect(slide, 0.58, 3.3, 5.82, 1.28, C.silver, C.line, 0.04);
  txt(slide, '04', 0.82, 3.55, 0.42, 0.3, { fontFace: FONT.head, fontSize: 15, color: C.orange, bold: true });
  txt(slide, '动作与表情', 1.48, 3.48, 1.8, 0.34, { fontSize: 18, bold: true });
  txt(slide, 'SYNC', 4.98, 3.52, 0.98, 0.22, { fontFace: FONT.body, fontSize: 8.5, color: C.teal, bold: true, align: 'right' });
  txt(slide, '六足姿态、双 OLED 与音频统一调度', 1.48, 3.98, 4.36, 0.28, { fontSize: 11, color: C.iron });

  rect(slide, 6.76, 3.3, 5.94, 1.28, C.graphite, C.graphite, 0.04);
  txt(slide, '05', 7.0, 3.55, 0.42, 0.3, { fontFace: FONT.head, fontSize: 15, color: C.orange, bold: true });
  txt(slide, '停止与安全', 7.66, 3.48, 1.8, 0.34, { fontSize: 18, color: C.white, bold: true });
  txt(slide, 'STOP PRIORITY', 10.92, 3.52, 1.36, 0.22, { fontFace: FONT.body, fontSize: 8.5, color: C.orange, bold: true, align: 'right' });
  txt(slide, '停止指令优先；软件限位与 API 控制', 7.66, 3.98, 4.36, 0.28, { fontSize: 11, color: C.silver });

  rect(slide, 0.58, 4.96, 12.12, 1.58, C.graphite, null, 0.04);
  txt(slide, '语音 / 视觉输入', 0.9, 5.26, 1.62, 0.34, { fontSize: 15, color: C.white, bold: true, align: 'center' });
  txt(slide, '→', 2.59, 5.26, 0.38, 0.34, { fontSize: 19, color: C.orange, align: 'center' });
  txt(slide, '偏好与统一调度', 3.02, 5.26, 1.85, 0.34, { fontSize: 15, color: C.white, bold: true, align: 'center' });
  txt(slide, '→', 4.94, 5.26, 0.38, 0.34, { fontSize: 19, color: C.orange, align: 'center' });
  const outs = [['动作', 5.45], ['表情', 6.62], ['音频', 7.79]];
  outs.forEach(([label, ox]) => {
    rect(slide, ox, 5.16, 0.98, 0.55, C.darkCard, C.iron, 0.03);
    txt(slide, label, ox, 5.27, 0.98, 0.28, { fontSize: 13, color: C.teal, bold: true, align: 'center' });
  });
  txt(slide, '控制边界', 9.3, 5.13, 1.2, 0.25, { fontSize: 10, color: C.orange, bold: true });
  txt(slide, '随时停止；视觉按需；\n实机验收状态见技术页。', 9.3, 5.47, 2.92, 0.62, {
    fontSize: 11.5, color: C.silver,
  });
  footer(slide, 'REAL CAPABILITIES / EXPLICIT CONTROLS AND SAFETY BOUNDARIES');
  slide.addNotes('真实功能控制台：语音对话、按需视觉、人格与偏好、动作与表情、停止与安全。停止优先，视觉按需，支持 API 控制。');
}

// 08 — API expansion roadmap
{
  const slide = pptx.addSlide('BLANK');
  slide.background = { color: C.white };
  header(slide, 8, '07 / API EXPANSION ROADMAP', 'API 可扩展规划');
  txt(slide, '以下均为规划能力，不属于当前已上线或已验收功能。', 0.6, 1.28, 7.2, 0.26, {
    fontSize: 12, color: C.orange, bold: true,
  });

  const plans = [
    ['主动坐姿', '尚未上线', '按交互情境调整身体姿态'],
    ['专注休息', '尚未上线', '专注计时与休息提醒'],
    ['陪伴日报', '尚未上线', '汇总互动摘要与偏好回顾'],
    ['自定义表演', '尚未上线', '通过 API 编排动作、表情与音频'],
    ['天气日程', '需授权 · 尚未上线', '访问天气或日程前明示授权'],
    ['安全远程', '需授权 · 尚未上线', '远程控制需鉴权、限权与停止'],
  ];
  plans.forEach((p, i) => {
    const x = 0.58 + (i % 3) * 4.22;
    const y = 1.72 + Math.floor(i / 3) * 1.68;
    rect(slide, x, y, 3.82, 1.42, i >= 4 ? C.silver : C.pale, C.line, 0.04);
    txt(slide, p[1], x + 0.24, y + 0.16, 3.3, 0.22, {
      fontFace: FONT.body, fontSize: 9, color: C.orange, bold: true, charSpacing: 0.5,
    });
    txt(slide, p[0], x + 0.24, y + 0.5, 3.3, 0.34, { fontSize: 18, bold: true });
    txt(slide, p[2], x + 0.24, y + 0.98, 3.3, 0.26, { fontSize: 10.5, color: C.iron });
  });

  rect(slide, 0.58, 5.28, 12.12, 1.3, C.graphite, null, 0.04);
  txt(slide, 'API / 外部数据', 0.88, 5.62, 1.55, 0.32, { fontSize: 14, color: C.white, bold: true, align: 'center' });
  txt(slide, '→', 2.52, 5.62, 0.38, 0.32, { fontSize: 18, color: C.orange, align: 'center' });
  txt(slide, '授权与统一调度', 2.98, 5.62, 1.8, 0.32, { fontSize: 14, color: C.white, bold: true, align: 'center' });
  txt(slide, '→', 4.88, 5.62, 0.38, 0.32, { fontSize: 18, color: C.orange, align: 'center' });
  const outs = [['动作', 5.38], ['表情', 6.52], ['音频', 7.66]];
  outs.forEach(([label, ox]) => {
    rect(slide, ox, 5.52, 0.96, 0.52, C.darkCard, C.iron, 0.03);
    txt(slide, label, ox, 5.62, 0.96, 0.28, { fontSize: 12.5, color: C.teal, bold: true, align: 'center' });
  });
  txt(slide, '默认关闭  /  明示授权  /  随时停止', 9.12, 5.51, 3.1, 0.28, { fontSize: 11, color: C.orange, bold: true, align: 'center' });
  txt(slide, '远程与外部数据能力必须先获得授权。', 9.12, 5.93, 3.1, 0.26, { fontSize: 9.5, color: C.silver, align: 'center' });
  footer(slide, 'ROADMAP ONLY / NOT SHIPPED / AUTHORIZATION REQUIRED WHERE NOTED');
  slide.addNotes('API 可扩展规划：主动坐姿、专注休息、陪伴日报、自定义表演均尚未上线；天气日程、安全远程需授权且尚未上线。规划不代表当前能力。');
}

// 09 — Engineering and verification
{
  const slide = pptx.addSlide('BLANK');
  slide.background = { color: C.white };
  header(slide, 9, '08 / ENGINEERING + VERIFICATION', '技术与验证，边界写清楚');

  rect(slide, 0.58, 1.48, 6.18, 3.47, C.silver);
  addImageCrop(slide, ASSETS.headViews, 0.7, 1.6, 5.94, 3.05, { x: 0.02, y: 0.11, w: 0.94, h: 0.77 });
  txt(slide, 'R06 / SOURCE-ALIGNED CAD VIEWS', 0.82, 4.63, 4.4, 0.2, {
    fontFace: FONT.body, fontSize: 8.5, color: C.iron, bold: true, charSpacing: 1.0,
  });

  const specs = [
    ['20', '姿态点 / 段', '动作可拆解、可验证'],
    ['2', '双 OLED', '左右眼独立像素图案'],
    ['16 kHz', '20 ms / Opus', '音频帧格式明确'],
    ['1', '统一调度', '动作、表情、音频协同'],
  ];
  specs.forEach((s, i) => {
    const x = 7.1 + (i % 2) * 2.86;
    const y = 1.48 + Math.floor(i / 2) * 1.78;
    rect(slide, x, y, 2.58, 1.5, i === 0 ? C.graphite : C.pale, i === 0 ? C.graphite : C.line, 0.04);
    txt(slide, s[0], x + 0.2, y + 0.16, 2.18, 0.5, {
      fontFace: FONT.head, fontSize: 28, color: i === 0 ? C.orange : C.graphite, bold: true,
    });
    txt(slide, s[1], x + 0.2, y + 0.72, 2.18, 0.28, {
      fontSize: 13, color: i === 0 ? C.white : C.graphite, bold: true,
    });
    txt(slide, s[2], x + 0.2, y + 1.08, 2.18, 0.24, {
      fontSize: 9.5, color: i === 0 ? C.silver : C.iron,
    });
  });

  const checks = [
    ['36', '项 Python 测试'],
    ['1253', '样本'],
    ['0', '软件限位越界'],
    ['PASS', 'edge50 编译'],
  ];
  checks.forEach((c, i) => {
    const x = 0.58 + i * 2.26;
    txt(slide, c[0], x, 5.28, 1.94, 0.48, {
      fontFace: FONT.head, fontSize: i === 3 ? 23 : 28, color: i === 2 ? C.teal : C.graphite, bold: true,
    });
    txt(slide, c[1], x, 5.84, 1.98, 0.26, { fontSize: 11, color: C.iron, bold: true });
  });
  rect(slide, 9.63, 5.2, 3.07, 1.16, C.graphite, C.orange, 0.04);
  txt(slide, '实机未验收', 9.87, 5.39, 2.58, 0.28, { fontSize: 15, color: C.orange, bold: true });
  txt(slide, '装配、OLED 实际显示、载荷与碰撞\n仍需实机验证。', 9.87, 5.77, 2.55, 0.45, { fontSize: 9.5, color: C.silver });
  footer(slide, 'SOFTWARE CHECKS PASSED ≠ HARDWARE ACCEPTED');
  slide.addNotes('技术与验证：20 姿态点/段、双 OLED、16kHz、20ms Opus、统一调度；36 项 Python 测试、1253 样本、0 软件限位越界、edge50 编译通过。实机未验收。');
}

// 10 — Closing
{
  const slide = pptx.addSlide('BLANK');
  slide.background = { color: C.graphite };
  rect(slide, 8.2, 0, 5.133, 7.5, C.silver);
  addImageCrop(slide, ASSETS.headViews, 8.36, 1.22, 4.82, 4.72, { x: 0.0, y: 0.11, w: 0.43, h: 0.70 });
  txt(slide, 'LINGXI / DESKTOP COMPANION', 0.62, 0.6, 4.2, 0.26, {
    fontFace: FONT.body, fontSize: 10, color: C.teal, bold: true, charSpacing: 1.6,
  });
  txt(slide, '灵犀，\n桌面上的机甲伙伴', 0.58, 1.55, 7.05, 1.65, {
    fontSize: 36, color: C.white, bold: true, lineSpacingMultiple: 0.96,
  });
  txt(slide, '语音对话、按需视觉、人格与偏好。\n动作与表情，让日常回应更自然。', 0.62, 3.65, 5.8, 0.8, {
    fontSize: 18, color: C.silver,
  });
  gaze(slide, 0.64, 5.02, 0.62, 'flat', 'square', C.white);
  txt(slide, '需要时回应，日常里克制陪伴。', 2.45, 5.2, 4.4, 0.36, {
    fontSize: 17, color: C.orange, bold: true,
  });
  tag(slide, 'VOICE · VISION · MOTION · SAFETY', 0.62, 6.38, 3.3, true);
  txt(slide, '10', 12.35, 6.9, 0.4, 0.25, {
    fontFace: FONT.head, fontSize: 11, color: C.graphite, align: 'right',
  });
  slide.addNotes('结尾：灵犀，桌面上的机甲伙伴。以真实功能提供持续而克制的日常陪伴。');
}

async function writeDeck() {
  const fileName = path.join(__dirname, '灵犀-你的桌面机甲伙伴-产品展示.pptx');
  await pptx.writeFile({ fileName });
  const zip = await JSZip.loadAsync(fs.readFileSync(fileName));
  const contentTypes = await zip.file('[Content_Types].xml').async('string');
  const cleaned = contentTypes
    .replace(/<Default Extension="[^"]+" ContentType="video\/[^"]+"\/>/g, '')
    .replace(/<Override PartName="[^"]+" ContentType="video\/[^"]+"\/>/g, '');
  zip.file('[Content_Types].xml', cleaned);
  fs.writeFileSync(fileName, await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' }));
}

writeDeck().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
