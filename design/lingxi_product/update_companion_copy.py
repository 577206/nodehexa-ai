"""Apply the approved lifelong-companion copy to the existing visual direction."""
from pathlib import Path
import re, shutil

P=Path(__file__).resolve().parent
def replace_once(s,old,new):
    if old not in s:raise ValueError('Missing expected copy: '+old[:60])
    return s.replace(old,new)

for name in ['index.html','rebuild_studio_v2.py']:
    target=P/name;s=target.read_text()
    pairs=[
      ('灵犀，你的桌面机甲伙伴。语音交流、按需视觉，以及有表情的回应。','灵犀，陪你长大，也陪你变老。通过 API 连接对话与视觉能力，让熟悉的陪伴跟随人生阶段延续。'),
      ('有点机甲，有点戏精。','长期陪伴，始终是你熟悉的灵犀。'),
      ('<h1 id="hero-title">灵犀<span>你的桌面机甲伙伴</span></h1><p>陪你聊天，也用眼神和小动作接住你的每一句话。</p>','<h1 id="hero-title">灵犀<span>陪你长大，也陪你变老。</span></h1><p>从陪你学习，到陪你面对生活，一路相伴。</p>'),
      ('需要时，认真回应。<br><span>日常里，安静陪伴。</span>','你的人生一直变。<br><span>灵犀一直在身边。</span>'),
      ('<h2>越聊，<br>越有默契。</h2>','<h2>越聊越熟悉，<br>陪伴更长久。</h2>'),
      ('<h3>记住你的选择</h3><p>称呼、语气与互动偏好，由你设置，也可以随时修改或清除。</p>','<h3>熟悉你的相处方式</h3><p>从称呼到语气，延续你认可的偏好，也跟随生活阶段调整回应。设置可以修改或清除。</p>'),
      ('<h2>留给未来的<br>想象空间。</h2><p class="roadmap-intro">以下为规划方向，尚未上线。</p>','<h2>API 连接能力，<br>陪伴继续生长。</h2><p class="roadmap-intro">灵犀已通过 API 接入对话与视觉能力。下列扩展场景将继续围绕长期陪伴展开，具体功能状态分别标注。</p>'),
      ('<p>你的桌面机甲伙伴</p>','<p>陪你长大，也陪你变老。</p>'),
    ]
    for old,new in pairs:s=replace_once(s,old,new)
    scenarios='''<section class="section scenarios" id="scenarios" data-reveal><h2>你在成长，<br>灵犀一直在。</h2><p class="life-intro">每个阶段，都有值得一起度过的日常。年龄是故事的起点，相处方式跟随你的需要。</p><div class="scenario-grid"><article class="scenario"><span class="scene-no">10 岁</span><h3>陪你学习</h3><p>一起讨论问题，<br>也保护你的好奇心。</p><small>学习与探索</small></article><article class="scenario"><span class="scene-no">20 岁</span><h3>陪你度过牛马生活</h3><p>听你下班后的吐槽，<br>也陪你整理明天的目标。</p><small>工作与倾诉</small></article><article class="scenario"><span class="scene-no">30 岁</span><h3>陪你出谋划策</h3><p>一起梳理难题、讨论选择，<br>决定仍由你做。</p><small>思考与规划</small></article><article class="scenario"><span class="scene-no">40 岁以后</span><h3>陪你养生喝茶</h3><p>聊聊健康生活，喝茶放松，<br>也继续折腾喜欢的事。</p><small>日常与兴趣</small></article></div></section>'''
    s,n=re.subn(r'<section class="section scenarios".*?</section>',lambda _:scenarios,s,count=1,flags=re.S)
    assert n==1
    vision='''<section class="section vision" id="vision" data-reveal><div class="eyebrow">长期陪伴的产品愿景</div><h2>赛博永生</h2><p class="vision-line">硬件可以更换，熟悉的陪伴继续。</p><p>我们希望让共同经历的记忆、熟悉的称呼与相处方式，跨越硬件更替而延续。灵犀承载你一路走来的故事，也陪你继续写下新的故事。</p><p class="vision-note">记忆的迁移、查看与删除由你掌握。长期记忆延续是产品愿景，将随功能建设逐步实现。</p></section>'''
    s=replace_once(s,'<section class="section evidence"',vision+'\n<section class="section evidence"')
    target.write_text(s)

css=P/'assets/v2/studio.css'
css.write_text(css.read_text()+'''\n/* Approved lifelong companionship copy, 2026-11-01. */
.life-intro{max-width:650px;font-size:15px;margin:-20px 0 50px}.scenario h3{font-size:19px}.scenario .scene-no{font-size:39px;white-space:nowrap}.vision{max-width:none;background:linear-gradient(90deg,#101010f0,#101010a6),url('./hangar-aigc.webp') center/cover;padding-block:110px}.vision h2{font-size:80px;margin-bottom:25px}.vision-line{font-size:28px;color:var(--text);margin:0 0 25px}.vision>p{max-width:670px}.vision-note{font-size:12px;margin-top:30px}.roadmap-intro{line-height:1.9;max-width:340px}
@media(max-width:700px){.hero h1 span{font-size:25px;white-space:nowrap}.hero .eyebrow{font-size:11px;letter-spacing:.08em}.life-intro{font-size:13px;margin:-12px 0 35px}.scenario h3{font-size:16px;line-height:1.5;min-height:48px}.scenario .scene-no{font-size:31px}.vision{padding-block:70px}.vision h2{font-size:60px}.vision-line{font-size:22px}.vision>p{font-size:14px}.vision .vision-note{font-size:11px}.roadmap-intro{max-width:none}}
@media(max-width:360px){.hero h1 span{font-size:22px}.hero .eyebrow{font-size:10px}}
''')

