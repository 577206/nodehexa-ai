from generate_firmware_motion import DEST, POINT_COUNT, render


def test_generated_motion_is_current_and_bounded():
    text, reports = render()
    assert DEST.read_text() == text
    assert [report["id"] for report in reports] == [
        "hold_that_compliment",
        "gossip_radar",
        "compliment_receipt",
    ]
    assert [report["step_duration_ms"] for report in reports] == [450, 400, 400]
    assert text.count("_paths[]") == 3
    assert text.count("_entries[] { 0 }") == 3

    for report in reports:
        assert report["points"] == POINT_COUNT == 20
        assert report["starts_and_ends_at_neutral"]
        assert report["all_six_world_feet_fixed"]
        assert report["max_fk_foot_error_mm"] < 1e-9
        assert report["max_quantized_fixed_foot_error_mm"] <= 0.02
        for minimum, maximum, (lower, upper) in zip(
            report["joint_min_deg"],
            report["joint_max_deg"],
            report["joint_limits_deg"],
        ):
            assert lower <= minimum <= maximum <= upper
