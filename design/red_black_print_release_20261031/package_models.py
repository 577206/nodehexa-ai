from pathlib import Path
import hashlib, json, shutil, zipfile
import trimesh

ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
ORIGINAL=REPO/'mechanism/hexapod'
INBOX=Path('/Users/dyke_4/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_5mio2s3wlprs22_624e/msg/file/2026-10')
INPUT=ROOT/'inputs'
INPUT.mkdir(exist_ok=True)
NEW=['Armor_R_A1_TrialFit.stl','Armor_L_A1_TrialFit.stl','TKRC-FootButtom_MountDraft.stl','TKRC-FootTop_MountDraft.stl']
for n in NEW:
    if not (INPUT/n).exists(): shutil.copy2(INBOX/n,INPUT/n)
reference=Path('/var/folders/5r/tr64v33975xfkwwc5lny84gm0000gn/T/codex-clipboard-eb5bc52d-b9ac-4fb2-abd6-77730377179b.png')
if not (ROOT/'approved_color_reference.png').exists(): shutil.copy2(reference,ROOT/'approved_color_reference.png')

# Group filenames, not mesh materials: the physical filament supplies the color.
red=[('TKRC-LegTop.STL',6),('TKRC-ThighTop.STL',6),('TKRC-JointCross.STL',6)]
black=[('TKRC-FootGround.STL',6),('TKRC-LegBottom.STL',6),('TKRC-ThighBottom.STL',6),('TKRC-JointTop.STL',12),('TKRC-JointDown.STL',12),('TKRC-FootTip.STL',6),('TKRC-BodyCenter.STL',1),('TKRC-BodySideWall.STL',2),('TKRC-BodyBackWall.STL',1)]
new_black=[('TKRC-FootTop_MountDraft.stl',6),('TKRC-FootButtom_MountDraft.stl',6),('Armor_L_A1_TrialFit.stl',6),('Armor_R_A1_TrialFit.stl',6)]
rows=[]
for color,entries in [('RED',red),('BLACK',black),('BLACK',new_black)]:
    for name,qty in entries:
        source=INPUT/name if name in NEW else ORIGINAL/name
        folder=ROOT/color/'models'/f'QTY_{qty:02d}'
        folder.mkdir(parents=True,exist_ok=True)
        dest=folder/name
        if dest.exists(): dest.chmod(dest.stat().st_mode | 0o200)
        shutil.copy2(source,dest)
        mesh=trimesh.load(dest,force='mesh')
        digest=hashlib.sha256(source.read_bytes()).hexdigest()
        assert digest==hashlib.sha256(dest.read_bytes()).hexdigest()
        rows.append(dict(color=color,file=str(dest.relative_to(ROOT)),quantity=qty,
            quantity_basis='每条腿左右外壳各一件，暂按各6件备料；需试装确认' if name.startswith('Armor_') else '清晰原机套件照片数量；新版FootTop/FootButtom按原件数量替换',
            source='user_supplied/'+name if name in NEW else str(source.relative_to(REPO)),
            sha256=digest,dimensions_mm=mesh.extents.round(4).tolist(),watertight=bool(mesh.is_watertight),
            note='试装/安装草稿，未验证装配间隙' if name in NEW else '原版几何，未修改'))

optional=[('TKRC-BodyCenter-Thin.STL',1,'备选：仅用于原机采用薄版中央支架时，和普通BodyCenter二选一')]
optional_rows=[]
for name,qty,note in optional:
    folder=ROOT/'BLACK'/'optional_not_in_main_count'/f'QTY_{qty:02d}'
    folder.mkdir(parents=True,exist_ok=True)
    dest=folder/name
    shutil.copy2(ORIGINAL/name,dest)
    optional_rows.append(dict(file=str(dest.relative_to(ROOT)),quantity=qty,note=note,sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))

common='''红黑配色打印文件 R01 / 2026-10-31
状态：分类备料包，上下机身等待用户新版；不是最终整机装配放行。
本包保留STL几何原样，无缩放、旋转、补洞或重建。STL本身不设打印颜色，切片时请装入并选用对应红色/黑色耗材。
每种STL只放一份，按QTY目录及清单中的数量在切片器复制实例，不要只打印一份。
新FootTop、FootButtom已替代原版。原版两文件未混入包内。
Armor_L/R为左右外壳，暂按每条腿各一件、各6件安排。不是左右三条腿各3件；此配对假设尚需试装确认。
新四件经只读网格检查可读取且封闭；未据此宣称舵机安装、孔位、间隙及实物适配已验证。尺寸检查假设STL数值单位为毫米。
旧BodyTop、BodyButtom及18650下框变体已排除，等待新版上下机身。
机盖、驾驶舱、底座、旧草稿饰件、螺丝和舵机均不在本次包内。图中金色紧固件沿用五金件，不作为打印件分色。
用户已确认保留原FootGround，新左右外壳加装在外面；FootGround共6件，已纳入黑色主清单。
optional_not_in_main_count 内BodyCenter-Thin与普通BodyCenter二选一，不要两者累计打印。
'''
for color in ['RED','BLACK']:
    selected=[r for r in rows if r['color']==color]
    text=common+'\n本色主清单（数量）\n'+'\n'.join(f"{Path(r['file']).name} × {r['quantity']}" for r in selected)
    text+='\n\n本色暂排数量：'+str(sum(r['quantity'] for r in selected))+'（不含待确认/备选件、上下机身）\n'
    if color=='BLACK':
        text+='\n待确认/备选：\n'+'\n'.join(f"{Path(r['file']).name} × {r['quantity']}：{r['note']}" for r in optional_rows)+'\n'
    (ROOT/color/'PRINT_README.txt').write_text(text)
    (ROOT/color/'manifest.json').write_text(json.dumps(dict(status='pending_new_body_and_fit_checks',parts=selected,optional=optional_rows if color=='BLACK' else []),ensure_ascii=False,indent=2)+'\n')
    archive=ROOT/f'NodeHexa_{color}_R01_pending_body.zip'
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for f in sorted((ROOT/color).rglob('*')):
            if f.is_file(): z.write(f,f.relative_to(ROOT))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for r in selected:
            assert hashlib.sha256(z.read(r['file'])).hexdigest()==r['sha256']
    print(archive.name,archive.stat().st_size,'bytes',len(selected),'main types',sum(r['quantity'] for r in selected),'planned parts')
(ROOT/'manifest.json').write_text(json.dumps(dict(status='pending_new_body_and_fit_checks',parts=rows,optional=optional_rows,pending=['新版BodyTop','新版BodyButtom','左右外壳各6件的装配配对及间隙试装']),ensure_ascii=False,indent=2)+'\n')
(ROOT/'README.txt').write_text(common+'\n红色3种、18件。黑色主清单13种、76件，其中含左右新外壳共12件的暂排数量。\n原FootGround 6件已确认保留，并入黑色主清单；新外壳为外加件。薄中央支架1件为替换备选，不额外累加。\n收到新版上下机身后再生成完整最终包。\n')
print('All copied meshes preserved; archive CRC and main file SHA-256 checks passed.')
