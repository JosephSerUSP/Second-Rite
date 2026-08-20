"""The nine town attempts.

Each attempt is a composition spec, not a re-render of one blockout: street
width, facade rhythm, depth compression, foreground framing, lighting and
material strategy all vary. Attempts 01-06 diverge; 07-09 converge on the
evaluation evidence.
"""
from __future__ import annotations

# Material strategy bias per attempt. "hero" surfaces get the named strategy.
#   A = procedural,  B = public-library CC0,  C = openai-generated
ATTEMPTS = {
    # ---------------------------------------------------------------- 01
    "01": dict(
        title="Narrow stone lane, hard morning rake",
        bias="B",
        note="Tall compressed lane. Deep doorway recess. Heavy CC0 stone.",
        street=dict(width=7.0, backX=24.0, facadeX=20.6, foreX=11.0),
        lighting=dict(sunEnergy=1.35, sunColour=(1.0, 0.88, 0.70), sunElevation=34,
                      sunAzimuth=-58, sunSoftness=1.5,
                      skyColour=(0.30, 0.40, 0.58, 1.0), skyStrength=0.85),
        palette=dict(wall="lib:medieval_blocks_02", wall2="lib:castle_brick_02_white",
                     ground="lib:cobblestone_floor_02", roof="lib:clay_roof_tiles_02",
                     timber="lib:dark_wooden_planks", trim="lib:rough_pine_door",
                     metal="lib:rust_coarse_01"),
        rhythm=[(2.6, 5.4), (1.9, 4.6), (3.1, 6.2), (2.2, 5.0)],
        foreground="post",
    ),
    # ---------------------------------------------------------------- 02
    "02": dict(
        title="Wide plaster square, flat overcast",
        bias="A",
        note="Open square, quiet plaster, low contrast. Procedural-led.",
        street=dict(width=11.5, backX=27.0, facadeX=21.5, foreX=12.5),
        lighting=dict(sunEnergy=0.85, sunColour=(0.96, 0.95, 0.94), sunElevation=62,
                      sunAzimuth=-20, sunSoftness=9.0,
                      skyColour=(0.55, 0.58, 0.62, 1.0), skyStrength=1.25),
        palette=dict(wall="proc:plaster", wall2="proc:stone_blocks",
                     ground="proc:cobblestone", roof="proc:roof_tile",
                     timber="proc:wood", trim="proc:wood", metal="proc:metal"),
        rhythm=[(3.6, 4.4), (4.2, 4.0), (3.4, 4.8)],
        foreground="none",
    ),
    # ---------------------------------------------------------------- 03
    "03": dict(
        title="Carved facade terrace, late afternoon",
        bias="C",
        note="Generated ornament course carried across a terrace. Warm raking sun.",
        street=dict(width=8.5, backX=25.0, facadeX=20.0, foreX=10.5),
        lighting=dict(sunEnergy=1.5, sunColour=(1.0, 0.80, 0.56), sunElevation=22,
                      sunAzimuth=-72, sunSoftness=2.0,
                      skyColour=(0.34, 0.42, 0.60, 1.0), skyStrength=0.75),
        palette=dict(wall="gen:gen_plaster_patch", wall2="gen:gen_facade_ornament",
                     ground="lib:cobblestone_floor_02", roof="gen:gen_roof_tile",
                     timber="gen:gen_shop_timber", trim="gen:gen_shop_timber",
                     metal="proc:metal"),
        rhythm=[(2.9, 5.8), (2.4, 5.2), (2.7, 6.0), (2.1, 4.8)],
        foreground="awning",
    ),
    # ---------------------------------------------------------------- 04
    "04": dict(
        title="Timber upper storeys, deep arch",
        bias="hybrid",
        note="Jettied timber over stone base. Big arch the player walks through.",
        street=dict(width=6.2, backX=23.0, facadeX=19.4, foreX=9.5),
        lighting=dict(sunEnergy=0.855, sunColour=(1.0, 0.86, 0.66), sunElevation=41,
                      sunAzimuth=-48, sunSoftness=2.5,
                      skyColour=(0.28, 0.38, 0.56, 1.0), skyStrength=0.95),
        palette=dict(wall="lib:plastered_stone_wall", wall2="lib:medieval_blocks_02",
                     ground="lib:dirt_floor", roof="lib:clay_roof_tiles_02",
                     timber="lib:weathered_peeling_timber", trim="gen:gen_shop_timber",
                     metal="proc:metal"),
        rhythm=[(2.3, 6.4), (2.0, 6.0), (2.8, 5.6)],
        foreground="arch",
    ),
    # ---------------------------------------------------------------- 05
    "05": dict(
        title="Shopfront row, cool blue hour",
        bias="hybrid",
        note="Low warm practicals against a cold sky. Strong horizontal read.",
        street=dict(width=9.5, backX=26.0, facadeX=20.8, foreX=11.5),
        lighting=dict(sunEnergy=0.35, sunColour=(0.62, 0.72, 1.0), sunElevation=8,
                      sunAzimuth=-95, sunSoftness=8.0,
                      skyColour=(0.16, 0.22, 0.40, 1.0), skyStrength=0.75,
                      practicals=[(2.4, 0.2, 19.0, 55.0, (1.0, 0.72, 0.40)),
                                  (7.0, 0.1, 19.0, 45.0, (1.0, 0.70, 0.38)),
                                  (11.2, 0.3, 19.0, 50.0, (1.0, 0.74, 0.44))]),
        palette=dict(wall="lib:plastered_stone_wall", wall2="gen:gen_plaster_patch",
                     ground="lib:cobblestone_floor_02", roof="lib:clay_roof_tiles_02",
                     timber="gen:gen_shop_timber", trim="lib:rough_pine_door",
                     metal="proc:metal"),
        rhythm=[(2.5, 4.8), (2.2, 4.4), (2.6, 5.0), (2.3, 4.6)],
        foreground="balcony",
    ),
    # ---------------------------------------------------------------- 06
    "06": dict(
        title="Stepped hill street, strong foreground post",
        bias="hybrid",
        note="Ground climbs; heavy near-camera post splits the frame.",
        street=dict(width=8.0, backX=24.5, facadeX=20.2, foreX=8.8),
        lighting=dict(sunEnergy=1.35, sunColour=(1.0, 0.84, 0.62), sunElevation=28,
                      sunAzimuth=-66, sunSoftness=1.8,
                      skyColour=(0.32, 0.40, 0.58, 1.0), skyStrength=0.90),
        palette=dict(wall="lib:castle_brick_02_white", wall2="gen:gen_facade_ornament",
                     ground="proc:cobblestone", roof="gen:gen_roof_tile",
                     timber="lib:weathered_peeling_timber", trim="gen:gen_shop_timber",
                     metal="lib:rust_coarse_01"),
        rhythm=[(2.7, 5.2), (2.4, 5.8), (2.9, 5.0), (2.0, 5.4)],
        foreground="stairs",
    ),
}


