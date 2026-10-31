"""Verify delivered figures still match the currently selected source files."""
from pathlib import Path
import hashlib
import json

OUT = Path(__file__).resolve().parents[1]
REPO = OUT.parents[2]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    lock = json.loads((OUT / "sources.lock.json").read_text())
    figures = json.loads((OUT / "figures_manifest.json").read_text())
    render = json.loads((OUT / "render_manifest.json").read_text())
    for record in lock["sources"]:
        assert digest(REPO / record["path"]) == record["sha256"], record["path"]
    for figure in figures["images"]:
        assert digest(OUT / figure["file"]) == figure["sha256"], figure["file"]
    assert digest(OUT / "sources.lock.json") == figures["sources_lock_sha256"]
    assert digest(OUT / "render_manifest.json") == figures["render_manifest_sha256"]
    assert digest(OUT / "source/compose_current.py") == figures["composer_sha256"]
    assert digest(OUT / "source/render_current.py") == render["renderer_sha256"]
    assert render["head_print_parts"] == lock["head_part_count"]
    assert render["oled_envelopes_shown"] == lock["head_display_modules"]
    assert len(render["body_parts"]) == 20
    result = {"status": "PASS_SOURCE_FIGURE_CORRESPONDENCE",
              "source_files": len(lock["sources"]), "figures": len(figures["images"]),
              "head_print_parts": render["head_print_parts"],
              "body_part_types_including_alternatives": len(render["body_parts"]),
              "full_assembly_validated": False, "hardware_motion_validated": False}
    (OUT / "delivery_checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
