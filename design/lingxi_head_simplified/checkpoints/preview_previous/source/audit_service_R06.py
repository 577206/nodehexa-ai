"""Read-only service-access audit of final R06 BREP caches.

Run only after the parent confirms the complete, final R06 cache is published:
  python source/audit_service_R06.py --final-cache-confirmed
Writes validation/service_R06_checks.json, never changes CAD or preview assets.
"""
from pathlib import Path
import argparse
import hashlib
import json
from datetime import datetime, timezone
from build123d import *

ROOT=Path(__file__).resolve().parents[1]
EPS_VOLUME=1e-5
MOVING=('H03_CLEAR_VISOR','H04_VISOR_FRAME')

def vol(shape):
    if not shape:return 0.0
    if isinstance(shape,ShapeList):return sum(vol(s) for s in shape)
    return float(shape.volume)

def overlap(a,b,tol=1e-7):
    aa=a.bounding_box();bb=b.bounding_box()
    return all(min(p,q)-max(r,s)>tol for p,q,r,s in zip(aa.max,bb.max,aa.min,bb.min))

def swept_face_overlap(face,other,length):
    a=face.bounding_box();b=other.bounding_box()
    amin=list(a.min);amax=list(a.max);bmin=list(b.min);bmax=list(b.max);amax[1]+=length
    return all(min(amax[i],bmax[i])-max(amin[i],bmin[i])>1e-7 for i in range(3))

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--final-cache-confirmed',action='store_true');args=ap.parse_args()
    if not args.final_cache_confirmed:raise SystemExit('Wait for final R06 cache confirmation; then pass --final-cache-confirmed.')
    manifest_path=ROOT/'validation/R06_checks.json';manifest=json.loads(manifest_path.read_text())
    if not manifest.get('pass'):raise SystemExit('Final R06 CAD checks are not passing; service audit stopped.')
    names=[p['id'] for p in manifest['parts']]
    if not all(n in names for n in MOVING) or not any(n.startswith('D') for n in names):raise SystemExit('R06 cache must contain both visor parts and the complete decoration set.')
    shapes={};provenance=[]
    for n in names:
        path=ROOT/f'review/cache/R06_{n}.brep';raw=path.read_bytes();shape=import_brep(str(path))
        if not shape.is_valid or len(shape.solids())!=1:raise ValueError('Invalid final cache: '+n)
        shapes[n]=shape;provenance.append({'part':n,'path':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(raw).hexdigest()})
    report={'schema':'lingxi.R06.service_access.v1','generated_at':datetime.now(timezone.utc).isoformat(),'units':'mm','mode':'read_only_final_cache','provenance':provenance,'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'volume_tolerance_mm3':EPS_VOLUME,'physical_fit_verified':False}
    static={n:s for n,s in shapes.items() if n not in MOVING}
    # Fixed corridor from outside left face towards the provisional PCB socket.
    usb=Pos(-47.5,-15,41.5)*Box(45,14,9)
    rows=[]
    for n,s in shapes.items():
        amount=vol(usb.intersect(s)) if overlap(usb,s) else 0.0
        rows.append({'part':n,'intersection_mm3':amount,'pass':amount<EPS_VOLUME})
    report['USB']={'probe_center_mm':[-47.5,-15,41.5],'probe_size_mm':[45,14,9],'insertion_axis':[1,0,0],'scope':'Existing 14 x 9 mm minimum plug corridor; actual cable head may require more clearance.','parts':rows,'pass':all(r['pass'] for r in rows)}
    report['visor_removal']={'translation_axis':[0,1,0],'distance_mm':100,'assembly_condition':'Remove the two lower M2 visor screws, then translate H03 and H04 together. Decorations and body remain fixed.','sampled_positions_mm':[0,.1,.5,1,2,5,10,20,40,75,100],'sample_checks':[],'face_prism_sweeps':[]}
    section=report['visor_removal']
    for n in MOVING:
        for dy in section['sampled_positions_mm']:
            moving=Pos(0,dy,0)*shapes[n]
            for other,solid in static.items():
                if not overlap(moving,solid):continue
                amount=vol(moving.intersect(solid))
                section['sample_checks'].append({'moving':n,'fixed':other,'translation_mm':dy,'intersection_mm3':amount,'pass':amount<EPS_VOLUME})
        # Exact swept-volume boundary prisms supplement positional sampling.
        # All non-Y-parallel faces are considered, including mounting ears and
        # upper locating pin end caps. Normals use the same 3 x 3 UV gate as R05A.
        sweep={'part':n,'method':'CAD prisms from every non-Y-parallel boundary face extruded +Y by100mm; 3x3 UV normal gate, bounding-box early rejection. Initial-volume checks included above.','faces_considered':len(shapes[n].faces()),'faces_parallel':0,'faces_outside_static_bounds':0,'prisms_checked':0,'errors':[],'intersections':[]}
        for i,face in enumerate(shapes[n].faces()):
            try:
                normals=[abs(face.normal_at(u=u,v=v).Y) for u in [.1,.5,.9] for v in [.1,.5,.9]]
                if max(normals)<1e-8:sweep['faces_parallel']+=1;continue
                targets=[(other,solid) for other,solid in static.items() if swept_face_overlap(face,solid,100)]
                if not targets:sweep['faces_outside_static_bounds']+=1;continue
                prism=Solid.extrude(face,(0,100,0))
                if not prism.is_valid:raise ValueError('invalid swept prism')
                sweep['prisms_checked']+=1
                for other,solid in targets:
                    amount=vol(prism.intersect(solid))
                    if amount>EPS_VOLUME:sweep['intersections'].append({'face':i,'fixed':other,'intersection_mm3':amount})
            except Exception as exc:sweep['errors'].append({'face':i,'error':str(exc)})
        sweep['pass']=not sweep['errors'] and not sweep['intersections'];section['face_prism_sweeps'].append(sweep)
    section['pass']=all(r['pass'] for r in section['sample_checks']) and all(r['pass'] for r in section['face_prism_sweeps'])
    report['pass']=section['pass'] and report['USB']['pass']
    report['limitations']=['Positive-volume CAD collision checks do not guarantee real printed clearances or flexible cable bend radius.','Removable visor parts move together; metal visor screws must be removed before extraction.','No model files are modified by this audit.']
    path=ROOT/'validation/service_R06_checks.json';path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps({'pass':report['pass'],'usb_pass':report['USB']['pass'],'visor_removal_pass':section['pass'],'sweeps':section['face_prism_sweeps'],'report':str(path)},ensure_ascii=False,indent=2))
    if not report['pass']:raise SystemExit(1)

if __name__=='__main__':main()
