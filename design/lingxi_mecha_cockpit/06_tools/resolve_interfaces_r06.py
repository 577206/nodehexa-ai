"""Exact receiving pockets for explicitly identified R06 cockpit interfaces.

Mutates only receiver Shapes in the document supplied by the caller.  It does
not save documents, export parts, remove objects, move parts, change insert
geometry to make it fit, or add a claimed manufacturing clearance.  Every
boolean candidate must retain one valid solid without discarding fragments.
"""
from itertools import combinations

# Subassemblies first, containing shell last. Each tuple is (receiver, inserts,
# physical reason). An insert may itself have received a smaller part earlier
# (for example a canopy frame receiving glass before that frame seats in shell).
INTERFACES=(
 ('P12',('P13',),'camera bezel receives black lens gasket'),
 ('P14',('P15',),'right vent perimeter receives black louver cassette'),
 ('P17',('P18',),'left vent perimeter receives black louver cassette'),
 ('P04',('G04',),'lower canopy seam carrier receives clear center pane'),
 ('P05',('G07',),'middle canopy seam carrier receives clear center pane'),
 ('P06',('G10',),'upper canopy seam carrier receives clear center pane'),
 ('P07',('G05','G06'),'eye carrier clears the two adjacent clear facets'),
 ('P10',('P20',),'right upper cheek rail ends under shoulder armor'),
 ('P11',('P22',),'left upper cheek rail ends under shoulder armor'),
 ('P68',('P14','P15','P16'),'right wraparound cheek clears complete vent frame, louver and fins'),
 ('P69',('P17','P18','P19'),'left wraparound cheek clears complete vent frame, louver and fins'),
 ('P60',('P68','P66'),'right front cheek receives side transition and lower canopy rail'),
 ('P61',('P69','P67'),'left front cheek receives side transition and lower canopy rail'),
 ('P03',tuple('G%02d'%i for i in range(1,13)),
          'canopy carrier receives all twelve separate clear facets'),
 ('P03',('P04','P05','P06'), 'canopy carrier receives three removable seam joiners'),
 ('P03',('P10','P11','P66','P67','P60','P61'),
          'concealed canopy carrier clears the external cheek rails and cheek armor'),
 ('P24',('P68',),'right upper side armor receives continuous front wraparound cheek'),
 ('P26',('P69',),'left upper side armor receives continuous front wraparound cheek'),
 ('P62',('P68','P32','P24'),'right upper black service panel receives front cheek, circular cap and lower armor'),
 ('P63',('P69','P35','P26'),'left upper black service panel receives front cheek, circular cap and lower armor'),
 ('P70',('P68','P62','P38'),'right lower black backing receives cheek and upper service panel, clearing orange intake'),
 ('P71',('P69','P63','P39'),'left lower black backing receives cheek and upper service panel, clearing orange intake'),
 ('P49',('P51','P64','P65'),'rear service frame receives latch and phone-support ribs'),
 ('P45',('P46','P47'),'phone backplate receives the two unchamfered orange cradle rails'),
 ('P48',('P64','P65','P49','P51'),'phone lower cradle receives support ribs and rear frame/latch'),
 ('P01',('P52','P49','P50','P14','P17'),
          'lower shell receives bottom contact cassette, rear service module and vent modules'),
 ('P02',('P03','P10','P11','P66','P67','P14','P17','P49','P50','P64','P65','P48','G11','G12'),
          'upper shell receives canopy, cheek rails, vents, rear service module, phone ribs and forward-shifted lower cradle, plus upper glass'),
)

# This is the existing whole-assembly report threshold, never a cleanup target.
# Boolean operations below are attempted at any measurable overlap >1e-7 mm^3.
REPORT_THRESHOLD_MM3=.05
BOOLEAN_EPSILON_MM3=1e-7

def _state(shape):
    out={'valid':False,'solids':0,'volume_mm3':0.0,'null':True}
    try:
        out.update(valid=bool(shape.isValid()),solids=len(shape.Solids),
                   volume_mm3=float(shape.Volume),null=bool(shape.isNull()))
    except Exception as ex:
        out['error']=str(ex)
    return out

def _part_entries(manifest):
    return manifest.get('parts',[]) if isinstance(manifest,dict) else list(manifest)

def _interferences(doc,entries):
    parts=[];missing=[];errors=[]
    for item in entries:
        if item.get('category')=='hardware':continue
        ob=doc.getObject(item['id'])
        if ob is None or not hasattr(ob,'Shape'):
            missing.append(item['id']);continue
        parts.append((item['id'],ob.Shape))
    hits=[]
    for (aid,a),(bid,b) in combinations(parts,2):
        if not a.BoundBox.intersect(b.BoundBox):continue
        try:
            v=float(a.common(b).Volume)
            if v>REPORT_THRESHOLD_MM3:
                hits.append({'parts':[aid,bid],'overlap_mm3':v})
        except Exception as ex:
            errors.append({'parts':[aid,bid],'error':str(ex)})
    hits.sort(key=lambda row:row['overlap_mm3'],reverse=True)
    return hits,missing,errors

