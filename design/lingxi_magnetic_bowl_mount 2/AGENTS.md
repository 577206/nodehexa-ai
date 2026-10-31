# AGENTS.md

<INSTRUCTIONS>
This is an engineering CAD model project. Wake and use `$engineering-3d-modeling` for model creation, continuation, CAD edits, review annotations, parameter patches, preview regeneration, preview rollback, STEP export, handoff packaging, review server work, validation, and diagnostics in this directory.

Start with `validation/current_context.json` when present, or run the installed skill's `scripts/summarize_model_project.py` before broad file reads. Do not default to full history, `previous/`, or handoff package reads.

Project facts:
- Active model: 灵犀磁吸驾驶舱固定罩座
- Kind: part
- Default backend: build123d
- Short human summary: `brief.md`
- Structured authoring truth: `spec/current.yaml`, `parameters.yaml`, `source/model.py`, and validation evidence
- Review artifacts: `review/index.html`, `review/manifest.json`, `review/annotations.json`, `review/parameter_patch.json`, `review/cache/`
- Explicit STEP output: `outputs/step/` plus `outputs/step/manifest.json` after export
- Default one-step rollback: `checkpoints/preview_previous/` plus `validation/preview_revision.json`

Rules:
- Read the installed skill's `references/context-routing.md` for task tags, minimum reads, artifact boundaries, controlled modeling intent templates, and review annotation clarity gate. Do not copy that routing table into this project.
- Confirm or record the coordinate system before geometry when direction words, assemblies, fixed components, shell/lid splits, cutouts, airflow, access directions, or imported-component transforms can affect placement or fit.
- Before geometry/source edits or preview-changing regeneration, compare the current user request with `spec/current.yaml`, `parameters.yaml`, the recorded coordinate system, fixed-component placements, constraints, preserve rules, and validation targets. If the request is ambiguous, self-contradictory, conflicts with authoring truth, or has multiple geometry-valid interpretations, ask targeted clarification questions before modeling. Do not guess through blocking ambiguity; record confirmed answers in structured truth, not `brief.md`.
- Keep `brief.md` short. Do not put open questions, long requirements, parameter tables, bbox data, validation evidence, history, or agent diagnostics there.
- Treat `review/annotations.json` and `review/parameter_patch.json` as review input, not CAD truth. Do not store agent diagnostics or consumed notes in annotations.
- If a review annotation is unclear about target, operation, reference, direction, dimensions, scope, preserve rules, or validation, ask or record an explicit low-risk assumption before modeling.
- Do not hand-roll a replacement review HTML. Restore it from the installed skill template or rerun `scripts/init_model_project.py`.
- Before build123d generation, run the installed skill's `scripts/check_environment.py --json` with the same Python that will execute `source/model.py`.
- Before changing the visible HTML preview model, save a preview checkpoint. "Go back one version" means `scripts/restore_preview_revision.py`, not `previous/`.
- Prefer `scripts/regenerate_from_review.py` for saved review patches. It checkpoints the preview, applies patches, rebuilds, syncs/audits review parameters, validates, marks STEP stale, clears consumed review state after success, and refreshes current context.
- Expose only parameters with explicit trustworthy live-preview bindings. Use preview adapters for localized or topology-changing features; do not use generic morph as a fallback.
- Export usable STEP directly with `scripts/export_step.py` when the preview is satisfactory. It must block pending review input and write a fresh non-stale `outputs/step/manifest.json`.
- Create a handoff zip only when requested with `scripts/create_handoff_package.py`.
- Keep V1 scope to lightweight engineering STEP CAD. Do not add STL, 3MF, G-code, slicer, simulation, animation, or rendering deliverables unless explicitly requested.
</INSTRUCTIONS>
