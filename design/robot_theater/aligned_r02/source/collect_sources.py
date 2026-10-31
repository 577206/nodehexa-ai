"""Read existing CAD outputs; verify provenance; compile real firmware constants.

This does not regenerate or modify CAD source, CAD review files, or manufacturing
outputs. All new derivative visualization files live in aligned_r02.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile

OUT = Path(__file__).resolve().parents[1]
REPO = OUT.parents[2]
HEAD = REPO / "design/lingxi_head_simplified"
BODY = REPO / "design/red_black_print_release_20261031"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_sources():
    mesh_path = HEAD / "review/cache/current_mesh.json"
    mesh = json.loads(mesh_path.read_text())
    provenance = mesh["provenance"]
    required = {
        "source_hash": HEAD / "source/model.py",
        "parameters_hash": HEAD / "parameters.yaml",
        "spec_hash": HEAD / "spec/current.yaml",
        "manifest_hash": HEAD / "review/manifest.json",
        "frozen_core_hash": HEAD / "source/model_R05A_archive.py",
        "visor_source_hash": HEAD / "source/visor_R05A.py",
    }
    records = []
    for key, path in required.items():
        actual = digest(path)
        if actual != provenance[key]:
            raise ValueError(f"Head mesh is stale: {path.relative_to(REPO)}")
        records.append({"path": str(path.relative_to(REPO)), "sha256": actual})
    for name, expected in provenance["module_hashes"].items():
        path = HEAD / "source" / (name + ".py")
        if digest(path) != expected:
            raise ValueError(f"Head decoration mesh is stale: {name}")
        records.append({"path": str(path.relative_to(REPO)), "sha256": expected})
    records.append({"path": str(mesh_path.relative_to(REPO)), "sha256": digest(mesh_path)})
    release = json.loads((BODY / "manifest.json").read_text())
    black = json.loads((BODY / "BLACK/manifest.json").read_text())
    for name, expected in black["body_source_hashes"].items():
        path = REPO / "design/nocturne_hexapod" / name
        if digest(path) != expected:
            raise ValueError(f"EDGE50 published mesh is stale: {name}")
        records.append({"path": str(path.relative_to(REPO)), "sha256": expected})
    for part in release["parts"] + release["optional"]:
        path = BODY / part["file"]
        if digest(path) != part["sha256"]:
            raise ValueError(f"Published part differs from manifest: {path}")
        records.append({"path": str(path.relative_to(REPO)), "sha256": part["sha256"]})
    for path in [BODY / "manifest.json", BODY / "BLACK/manifest.json"]:
        records.append({"path": str(path.relative_to(REPO)), "sha256": digest(path)})
    return records, release


def compile_profiles():
    profiles = {}
    source = OUT / "source/geometry_probe.cpp"
    with tempfile.TemporaryDirectory(prefix="nodehexa-geometry-") as tmp:
        for name, defines in [("original", []), ("edge50", ["-DNODEHEXA_CHASSIS_EDGE50", "-DNODEHEXA_BENCH_MODE"])]:
            binary = str(Path(tmp) / name)
            subprocess.run(["clang++", "-std=c++11", "-I", str(REPO / "firmware/include"),
                            *defines, str(source), "-o", binary], check=True)
            profiles[name] = json.loads(subprocess.check_output([binary], text=True))
    before, after = profiles["original"], profiles["edge50"]
    # Independent CAD dimension record supplies the required translation.
    cad = json.loads((REPO / "design/head_body_interface_20261031/dimension_basis.json").read_text())
    shift = cad["side_translation_mm"]
    assert shift == 25
    for key in ["mount_side_x_mm", "mount_corner_x_mm"]:
        assert abs(after[key] - before[key] - shift) < 1e-5, key
    assert after["mount_corner_y_mm"] == before["mount_corner_y_mm"]
    assert after["link_lengths_mm"] == before["link_lengths_mm"]
    profiles["validation"] = {"cad_side_translation_mm": shift,
                              "two_lateral_mount_coordinates_match_cad_shift": True,
                              "longitudinal_coordinate_and_link_lengths_preserved": True,
                              "physical_hole_alignment_validated": False,
                              "method": "compile and execute firmware/include/config.h for both profiles; compare against CAD dimension record"}
    return profiles


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "renders").mkdir(exist_ok=True)
    records, release = verify_sources()
    profiles = compile_profiles()
    for path in [REPO / "firmware/include/config.h", REPO / "firmware/platformio.ini",
                 OUT / "source/geometry_probe.cpp", OUT / "source/collect_sources.py",
                 OUT / "source/render_current.py", OUT / "source/compose_current.py",
                 REPO / "design/head_body_interface_20261031/dimension_basis.json"]:
        records.append({"path": str(path.relative_to(REPO)), "sha256": digest(path)})
    doc = {"revision": "R02", "status": "SOURCE_MATCHED_PREVIEW_NOT_FULL_ASSEMBLY",
           "user_confirmed_baseline": "red-black EDGE50 chassis + lingxi_head_simplified R06",
           "cad_sources_regenerated": False, "cad_sources_modified": False,
           "head_part_count": 20, "head_display_modules": 2,
           "head_display_active_area_and_pixel_resolution": "not yet confirmed by hardware measurement",
           "head_source": str((HEAD / "source/model.py").relative_to(REPO)),
           "head_mesh": str((HEAD / "review/cache/current_mesh.json").relative_to(REPO)),
           "release_manifest": str((BODY / "manifest.json").relative_to(REPO)),
           "part_types_in_main_release": len(release["parts"]),
           "firmware_geometry": profiles,
           "firmware_environment": "nodehexa-edge50-bench",
           "servo_pwm_enabled": False,
           "known_gaps": ["No complete validated six-leg assembly transforms / servo-axis alignment",
                          "No hardware-verified head / chassis / leg collisions or center of mass",
                          "Two OLED active areas, resolutions, pinout and firmware drivers unconfirmed",
                          "Theater deployment is implemented, but real assembly and hardware synchronization are not verified",
                          "Existing head preview mesh carries a nonmanifold-edge warning; source CAD not repaired in this task"],
           "sources": records}
    (OUT / "sources.lock.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    (OUT / "geometry_profiles.json").write_text(json.dumps(profiles, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"source_files_verified": len(records), "geometry_profiles": profiles}, ensure_ascii=False))


if __name__ == "__main__":
    main()
