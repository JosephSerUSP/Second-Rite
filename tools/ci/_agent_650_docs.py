from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def replace_exact(path, old, new):
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected exactly one target, found {count}")
    p.write_text(text.replace(old, new), encoding="utf-8")
    print(f"updated {path}")


replace_exact(
    "docs/design/combat-state-resources.md",
    "Most of the previous excess vitality is now ordinary HP capacity; only 5 HP is\nstill above Max HP.",
    "In the intended numeric model, most of that excess vitality becomes ordinary HP\ncapacity; only 5 HP remains above Max HP.",
)

replace_exact(
    "docs/game design/Summoner.md",
    "MP is now the central resource of the whole game, not just a spell-cost meter. Active creatures continuously drain it just by being on the field. Creature spells cost it. Summoning a creature spends it. Sacrificing a creature refunds some of it back, scaled by the sacrificed creature's level. If MP hits zero mid-battle, the bond between summoner and creatures frays — active creatures start suffering per-round damage or penalties (the old MP-exhaustion-damage concept, redirected from the summoner onto the party). A battle is lost only when every active creature is dead; MP running dry is dangerous pressure, not an instant loss.",
    "MP is intended to remain the Summoner's central resource rather than only a spell-cost meter, but its spend model is still under active design in #372 and #373. The current prototype direction is to avoid charging party MPD merely for ordinary traversal, charge manifestation/activation around battle entry, and make Veil-style encounter avoidance a deliberate traversal sink; prolonged-battle Strain may remain as separate anti-stall pressure. Exact activation and Veil costs, starting Max MP, progression, restoration pacing, and zero-MP consequences are not settled by this document.",
)

print("#650 genuine status assertions corrected")