deck=P/'.build-v2/build_deck.mjs'
src=deck.read_text()
src=replace_once(src,'V2-预览03.pptx','V2-长期陪伴版.pptx')
src=replace_once(src,"validation-03.json","validation-companion.json")
src=replace_once(src,"text(s,'你的桌面机甲伙伴',62,370,520,65,39,C.white,true);","text(s,'陪你长大，也陪你变老',62,370,530,65,36,C.white,true);")
src=replace_once(src,"陪你聊天，也用眼神和小动作\\n接住你的每一句话。","从陪你学习，到陪你面对生活。\\n你在成长，灵犀一直在。")
src=replace_once(src,"text(s,'日常陪伴',60,130,780,88,64,C.white,true);","text(s,'你在成长，灵犀一直在',60,130,1160,88,54,C.white,true);")
src=replace_once(src,"需要时认真回应，日常里安静陪伴。","陪伴跟随你的人生阶段，也跟随你当下的需要。")
old="const rows=[['开始工作','先聊清楚今天做什么，\\n再一起拆解目标。','当前能力'],['需要确认','看一眼眼前的物体，\\n只获取需要的画面。','当前能力'],['互动放松','一句俏皮话，\\n一个短暂的小表演。','软件预演'],['休息与回顾','按你的安排提醒休息，\\n在同意后总结互动。','规划，尚未上线']];"
new="const rows=[['陪你学习','一起讨论问题，\\n也保护你的好奇心。','学习与探索'],['陪你度过牛马生活','听你下班后的吐槽，\\n也陪你整理明天的目标。','工作与倾诉'],['陪你出谋划策','梳理难题、讨论选择，\\n决定仍由你做。','思考与规划'],['陪你养生喝茶','聊健康生活，喝茶放松，\\n继续折腾喜欢的事。','日常与兴趣']];"
src=replace_once(src,old,new)
src=replace_once(src,"text(s,'0'+(i+1),x,350,110,66,48,C.red);text(s,r[0],x,443,278,42,28,C.white,true);","text(s,['10 岁','20 岁','30 岁','40 岁以后'][i],x,350,278,66,39,C.red);text(s,r[0],x,443,278,60,i===1?25:28,C.white,true);")
src=replace_once(src,"i===3?C.red:C.muted","C.muted")
src=replace_once(src,"开始工作、按需确认为现有能力场景。互动放松目前展示软件预演。休息提醒和日报为规划，尚未上线。","用户确认的长期陪伴理念：十岁学习、二十岁工作倾诉、三十岁出谋划策、四十岁以后养生喝茶。年龄用于讲述人生阶段，不构成角色限制。健康生活指日常交流与兴趣陪伴。")
src=replace_once(src,"text(s,'由你定义的\\n相处方式',680,128,555,150,54,C.white,true);","text(s,'熟悉的陪伴，\\n跟随你的变化',680,128,555,150,48,C.white,true);")
src=replace_once(src,"温柔、专注，或偶尔吐槽。\\n选择你愿意听见的表达方式。","延续你认可的称呼与偏好。\\n不同阶段，回应不同的需要。")
src=replace_once(src,"text(s,'留给未来的想象空间',60,122,1160,90,52,C.white,true);","text(s,'API 连接能力，陪伴继续生长',60,122,1160,90,48,C.white,true);")
src=replace_once(src,"text(s,'以下为规划方向，尚未上线',64,227,1080,40,23,C.red);","text(s,'已接入对话与视觉 API，以下为陪伴场景的扩展方向',64,227,1120,40,23,C.red);")
src=replace_once(src,"text(s,'机甲的样子，\\n伙伴的回应。',64,370,520,146,48,C.white,true);","text(s,'赛博永生',64,360,560,90,60,C.white,true);")
src=replace_once(src,"text(s,'陪伴跟随你的人生阶段，也跟随你当下的需要。',64,584,590,50,22,'#d8cfc6');","text(s,'硬件可以更换，熟悉的陪伴继续。',64,480,590,50,25,'#d8cfc6');\n text(s,'让共同经历的记忆与相处方式，\\n跨越硬件更替而延续。',64,562,590,90,22,C.muted);\n text(s,'长期陪伴的产品愿景',64,674,590,30,16,C.red);")
src=replace_once(src,"结束页回到桌面机甲伙伴定位。AIGC 只生成环境背景。当前驾驶舱、概念双眼与模型来源保持一致。","结束页展示经用户确认的赛博永生愿景：硬件可更换，记忆与熟悉的相处方式延续。长期记忆的迁移、查看与删除由用户掌握，随功能建设逐步实现，不承诺人的意识永生。AIGC 仅生成环境背景。")
src=replace_once(src,"产品定位：桌面机甲伙伴。","产品定位：长期陪伴的桌面机甲伙伴，陪你长大，也陪你变老。")
deck.write_text(src)
shutil.copy2(deck,P/'source-v2/build_deck.mjs')
print('COMPANION_COPY_UPDATED')
