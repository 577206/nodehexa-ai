"""Checked source-profile receiving pockets for R06 upper cheek rails.

The five-sided rail station profiles are expanded in XY and extrapolated at
both Z ends. This cuts an intentional receiving slot, including thin shell
regions that an exact insert subtraction would isolate. The *complete* cut
result must remain a valid single solid; no fragment is ever discarded.

Only P02 is modified, in memory, after both sides have passed. Rails P10/P11
are unchanged. Nominal gaps are design-review values, not print-fit approval.
"""
import math
import FreeCAD as App
import Part

_DEFAULT_STATIONS = [(33, -53, 23), (40, -52, 27), (58, -42, 29),
                     (73, -27, 24), (81, -15, 20)]
_SETBACKS = [3.0, 3.6, 3.6, 2.5, 1.8]


def _offset_xy(points, amount):
    """Outward miter offset of a simple consistently wound planar polygon."""
    area = sum(a[0] * b[1] - a[1] * b[0]
               for a, b in zip(points, points[1:] + points[:1]))
    sign = 1 if area > 0 else -1
    lines = []
    for a, b in zip(points, points[1:] + points[:1]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 1e-8:
            raise ValueError('Degenerate source rail profile')
        lines.append(((a[0] + sign * dy * amount / length,
                       a[1] - sign * dx * amount / length), (dx, dy)))
    result = []
    for i, (b, s) in enumerate(lines):
        a, r = lines[i - 1]
        den = r[0] * s[1] - r[1] * s[0]
        if abs(den) < 1e-10:
            raise ValueError('Parallel consecutive rail profile edges')
        t = ((b[0] - a[0]) * s[1] - (b[1] - a[1]) * s[0]) / den
        result.append((a[0] + t * r[0], a[1] + t * r[1]))
    return result


def _state(shape):
    return {'valid': bool(shape.isValid()), 'solids': len(shape.Solids),
            'volume_mm3': float(shape.Volume), 'null': bool(shape.isNull())}


def _valid(state):
    return state['valid'] and not state['null'] and state['solids'] == 1 and state['volume_mm3'] > 0


def _receiving_tools(stations, gap_xy, end_gap_z, lower_z):
    if len(stations) != len(_SETBACKS):
        raise ValueError('Rail source expects five canopy stations')
    source = [(float(z), float(y) + b, float(w))
              for (z, y, w), b in zip(stations, _SETBACKS)]
    if any(b[0] <= a[0] for a, b in zip(source, source[1:])):
        raise ValueError('Rail station Z values must increase')
    if not source[0][0] < lower_z < source[-1][0]:
        raise ValueError('Upper rail lower clipping Z is outside source range')

    def interpolate(z):
        i = next((j for j in range(len(source) - 1)
                  if source[j][0] <= z <= source[j + 1][0]),
                 0 if z < source[0][0] else len(source) - 2)
        a, b = source[i:i + 2]
        t = (z - a[0]) / (b[0] - a[0])
        return z, a[1] + t * (b[1] - a[1]), a[2] + t * (b[2] - a[2])

    levels = [lower_z - end_gap_z]
    levels += [z for z, _, _ in source if lower_z < z < source[-1][0]]
    levels += [source[-1][0] + end_gap_z]
    wires = []
    for height in levels:
        z, front, width = interpolate(height)
        profile = [(width + .4, front), (width + 7, front),
                   (width + 8.7, front + 1.7), (width + 7.5, front + 4.5),
                   (width + .4, front + 4.5)]
        points = [App.Vector(x, y, z) for x, y in _offset_xy(profile, gap_xy)]
        wires.append(Part.makePolygon(points + [points[0]]))
    right = Part.makeLoft(wires, True, True)
    left = right.copy()
    left = left.mirror(App.Vector(0, 0, 0), App.Vector(1, 0, 0))
    return [('P10', right), ('P11', left)], levels


def apply_rail_receiving_clearance(doc, manifest, stations=None,
                                   gap_xy_mm=.30, end_gap_z_mm=.20,
                                   upper_rail_lower_z_mm=49.6):
    """Return (report, changed_ids); atomically update P02 after both checks.

    Call after resolve_interfaces and re-export P02. Pass live build ``stations``
    explicitly, or a manifest dict with canopy_stations. Current insert geometry
    must fit the envelope, otherwise the whole operation is rejected.
    """
    if not 0 < gap_xy_mm <= .5 or not 0 < end_gap_z_mm <= .5:
        raise ValueError('Review pocket clearances must be >0 and <=0.5 mm')
    if stations is None:
        stations = manifest.get('canopy_stations', _DEFAULT_STATIONS) if isinstance(manifest, dict) else _DEFAULT_STATIONS
    report = {'operation': 'R06_upper_rail_source_profile_clearance',
              'receiver': 'P02', 'insert_parts': ['P10', 'P11'],
              'nominal_xy_profile_expansion_mm': float(gap_xy_mm),
              'nominal_z_end_extension_mm': float(end_gap_z_mm),
              'upper_rail_lower_z_mm': float(upper_rail_lower_z_mm),
              'source_canopy_stations': stations, 'front_setbacks_mm': _SETBACKS,
              'actions': [], 'changed_ids': [],
              'limitations': ['XY profile expansion is not uniform surface-normal clearance.',
                             'Print tolerance, retention, minimum wall thickness and assembly paths remain unverified.']}
    receiver = doc.getObject('P02')
    if receiver is None:
        report['status'] = 'REJECTED_MISSING_RECEIVER'
        return report, []
    current = receiver.Shape.copy()
    report['before'] = _state(current)
    if not _valid(report['before']):
        report['status'] = 'REJECTED_INVALID_RECEIVER'
        return report, []
    try:
        tools, levels = _receiving_tools(stations, gap_xy_mm, end_gap_z_mm,
                                        upper_rail_lower_z_mm)
        report['receiving_loft_z_levels_mm'] = levels
        for pid, tool in tools:
            action = {'receiver': 'P02', 'insert': pid,
                      'before': _state(current), 'tool_state': _state(tool)}
            report['actions'].append(action)
            insert = doc.getObject(pid)
            if insert is None or not _valid(action['tool_state']):
                raise ValueError('Missing insert or invalid receiving envelope: ' + pid)
            ins = insert.Shape
            action['insert_state'] = _state(ins)
            if not _valid(action['insert_state']):
                raise ValueError('Invalid insert: ' + pid)
            action['insert_outside_envelope_mm3'] = float(ins.cut(tool).Volume)
            if action['insert_outside_envelope_mm3'] > 1e-5:
                raise ValueError('Source envelope no longer contains current insert: ' + pid)
            candidate = current.cut(tool).removeSplitter()
            state = _state(candidate)
            action['candidate'] = state
            if not _valid(state):
                action['candidate_fragment_volumes_mm3'] = [float(s.Volume) for s in candidate.Solids]
                raise ValueError('Whole cut result is not one valid solid: ' + pid)
            distance = float(candidate.distToShape(ins)[0])
            common = float(candidate.common(ins).Volume)
            removed = action['before']['volume_mm3'] - state['volume_mm3']
            action.update(measured_min_gap_mm=distance, remaining_overlap_mm3=common,
                          removed_volume_mm3=removed)
            if distance <= 1e-4 or common > 1e-6 or removed < -1e-6:
                raise ValueError('Clearance or monotonic volume check failed: ' + pid)
            action.update(status='validated_candidate', insert_unchanged=True)
            current = candidate
        report['final_measured_gaps_mm'] = {
            pid: float(current.distToShape(doc.getObject(pid).Shape)[0]) for pid in ('P10', 'P11')}
        report['final_overlaps_mm3'] = {
            pid: float(current.common(doc.getObject(pid).Shape).Volume) for pid in ('P10', 'P11')}
        if (min(report['final_measured_gaps_mm'].values()) <= 1e-4 or
                max(report['final_overlaps_mm3'].values()) > 1e-6):
            raise ValueError('Final two-sided check failed')
        receiver.Shape = current
        doc.recompute()
        for action in report['actions']:
            action['status'] = 'applied'
        report.update(status='NOMINAL_GAP_VERIFIED_FIT_UNVERIFIED',
                      after=_state(current), changed_ids=['P02'])
        return report, ['P02']
    except Exception as ex:
        report.update(status='REJECTED_REQUIRES_REVIEW', error=str(ex),
                      receiver_unchanged=True)
        return report, []
