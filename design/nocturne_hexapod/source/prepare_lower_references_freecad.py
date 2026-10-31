"""Run in FreeCAD Python. Preserve original faceted geometry as reference BRep.
This helper does not recover nominal CAD surfaces or establish physical fit.
The editable widening operation remains in build123d lower_frame.py.
"""
import FreeCAD as A, Part, Mesh, json, hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
records=[]
for name in ['BodyButtom','BodyButtom-18650-2S']:
    path=ROOT/'inputs/original_chassis'/('TKRC-'+name+'.STL')
    mesh=Mesh.Mesh(str(path));shape=Part.Shape()
    shape.makeShapeFromMesh(mesh.Topology,.00001)
    shape=Part.makeSolid(shape).removeSplitter()
    assert shape.isValid() and len(shape.Solids)==1
    b=shape.BoundBox
    shape.translate(A.Vector(-b.XMin,-b.YMin,-b.ZMin))
    shape.rotate(A.Vector(0,0,0),A.Vector(1,0,0),90)
    b=shape.BoundBox;shape.translate(A.Vector(-b.XMin,-b.YMin,-b.ZMin))
    out=ROOT/'validation/interfaces'/(name+'_reference.brep')
    shape.exportBrep(str(out))
    records.append(dict(name=name,source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),reference_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),valid=shape.isValid(),solids=len(shape.Solids),volume_mm3=shape.Volume,local_coordinates='u=X-Xmin; v=Zmax-Z; w=Y-Ymin (proper rotation, not assembly placement)',source_precision='original triangulated STL surface; no nominal tolerance recovery'))
(ROOT/'validation/interfaces/lower_reference_provenance.json').write_text(json.dumps(records,indent=2))
