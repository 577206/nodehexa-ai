"""R06 second-batch decorations on immutable R05A four-piece structural core.
CAD truth in mm. X robot right, Y camera forward, Z up. Exports keep parts separate.
"""
from pathlib import Path
import importlib.util,sys
from build123d import *
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'source'))
sp=importlib.util.spec_from_file_location('fixed_r05a',ROOT/'source/model_R05A_archive.py');core=importlib.util.module_from_spec(sp);sp.loader.exec_module(core)
load_parameters=core.load_parameters;val=core.val;volume=core.volume
COLORS={};LABELS={};PART_IDS={};MOUNT_INTERFACES=[];DECORATION_RECORDS=[];DECORATION_MOUNTS=[]
MODULES=['decoration_vents_R06','decoration_armor_R06','decoration_camera_R06','decoration_phone_R06']

# Explicit routing documents the source call chain for the lightweight static auditor.
# Values are passed unchanged to these functions; core dimensions are locked.
PARAMETER_ROUTES={
 'base_thickness':'core.bottom_dock -> R04.bottom_dock -> R03.bottom_dock',
 'wall':'core.top_support_shell', 'dock_pocket':'core.bottom_dock',
 'dock_depth':'core.bottom_dock', 'dock_radial_clearance':'core.bottom_dock',
 'bowl_height':'core.bottom_dock', 'screw_span':'core.bottom_dock and top_support_shell',
 'shaft_diameter':'core.bottom_dock and top_support_shell', 'pan_recess_diameter':'core.bottom_dock',
 'usb_access_width':'core.top_support_shell', 'usb_access_height':'core.top_support_shell',
 'usb_access_center_z':'core.top_support_shell',
 'oled_board_width':'core.hardware_references -> R04.oled_references',
 'oled_board_height':'core.hardware_references -> R04.oled_references',
 'oled_center_spacing':'core.hardware_references -> R04.oled_references',
 'phone_clear_width':'decoration_phone_R06.build_parts',
 'phone_clear_depth':'decoration_phone_R06.build_parts',
 'phone_support_top':'decoration_phone_R06.build_parts'}
FROZEN_GEOMETRY={'base_thickness':34,'wall':3,'dock_pocket':86.8,'dock_depth':29.4,
 'dock_radial_clearance':.4,'bowl_height':29,'screw_span':92,'shaft_diameter':2.4,
 'pan_recess_diameter':5.2,'usb_access_width':42,'usb_access_height':28,'usb_access_center_z':50}

def build_model(p):
 for key,value in FROZEN_GEOMETRY.items():
  if abs(val(p,key)-value)>1e-8:raise ValueError(f"Frozen first-batch parameter {key} cannot change in decoration iteration")
 COLORS.clear();LABELS.clear();PART_IDS.clear();MOUNT_INTERFACES.clear();DECORATION_RECORDS.clear();DECORATION_MOUNTS.clear()
 base=core.build_model(p);parts=list(base.children)
 COLORS.update(core.COLORS);LABELS.update(core.LABELS);PART_IDS.update(core.PART_IDS);MOUNT_INTERFACES.extend(core.MOUNT_INTERFACES)
 for module_name in MODULES:
  module=__import__(module_name)
  for record in module.build_parts(p):
   s=record['shape'];name=record['name'];color=record['color']
   assert s.is_valid and len(s.solids())==1,name
   s.label=name;s.color=Color(*(int(color[k:k+2],16)/255 for k in [1,3,5]))
   COLORS[name]=color;LABELS[name]=record['label'];PART_IDS[name]=name;parts.append(s)
   DECORATION_RECORDS.append({k:v for k,v in record.items() if k not in ['shape']})
  DECORATION_MOUNTS.extend(getattr(module,'MOUNTS',[]))
 return Compound(children=parts,label='LINGXI_R06_ORANGE_GRAY_SEPARATE_MODULES')
def hardware_references(p):return core.hardware_references(p)
def write_step(model,path):export_step(model,str(path))
if __name__=='__main__':
 a=build_model(load_parameters(ROOT/'parameters.yaml'))
 for s in a.children:print(s.label,s.is_valid,len(s.solids()),s.volume,list(s.bounding_box().size),flush=True)