def resolve_interfaces(doc,manifest):
    """Resolve known nominal receiving pockets, returning (report, changed_ids).

    A failed operation leaves its receiver completely unchanged.  Candidate
    fragment volumes are reported for multi-solid failures; no fragment is
    silently dropped.  This is an exact-solid collision reduction pass only:
    fasteners, wall thickness, tolerance, assembly path and print fit remain
    independent design checks.
    """
    entries=_part_entries(manifest)
    before_hits,missing,audit_errors=_interferences(doc,entries)
    report={'schema_version':1,'operation':'exact_receiver_pockets',
            'report_overlap_threshold_mm3':REPORT_THRESHOLD_MM3,
            'boolean_epsilon_mm3':BOOLEAN_EPSILON_MM3,'clearance_added_mm':0.0,
            'policy':'No insert clipping, object deletion, fragment removal, or implicit clearance.',
            'before':{'interference_count':len(before_hits),'interferences':before_hits},
            'actions':[],'missing_parts':missing,'audit_errors':audit_errors,
            'limitations':['Nominal common-volume removal does not validate wall thickness.',
                           'No physical tolerance, fastener retention, assembly path or print fit approval.']}
    changed=set()
    def apply(receiver_id,insert_ids,reason,mode='pair'):
        record={'receiver':receiver_id,'inserts':list(insert_ids),'reason':reason,'mode':mode}
        report['actions'].append(record)
        receiver=doc.getObject(receiver_id)
        inserts=[doc.getObject(i) for i in insert_ids]
        if receiver is None or any(i is None for i in inserts):
            record.update(status='skipped_missing_part');return False
        original=receiver.Shape.copy();record['before']=_state(original)
        if not (record['before']['valid'] and record['before']['solids']==1):
            record.update(status='rejected_invalid_receiver_input');return False
        insert_shapes=[ob.Shape.copy() for ob in inserts]
        record['insert_states']={pid:_state(s) for pid,s in zip(insert_ids,insert_shapes)}
        try:
            # A batch uses a solid union only as the cutter. It cannot discard
            # receiver fragments; the resulting receiver is validated intact.
            cutter=insert_shapes[0]
            for s in insert_shapes[1:]:cutter=cutter.fuse(s)
            overlap=float(original.common(cutter).Volume)
            record['overlap_before_mm3']=overlap
            if overlap<=BOOLEAN_EPSILON_MM3:
                record.update(status='no_measurable_overlap',after=record['before'],
                              overlap_after_mm3=overlap,insert_unchanged=True);return False
            candidate=original.cut(cutter).removeSplitter()
            state=_state(candidate);record['candidate']=state
            if state['solids']!=1:
                record['candidate_fragment_volumes_mm3']=[float(s.Volume) for s in candidate.Solids]
                record.update(status='rejected_multiple_or_zero_solids',after=record['before'],
                              insert_unchanged=True);return False
            if not state['valid'] or state['null'] or state['volume_mm3']<=0:
                record.update(status='rejected_invalid_candidate',after=record['before'],
                              insert_unchanged=True);return False
            removed=record['before']['volume_mm3']-state['volume_mm3']
            record['removed_volume_mm3']=removed
            residual=float(candidate.common(cutter).Volume)
            record['overlap_after_mm3']=residual
            if removed<-1e-6 or residual>max(1e-6,overlap*1e-7):
                record.update(status='rejected_boolean_volume_inconsistency',after=record['before'],
                              insert_unchanged=True);return False
            receiver.Shape=candidate
            changed.add(receiver_id)
            record.update(status='applied',after=state,insert_unchanged=True)
            return True
        except Exception as ex:
            record.update(status='rejected_boolean_exception',error=str(ex),after=record['before'],
                          insert_unchanged=True)
            return False
    rejected_by_receiver={}
    for receiver,insert_ids,reason in INTERFACES:
        for insert in insert_ids:
            apply(receiver,(insert,),reason)
            action=report['actions'][-1]
            if action['status'].startswith('rejected_'):
                rejected_by_receiver.setdefault(receiver,[]).append((insert,reason))
    # Failed single cuts can leave small pieces entirely occupied by another
    # explicitly specified insert. A combined known-insert pocket is tried once
    # per receiver; its full output must still be valid and exactly one solid.
    for receiver,items in rejected_by_receiver.items():
        ids=tuple(dict.fromkeys(i for i,_ in items))
        if len(ids)>1:
            apply(receiver,ids,'combined retry of explicitly identified receiving pockets','combined_retry')
    doc.recompute()
    after_hits,after_missing,after_errors=_interferences(doc,entries)
    report['after']={'interference_count':len(after_hits),'interferences':after_hits}
    report['audit_errors'].extend(after_errors)
    report['missing_parts']=sorted(set(report['missing_parts']+after_missing))
    report['changed_ids']=sorted(changed)
    report['resolved_pair_count']=len(before_hits)-len(after_hits)
    report['status']='NOMINAL_OVERLAPS_CLEARED_FIT_UNVERIFIED' if not after_hits and not report['audit_errors'] else 'PARTIAL_CLEARANCE_REQUIRES_REVIEW'
    report['applied_action_count']=sum(a['status']=='applied' for a in report['actions'])
    report['rejected_action_count']=sum(a['status'].startswith('rejected_') for a in report['actions'])
    return report,sorted(changed)
