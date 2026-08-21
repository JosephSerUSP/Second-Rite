"""Pure-Python checks for view_weighted_atlas demand policy."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from view_weighted_atlas import (  # noqa: E402
    AllocationPolicy,
    FaceObservation,
    allocate_demands,
    policy_from_preset,
)


def obs(name, *, cost, area=0.0, facing=-1.0, in_frame=False, occluded=False, weight=1.0):
    return FaceObservation(
        sample_name=name,
        sample_weight=weight,
        sample_cost=cost,
        projected_area_px=area,
        facing_cos=facing,
        in_frame=in_frame,
        occluded=occluded,
    )


def main():
    policy = AllocationPolicy(view_bias=0.85, min_density=0.05, accessibility_reserve=0.40)

    world = [1.0, 1.0, 1.0]
    envelope = [
        [
            obs("nominal", cost=0.0, area=900, facing=0.9, in_frame=True),
            obs("tilt", cost=0.35, area=760, facing=0.8, in_frame=True),
        ],
        [
            obs("nominal", cost=0.0, facing=-0.10),
            obs("tilt", cost=0.35, facing=-0.02),
        ],
        [
            obs("nominal", cost=0.0, facing=-1.0),
            obs("tilt", cost=0.35, facing=-0.92),
        ],
    ]
    demands = allocate_demands(world, envelope, policy)
    assert demands[0].density_multiplier > demands[1].density_multiplier
    assert demands[1].density_multiplier > demands[2].density_multiplier
    assert demands[1].category == "near-visible"
    assert demands[2].category == "strongly-back-facing"

    fair = allocate_demands(world, envelope, AllocationPolicy(view_bias=0.0))
    assert max(abs(d.density_multiplier - 1.0) for d in fair) < 1e-9

    larger = [list(row) for row in envelope]
    larger[1].append(obs(
        "larger-tilt", cost=0.75, area=420, facing=0.45,
        in_frame=True, weight=0.4,
    ))
    larger_demands = allocate_demands(world, larger, policy)
    assert larger_demands[1].density_multiplier > demands[1].density_multiplier

    occ = [
        [obs("nominal", cost=0.0, area=300, facing=0.8, in_frame=True, occluded=True)],
        [obs("nominal", cost=0.0, facing=-1.0)],
    ]
    occ_demands = allocate_demands([1.0, 1.0], occ, policy)
    assert occ_demands[0].density_multiplier > occ_demands[1].density_multiplier
    assert occ_demands[0].category == "occluded"

    unreachable = allocate_demands(
        [1.0, 1.0], envelope[:2], policy, explicitly_unreachable=(1,)
    )
    assert unreachable[1].category == "unreachable"
    assert unreachable[1].density_multiplier < unreachable[0].density_multiplier
    assert policy_from_preset("bounded-camera").view_bias == 0.65
    assert policy_from_preset({"viewBias": 0.5}).view_bias == 0.5

    print("VIEW_WEIGHTED_ATLAS_POLICY OK")


if __name__ == "__main__":
    main()
