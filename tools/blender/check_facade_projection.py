"""Fast non-Blender checks for the geometry-conditioned facade protocol."""

from __future__ import annotations

import tempfile
from pathlib import Path

from facade_projection import (
    CONTROL_PACKET_VERSION,
    PROTOCOL_VERSION,
    GeneratedFacadeInput,
    ProjectionSpec,
    read_control_packet,
    validate_source_only_collection,
    write_control_packet,
)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="th_facade_check_") as temp:
        root = Path(temp)
        image = root / "facade.png"
        height = root / "height.png"
        image.write_bytes(b"external facade fixture")
        height.write_bytes(b"external height fixture")

        generated = GeneratedFacadeInput(
            image=image,
            provider="fixture-external",
            model="fixture-model",
            prompt="late-90s facade treatment",
            seed=17,
            height_image=height,
        )
        record = generated.to_record()
        assert record["image"] == "facade.png"
        assert record["heightImage"] == "height.png"
        assert "apiKey" not in record
        assert "endpoint" not in record

        spec = ProjectionSpec(
            target_objects=("SRC_BuildingMass",),
            face_indices={"SRC_BuildingMass": (0, 1, 2)},
            height_scale=0.08,
        )
        assert spec.faces_for("SRC_BuildingMass", 6) == (0, 1, 2)
        assert spec.faces_for("SRC_BuildingMass", 3) == (0, 1, 2)

        validate_source_only_collection(("TH_SOURCE",))
        try:
            validate_source_only_collection(("TH_SOURCE", "TH_RENDER"))
        except RuntimeError:
            pass
        else:
            raise AssertionError("runtime proxy collection was accepted as a displacement target")

        packet = {
            "protocolVersion": PROTOCOL_VERSION,
            "controlPacketVersion": CONTROL_PACKET_VERSION,
            "camera": {"name": "TH_CAMERA_PREVIEW"},
            "images": {"beauty": "beauty.png", "depth": "depth.exr"},
        }
        packet_path = root / "control.json"
        write_control_packet(packet_path, packet)
        assert read_control_packet(packet_path)["camera"]["name"] == "TH_CAMERA_PREVIEW"

        try:
            GeneratedFacadeInput(image=image, prompt="bad\nrecord").to_record()
        except ValueError:
            pass
        else:
            raise AssertionError("provider metadata control-character negative test did not fail")

    print("FACADE_PROJECTION_PROTOCOL OK")


if __name__ == "__main__":
    main()
