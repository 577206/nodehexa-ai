"""Collect saved R06 review evidence without changing geometry or QA thresholds."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / '04_review/iteration_06c'
def read(path):
    return json.loads((ROOT / path).read_text())

manifest = read('03_assembly/manifest_R06.json')
qa = read('04_review/iteration_06c/blender_qa.json')
interference = read('03_assembly/interference_R06.json')
interfaces = read('03_assembly/interface_resolution_R06.json')
rear_clearance = read('03_assembly/rear_clearance_R06.json')
rail_clearance = read('03_assembly/rail_clearance_R06.json')
parts = manifest['parts']
summary = {
    'revision': 'R06',
    'status': 'DRAFT_REVIEW_NOT_PRINT_RELEASE',
    'part_count': len(parts),
    'categories': dict(Counter(p['category'] for p in parts)),
    'all_cad_valid_single_solid': all(p['valid'] and p['solids'] == 1 for p in parts),
    'independent_saved_cad_validation': interference['all_saved_parts_valid'],
    'parts_with_edge_breaks': sum(p.get('edge_break_mm', 0) > 0 for p in parts),
    'triangle_count': sum(o['tris'] for o in qa['objects'].values()),
    'mesh_qa_pass': qa['pass'],
    'mesh_errors': qa['errors'],
    'mesh_warnings': qa['warnings'],
    'nonhardware_overlap_count': len(interference['rigid_part_interferences']),
    'nonhardware_overlap_threshold_mm3': .05,
    'receiving_parts_modified': interfaces['changed_ids'],
    'clearance_added_by_exact_pockets_mm': interfaces['clearance_added_mm'],
    'rear_source_pocket_nominal_gap_mm': rear_clearance['nominal_review_gap_mm'],
    'rear_measured_min_gaps_mm': rear_clearance['final_measured_gaps_mm'],
    'upper_rail_measured_min_gaps_mm': rail_clearance['final_measured_gaps_mm'],
    'print_ready': False,
    'reference_match_exact': False,
    'limitations': [
        'Hardware dimensions unmeasured; packaging and retention remain provisional.',
        'No minimum-wall, tolerance, strength or assembly-path approval.',
        'Legacy desktop base is retained for context and is not a print release.',
        'Nominal zero-overlap does not establish printable mating clearance.',
    ],
}
REVIEW.mkdir(exist_ok=True, parents=True)
(REVIEW / 'validation_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in summary.items() if k not in ('mesh_warnings', 'limitations')}, ensure_ascii=False, indent=2))