# ---------------------------------------------------------------- staging
# (name, walker frame index, street Y, world height in metres, depth X)
# The protagonist stands on the action plane; NPCs are offset in depth so the
# side view still reads as a space rather than a line-up.
STAGING = {
    "01": [("ACTOR_protagonist", 0, 4.6, 1.70, 19.0),
           ("ACTOR_npc_a", 2, 7.4, 1.66, 19.9),
           ("ACTOR_npc_b", 4, 2.6, 1.62, 18.2)],
    "02": [("ACTOR_protagonist", 0, 5.2, 1.70, 19.0),
           ("ACTOR_npc_a", 3, 9.4, 1.64, 20.4),
           ("ACTOR_npc_b", 1, 1.7, 1.68, 18.0),
           ("ACTOR_npc_c", 5, 8.0, 1.60, 21.6)],
    "03": [("ACTOR_protagonist", 0, 4.2, 1.70, 19.0),
           ("ACTOR_npc_a", 2, 7.9, 1.66, 19.6),
           ("ACTOR_npc_b", 5, 6.2, 1.63, 18.4)],
    "04": [("ACTOR_protagonist", 0, 5.5, 1.70, 19.0),
           ("ACTOR_npc_a", 4, 3.4, 1.65, 19.4),
           ("ACTOR_npc_b", 1, 7.6, 1.61, 18.6)],
    "05": [("ACTOR_protagonist", 0, 4.0, 1.70, 19.0),
           ("ACTOR_npc_a", 2, 8.2, 1.67, 19.8),
           ("ACTOR_npc_b", 3, 6.4, 1.62, 18.3),
           ("ACTOR_npc_c", 5, 1.9, 1.59, 20.6)],
    "06": [("ACTOR_protagonist", 0, 4.8, 1.70, 19.0),
           ("ACTOR_npc_a", 3, 8.4, 1.66, 19.7),
           ("ACTOR_npc_b", 1, 2.4, 1.63, 18.5)],
}

for _k, _v in STAGING.items():
    ATTEMPTS[_k]["actors"] = _v

# 07-09 are written by the convergence step after evaluation.
