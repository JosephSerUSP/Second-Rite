"""Item definitions for experimental blind review (Passes 1 to 6, 60 items total).

Each item defines:
- stem: filename stem in assets/models/items/<stem>.obj
- name: authored display name in data/items.json
- arm_a: composed LatheMesh using at least 3 distinct parts from parts.py
- arm_b: single profile LatheMesh using lathe.lathe() with no merge
"""

from __future__ import annotations

import math
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "asset-production"))

import lathe
import parts

# Canonical Materials
IRON = "wrought_iron"
GOLD = "ritual_gold"
BRONZE = "oxidized_bronze"
WOOD = "dark_wood"
CLOTH = "aged_cloth"
GLASS = "smoked_glass"
SLIME = "wet_residue"
BONE = "bone"
WAX = "wax"
CRYSTAL = "crystal"
STONE = "old_limestone"
ROUGH_STONE = "rough_limestone"


# =============================================================================
# PASS 1: Armors & Robes (1 - 10)
# =============================================================================

def pass1_adamant_armor_a():
    cuirass = parts.cylinder(0.68, 0.88, material=IRON, segments=18, name="cuirass")
    gorget = lathe.transform(parts.dome(0.48, 0.28, flatten=0.4, material=IRON, segments=16), translate=(0, 0.88, 0))
    collar_trim = lathe.transform(parts.band(0.38, 0.08, material=GOLD, segments=18), translate=(0, 1.10, 0))
    rivets = parts.scatter(parts.dome(0.08, 0.05, material=GOLD, segments=6), count=6, radius=0.62, height=0.44, jitter=0.04, name="rivets")
    return lathe.merge("adamant_armor", [cuirass, gorget, collar_trim, rivets])

def pass1_adamant_armor_b():
    profile = [(0.0, 0.55), (0.35, 0.68), (0.85, 0.65), (1.10, 0.40), (1.18, 0.35), (1.20, 0.0)]
    return lathe.lathe(profile, segments=18, material=IRON, name="adamant_armor")


def pass1_black_robe_a():
    skirt = parts.dome(0.78, 1.25, flatten=0.82, material=WOOD, segments=18, name="skirt")
    sash = lathe.transform(parts.band(0.46, 0.09, material=GOLD, segments=18), translate=(0, 0.65, 0))
    cowl = lathe.transform(parts.wrap(0.38, 0.42, sweep=0.85, material=CLOTH, segments=16), translate=(0, 0.90, 0))
    beads = parts.scatter(parts.disc(0.07, 0.04, material=GOLD, segments=6), count=5, radius=0.48, height=0.60, name="beads")
    return lathe.merge("black_robe", [skirt, sash, cowl, beads])

def pass1_black_robe_b():
    profile = [(0.0, 0.78), (0.45, 0.58), (0.70, 0.45), (1.00, 0.38), (1.25, 0.28), (1.30, 0.0)]
    return lathe.lathe(profile, segments=18, material=WOOD, name="black_robe")


def pass1_brigandine_a():
    vest = parts.cylinder(0.64, 0.96, material=CLOTH, segments=16, name="vest")
    belt = lathe.transform(parts.band(0.66, 0.08, material=IRON, segments=18), translate=(0, 0.40, 0))
    studs = parts.scatter(parts.disc(0.08, 0.03, material=IRON, segments=6), count=8, radius=0.65, height=0.70, jitter=0.06, name="studs")
    collar = lathe.transform(parts.dome(0.44, 0.22, flatten=0.45, material=IRON, segments=14), translate=(0, 0.96, 0))
    return lathe.merge("brigandine", [vest, belt, studs, collar])

def pass1_brigandine_b():
    profile = [(0.0, 0.58), (0.40, 0.64), (0.75, 0.62), (0.96, 0.48), (1.10, 0.38), (1.15, 0.0)]
    return lathe.lathe(profile, segments=16, material=CLOTH, name="brigandine")


def pass1_chainmail_a():
    hauberk = parts.cylinder(0.62, 0.92, material=IRON, segments=16, name="hauberk")
    coif = lathe.transform(parts.dome(0.46, 0.45, flatten=0.25, material=IRON, segments=14), translate=(0, 0.90, 0))
    waistband = lathe.transform(parts.band(0.64, 0.07, material=WOOD, segments=16), translate=(0, 0.38, 0))
    mantle_rings = parts.scatter(parts.band(0.10, 0.03, material=BRONZE, segments=8), count=6, radius=0.58, height=0.20, name="rings")
    return lathe.merge("chainmail", [hauberk, coif, waistband, mantle_rings])

def pass1_chainmail_b():
    profile = [(0.0, 0.60), (0.38, 0.62), (0.85, 0.56), (1.10, 0.44), (1.30, 0.20), (1.35, 0.0)]
    return lathe.lathe(profile, segments=16, material=IRON, name="chainmail")


def pass1_cocoon_husk_a():
    core = parts.teardrop(0.65, 1.35, material=BONE, segments=14, name="core")
    wrapping = lathe.transform(parts.wrap(0.68, 0.55, sweep=0.70, material=CLOTH, segments=14), translate=(0, 0.35, 0))
    spurs = parts.scatter(parts.teardrop(0.12, 0.32, material=BONE, segments=6), count=5, radius=0.56, height=0.75, jitter=0.06, name="spurs")
    stalk_ring = lathe.transform(parts.band(0.16, 0.05, material=SLIME, segments=12), translate=(0, 1.32, 0))
    return lathe.merge("cocoon_husk", [core, wrapping, spurs, stalk_ring])

def pass1_cocoon_husk_b():
    profile = [(0.0, 0.0), (0.25, 0.50), (0.65, 0.68), (1.05, 0.45), (1.35, 0.12), (1.40, 0.0)]
    return lathe.lathe(profile, segments=14, material=BONE, name="cocoon_husk")


def pass1_coral_mail_a():
    cuirass = parts.cylinder(0.62, 0.86, material=WAX, segments=16, name="cuirass")
    polyps = parts.scatter(parts.teardrop(0.14, 0.42, material=WAX, segments=7), count=6, radius=0.58, height=0.45, jitter=0.06, name="polyps")
    belt = lathe.transform(parts.band(0.64, 0.08, material=BONE, segments=16), translate=(0, 0.30, 0))
    collar = lathe.transform(parts.dome(0.46, 0.26, flatten=0.35, material=BONE, segments=14), translate=(0, 0.86, 0))
    return lathe.merge("coral_mail", [cuirass, polyps, belt, collar])

def pass1_coral_mail_b():
    profile = [(0.0, 0.56), (0.30, 0.64), (0.60, 0.60), (0.86, 0.50), (1.10, 0.35), (1.15, 0.0)]
    return lathe.lathe(profile, segments=16, material=WAX, name="coral_mail")


def pass1_cotton_robe_a():
    skirt = parts.dome(0.72, 1.20, flatten=0.76, material=STONE, segments=18, name="skirt")
    rope_belt = lathe.transform(parts.band(0.46, 0.07, material=CLOTH, segments=16), translate=(0, 0.60, 0))
    shawl = lathe.transform(parts.wrap(0.38, 0.36, sweep=0.75, material=CLOTH, segments=14), translate=(0, 0.88, 0))
    knots = parts.scatter(parts.disc(0.06, 0.04, material=WOOD, segments=6), count=5, radius=0.47, height=0.55, name="knots")
    return lathe.merge("cotton_robe", [skirt, rope_belt, shawl, knots])

def pass1_cotton_robe_b():
    profile = [(0.0, 0.72), (0.40, 0.55), (0.68, 0.44), (1.00, 0.36), (1.20, 0.26), (1.25, 0.0)]
    return lathe.lathe(profile, segments=18, material=STONE, name="cotton_robe")


def pass1_dragon_mail_a():
    torso = parts.cylinder(0.66, 0.94, material=ROUGH_STONE, segments=16, name="torso")
    horns = parts.scatter(parts.teardrop(0.16, 0.48, material=BONE, segments=7), count=4, radius=0.60, height=0.82, name="horns")
    belt = lathe.transform(parts.band(0.68, 0.09, material=GOLD, segments=16), translate=(0, 0.36, 0))
    pectoral = lathe.transform(parts.dome(0.50, 0.30, flatten=0.48, material=GOLD, segments=14), translate=(0, 0.94, 0))
    return lathe.merge("dragon_mail", [torso, horns, belt, pectoral])

def pass1_dragon_mail_b():
    profile = [(0.0, 0.58), (0.36, 0.68), (0.75, 0.65), (0.98, 0.52), (1.20, 0.34), (1.26, 0.0)]
    return lathe.lathe(profile, segments=16, material=ROUGH_STONE, name="dragon_mail")


def pass1_ether_robe_a():
    mantle = parts.dome(0.70, 1.18, flatten=0.80, material=CRYSTAL, segments=18, name="mantle")
    glowing_belt = lathe.transform(parts.band(0.44, 0.08, material=GOLD, segments=16), translate=(0, 0.62, 0))
    cowl = lathe.transform(parts.wrap(0.36, 0.38, sweep=0.80, material=GLASS, segments=14), translate=(0, 0.88, 0))
    crystals = parts.scatter(parts.teardrop(0.09, 0.22, material=CRYSTAL, segments=6), count=5, radius=0.46, height=0.72, name="crystals")
    return lathe.merge("ether_robe", [mantle, glowing_belt, cowl, crystals])

def pass1_ether_robe_b():
    profile = [(0.0, 0.70), (0.42, 0.52), (0.70, 0.42), (0.98, 0.34), (1.18, 0.25), (1.22, 0.0)]
    return lathe.lathe(profile, segments=18, material=CRYSTAL, name="ether_robe")


def pass1_flame_mail_a():
    cuirass = parts.cylinder(0.66, 0.90, material=IRON, segments=16, name="cuirass")
    flame_spires = parts.scatter(parts.teardrop(0.15, 0.44, material=GOLD, segments=6), count=5, radius=0.62, height=0.62, jitter=0.05, name="flames")
    brass_band = lathe.transform(parts.band(0.68, 0.08, material=BRONZE, segments=16), translate=(0, 0.36, 0))
    sunburst_collar = lathe.transform(parts.dome(0.46, 0.26, flatten=0.42, material=GOLD, segments=14), translate=(0, 0.90, 0))
    return lathe.merge("flame_mail", [cuirass, flame_spires, brass_band, sunburst_collar])

def pass1_flame_mail_b():
    profile = [(0.0, 0.58), (0.36, 0.68), (0.72, 0.64), (0.95, 0.48), (1.16, 0.32), (1.20, 0.0)]
    return lathe.lathe(profile, segments=16, material=IRON, name="flame_mail")


PASS_1_DEFS = [
    {"stem": "adamant_armor", "name": "Adamant Armor", "arm_a": pass1_adamant_armor_a, "arm_b": pass1_adamant_armor_b},
    {"stem": "black_robe", "name": "Black Robe", "arm_a": pass1_black_robe_a, "arm_b": pass1_black_robe_b},
    {"stem": "brigandine", "name": "Brigandine", "arm_a": pass1_brigandine_a, "arm_b": pass1_brigandine_b},
    {"stem": "chainmail", "name": "Chainmail", "arm_a": pass1_chainmail_a, "arm_b": pass1_chainmail_b},
    {"stem": "cocoon_husk", "name": "Cocoon Husk", "arm_a": pass1_cocoon_husk_a, "arm_b": pass1_cocoon_husk_b},
    {"stem": "coral_mail", "name": "Coral Mail", "arm_a": pass1_coral_mail_a, "arm_b": pass1_coral_mail_b},
    {"stem": "cotton_robe", "name": "Cotton Robe", "arm_a": pass1_cotton_robe_a, "arm_b": pass1_cotton_robe_b},
    {"stem": "dragon_mail", "name": "Dragon Mail", "arm_a": pass1_dragon_mail_a, "arm_b": pass1_dragon_mail_b},
    {"stem": "ether_robe", "name": "Ether Robe", "arm_a": pass1_ether_robe_a, "arm_b": pass1_ether_robe_b},
    {"stem": "flame_mail", "name": "Flame Mail", "arm_a": pass1_flame_mail_a, "arm_b": pass1_flame_mail_b},
]


# =============================================================================
# PASS 2: Armors, Robes & Coats (11 - 20)
# =============================================================================

def pass2_fortress_plate_a():
    chest = parts.cylinder(0.72, 0.95, material=IRON, segments=18, name="chest")
    rim = lathe.transform(parts.band(0.74, 0.12, material=BRONZE, segments=18), translate=(0, 0.45, 0))
    rivets = parts.scatter(parts.disc(0.09, 0.04, material=BRONZE, segments=6), count=8, radius=0.74, height=0.80, name="rivets")
    gorget = lathe.transform(parts.dome(0.52, 0.32, flatten=0.45, material=IRON, segments=16), translate=(0, 0.95, 0))
    return lathe.merge("fortress_plate", [chest, rim, rivets, gorget])

def pass2_fortress_plate_b():
    profile = [(0.0, 0.68), (0.45, 0.74), (0.85, 0.70), (1.05, 0.50), (1.20, 0.38), (1.24, 0.0)]
    return lathe.lathe(profile, segments=18, material=IRON, name="fortress_plate")


def pass2_hero_armor_a():
    cuirass = parts.cylinder(0.66, 0.92, material=IRON, segments=16, name="cuirass")
    gold_crest = lathe.transform(parts.dome(0.50, 0.30, flatten=0.50, material=GOLD, segments=14), translate=(0, 0.92, 0))
    sash = lathe.transform(parts.band(0.68, 0.08, material=GOLD, segments=16), translate=(0, 0.38, 0))
    star_studs = parts.scatter(parts.disc(0.08, 0.03, material=GOLD, segments=5), count=6, radius=0.64, height=0.65, name="stars")
    return lathe.merge("hero_armor", [cuirass, gold_crest, sash, star_studs])

def pass2_hero_armor_b():
    profile = [(0.0, 0.58), (0.38, 0.68), (0.75, 0.64), (0.96, 0.48), (1.18, 0.32), (1.22, 0.0)]
    return lathe.lathe(profile, segments=16, material=GOLD, name="hero_armor")


def pass2_holy_vestment_a():
    skirt = parts.dome(0.74, 1.22, flatten=0.80, material=STONE, segments=18, name="skirt")
    stole = lathe.transform(parts.wrap(0.40, 0.55, sweep=0.60, material=GOLD, segments=14), translate=(0, 0.70, 0))
    belt = lathe.transform(parts.band(0.48, 0.07, material=GOLD, segments=16), translate=(0, 0.58, 0))
    medallions = parts.scatter(parts.disc(0.08, 0.03, material=GOLD, segments=8), count=4, radius=0.46, height=0.85, name="medallions")
    return lathe.merge("holy_vestment", [skirt, stole, belt, medallions])

def pass2_holy_vestment_b():
    profile = [(0.0, 0.74), (0.45, 0.56), (0.72, 0.46), (1.02, 0.36), (1.24, 0.25), (1.28, 0.0)]
    return lathe.lathe(profile, segments=18, material=STONE, name="holy_vestment")


def pass2_leather_armor_a():
    vest = parts.cylinder(0.62, 0.90, material=WOOD, segments=14, name="vest")
    straps = lathe.transform(parts.band(0.64, 0.07, material=CLOTH, segments=14), translate=(0, 0.42, 0))
    bone_studs = parts.scatter(parts.disc(0.07, 0.03, material=BONE, segments=6), count=8, radius=0.62, height=0.68, jitter=0.04, name="studs")
    collar = lathe.transform(parts.dome(0.42, 0.20, flatten=0.40, material=WOOD, segments=12), translate=(0, 0.90, 0))
    return lathe.merge("leather_armor", [vest, straps, bone_studs, collar])

def pass2_leather_armor_b():
    profile = [(0.0, 0.55), (0.40, 0.63), (0.75, 0.60), (0.94, 0.46), (1.08, 0.35), (1.12, 0.0)]
    return lathe.lathe(profile, segments=14, material=WOOD, name="leather_armor")


def pass2_mage_robe_a():
    mantle = parts.dome(0.72, 1.20, flatten=0.78, material=GLASS, segments=18, name="mantle")
    arcane_belt = lathe.transform(parts.band(0.45, 0.08, material=BRONZE, segments=16), translate=(0, 0.62, 0))
    collar = lathe.transform(parts.wrap(0.38, 0.40, sweep=0.82, material=CLOTH, segments=14), translate=(0, 0.88, 0))
    charms = parts.scatter(parts.teardrop(0.08, 0.20, material=CRYSTAL, segments=6), count=6, radius=0.48, height=0.68, name="charms")
    return lathe.merge("mage_robe", [mantle, arcane_belt, collar, charms])

def pass2_mage_robe_b():
    profile = [(0.0, 0.72), (0.42, 0.54), (0.68, 0.44), (0.98, 0.35), (1.18, 0.24), (1.22, 0.0)]
    return lathe.lathe(profile, segments=18, material=GLASS, name="mage_robe")


def pass2_mirror_armor_a():
    cuirass = parts.cylinder(0.65, 0.88, material=IRON, segments=18, name="cuirass")
    mirror_roundel = lathe.transform(parts.disc(0.38, 0.08, bevel=0.02, material=CRYSTAL, segments=16), translate=(0, 0.48, 0))
    silver_rim = lathe.transform(parts.band(0.67, 0.07, material=BONE, segments=16), translate=(0, 0.32, 0))
    pauldrons = lathe.transform(parts.dome(0.48, 0.25, flatten=0.40, material=BONE, segments=14), translate=(0, 0.88, 0))
    return lathe.merge("mirror_armor", [cuirass, mirror_roundel, silver_rim, pauldrons])

def pass2_mirror_armor_b():
    profile = [(0.0, 0.56), (0.35, 0.66), (0.70, 0.62), (0.92, 0.46), (1.10, 0.32), (1.15, 0.0)]
    return lathe.lathe(profile, segments=18, material=CRYSTAL, name="mirror_armor")


def pass2_moth_cloak_a():
    cloak_body = parts.dome(0.76, 1.25, flatten=0.82, material=CLOTH, segments=16, name="cloak")
    fur_cowl = lathe.transform(parts.band(0.40, 0.12, material=WAX, segments=14), translate=(0, 0.95, 0))
    antennae = parts.scatter(parts.teardrop(0.09, 0.35, material=BONE, segments=6), count=4, radius=0.36, height=1.05, name="antennae")
    hem_trim = lathe.transform(parts.wrap(0.74, 0.15, sweep=1.0, material=WOOD, segments=16), translate=(0, 0.02, 0))
    return lathe.merge("moth_cloak", [cloak_body, fur_cowl, antennae, hem_trim])

def pass2_moth_cloak_b():
    profile = [(0.0, 0.76), (0.42, 0.58), (0.75, 0.46), (1.05, 0.36), (1.25, 0.22), (1.30, 0.0)]
    return lathe.lathe(profile, segments=16, material=CLOTH, name="moth_cloak")


def pass2_plate_armor_a():
    breastplate = parts.cylinder(0.66, 0.90, material=IRON, segments=18, name="breastplate")
    faulds_rim = lathe.transform(parts.band(0.68, 0.08, material=IRON, segments=18), translate=(0, 0.25, 0))
    gorget = lathe.transform(parts.dome(0.48, 0.28, flatten=0.38, material=IRON, segments=16), translate=(0, 0.90, 0))
    steel_studs = parts.scatter(parts.dome(0.08, 0.04, material=IRON, segments=6), count=6, radius=0.62, height=0.55, name="studs")
    return lathe.merge("plate_armor", [breastplate, faulds_rim, gorget, steel_studs])

def pass2_plate_armor_b():
    profile = [(0.0, 0.58), (0.35, 0.67), (0.75, 0.63), (0.95, 0.47), (1.15, 0.34), (1.20, 0.0)]
    return lathe.lathe(profile, segments=18, material=IRON, name="plate_armor")


def pass2_quarantine_coat_a():
    longcoat = parts.cylinder(0.64, 1.15, material=WOOD, segments=16, name="longcoat")
    storm_collar = lathe.transform(parts.wrap(0.40, 0.42, sweep=0.85, material=CLOTH, segments=14), translate=(0, 0.85, 0))
    utility_belt = lathe.transform(parts.band(0.66, 0.09, material=BRONZE, segments=16), translate=(0, 0.48, 0))
    ampoules = parts.scatter(parts.cylinder(0.06, 0.20, material=GLASS, segments=6), count=6, radius=0.65, height=0.42, name="ampoules")
    return lathe.merge("quarantine_coat", [longcoat, storm_collar, utility_belt, ampoules])

def pass2_quarantine_coat_b():
    profile = [(0.0, 0.64), (0.45, 0.62), (0.80, 0.54), (1.05, 0.42), (1.22, 0.30), (1.26, 0.0)]
    return lathe.lathe(profile, segments=16, material=WOOD, name="quarantine_coat")


def pass2_ring_mail_a():
    doublet = parts.cylinder(0.63, 0.90, material=CLOTH, segments=16, name="doublet")
    girdle = lathe.transform(parts.band(0.65, 0.08, material=BRONZE, segments=16), translate=(0, 0.36, 0))
    rings = parts.scatter(parts.band(0.11, 0.035, material=IRON, segments=10), count=7, radius=0.61, height=0.62, jitter=0.05, name="rings")
    collar = lathe.transform(parts.dome(0.44, 0.22, flatten=0.40, material=IRON, segments=14), translate=(0, 0.90, 0))
    return lathe.merge("ring_mail", [doublet, girdle, rings, collar])

def pass2_ring_mail_b():
    profile = [(0.0, 0.57), (0.36, 0.64), (0.72, 0.60), (0.92, 0.45), (1.10, 0.32), (1.14, 0.0)]
    return lathe.lathe(profile, segments=16, material=CLOTH, name="ring_mail")


PASS_2_DEFS = [
    {"stem": "fortress_plate", "name": "Fortress Plate", "arm_a": pass2_fortress_plate_a, "arm_b": pass2_fortress_plate_b},
    {"stem": "hero_armor", "name": "Hero Armor", "arm_a": pass2_hero_armor_a, "arm_b": pass2_hero_armor_b},
    {"stem": "holy_vestment", "name": "Holy Vestment", "arm_a": pass2_holy_vestment_a, "arm_b": pass2_holy_vestment_b},
    {"stem": "leather_armor", "name": "Leather Armor", "arm_a": pass2_leather_armor_a, "arm_b": pass2_leather_armor_b},
    {"stem": "mage_robe", "name": "Mage Robe", "arm_a": pass2_mage_robe_a, "arm_b": pass2_mage_robe_b},
    {"stem": "mirror_armor", "name": "Mirror Armor", "arm_a": pass2_mirror_armor_a, "arm_b": pass2_mirror_armor_b},
    {"stem": "moth_cloak", "name": "Moth Cloak", "arm_a": pass2_moth_cloak_a, "arm_b": pass2_moth_cloak_b},
    {"stem": "plate_armor", "name": "Plate Armor", "arm_a": pass2_plate_armor_a, "arm_b": pass2_plate_armor_b},
    {"stem": "quarantine_coat", "name": "Quarantine Coat", "arm_a": pass2_quarantine_coat_a, "arm_b": pass2_quarantine_coat_b},
    {"stem": "ring_mail", "name": "Ring Mail", "arm_a": pass2_ring_mail_a, "arm_b": pass2_ring_mail_b},
]


# =============================================================================
# PASS 3: Robes, Coats & Curios (21 - 30)
# =============================================================================

def pass3_sage_robe_a():
    body = parts.dome(0.74, 1.24, flatten=0.80, material=STONE, segments=18, name="body")
    stole = lathe.transform(parts.wrap(0.42, 0.60, sweep=0.65, material=WOOD, segments=14), translate=(0, 0.68, 0))
    sash = lathe.transform(parts.band(0.48, 0.08, material=GOLD, segments=16), translate=(0, 0.58, 0))
    bead_scatter = parts.scatter(parts.disc(0.07, 0.04, material=GOLD, segments=6), count=6, radius=0.48, height=0.82, name="beads")
    return lathe.merge("sage_robe", [body, stole, sash, bead_scatter])

def pass3_sage_robe_b():
    profile = [(0.0, 0.74), (0.44, 0.56), (0.72, 0.46), (1.02, 0.36), (1.24, 0.24), (1.28, 0.0)]
    return lathe.lathe(profile, segments=18, material=STONE, name="sage_robe")


def pass3_scale_mail_a():
    hauberk = parts.cylinder(0.64, 0.92, material=BRONZE, segments=16, name="hauberk")
    scales = parts.scatter(parts.teardrop(0.12, 0.32, material=BRONZE, segments=6), count=7, radius=0.62, height=0.55, jitter=0.05, name="scales")
    belt = lathe.transform(parts.band(0.66, 0.08, material=WOOD, segments=16), translate=(0, 0.35, 0))
    collar = lathe.transform(parts.dome(0.46, 0.24, flatten=0.38, material=BRONZE, segments=14), translate=(0, 0.92, 0))
    return lathe.merge("scale_mail", [hauberk, scales, belt, collar])

def pass3_scale_mail_b():
    profile = [(0.0, 0.58), (0.36, 0.66), (0.74, 0.61), (0.94, 0.46), (1.14, 0.32), (1.18, 0.0)]
    return lathe.lathe(profile, segments=16, material=BRONZE, name="scale_mail")


def pass3_silk_robe_a():
    kimono = parts.dome(0.70, 1.18, flatten=0.82, material=WAX, segments=18, name="kimono")
    obi = lathe.transform(parts.wrap(0.48, 0.32, sweep=0.92, material=CLOTH, segments=16), translate=(0, 0.48, 0))
    obi_cord = lathe.transform(parts.band(0.50, 0.06, material=GOLD, segments=16), translate=(0, 0.64, 0))
    sleeve_trim = parts.scatter(parts.disc(0.06, 0.03, material=GOLD, segments=6), count=6, radius=0.46, height=0.86, name="trim")
    return lathe.merge("silk_robe", [kimono, obi, obi_cord, sleeve_trim])

def pass3_silk_robe_b():
    profile = [(0.0, 0.70), (0.40, 0.54), (0.68, 0.44), (0.96, 0.34), (1.18, 0.22), (1.22, 0.0)]
    return lathe.lathe(profile, segments=18, material=WAX, name="silk_robe")


def pass3_slime_coat_a():
    fluid_body = parts.cylinder(0.65, 1.05, material=SLIME, segments=14, name="body")
    membrane_cape = lathe.transform(parts.wrap(0.52, 0.45, sweep=0.75, material=SLIME, segments=12), translate=(0, 0.75, 0))
    bubbles = parts.scatter(parts.dome(0.12, 0.10, material=CRYSTAL, segments=7), count=6, radius=0.62, height=0.48, jitter=0.06, name="bubbles")
    ooze_rim = lathe.transform(parts.band(0.66, 0.08, material=SLIME, segments=14), translate=(0, 0.20, 0))
    return lathe.merge("slime_coat", [fluid_body, membrane_cape, bubbles, ooze_rim])

def pass3_slime_coat_b():
    profile = [(0.0, 0.65), (0.35, 0.68), (0.70, 0.58), (0.98, 0.44), (1.18, 0.28), (1.24, 0.0)]
    return lathe.lathe(profile, segments=14, material=SLIME, name="slime_coat")


def pass3_tin_armor_a():
    chest = parts.cylinder(0.62, 0.86, material=STONE, segments=14, name="chest")
    flange = lathe.transform(parts.band(0.65, 0.06, material=STONE, segments=14), translate=(0, 0.28, 0))
    patches = parts.scatter(parts.disc(0.08, 0.03, material=IRON, segments=5), count=6, radius=0.61, height=0.55, jitter=0.06, name="patches")
    neck = lathe.transform(parts.dome(0.42, 0.20, flatten=0.45, material=STONE, segments=12), translate=(0, 0.86, 0))
    return lathe.merge("tin_armor", [chest, flange, patches, neck])

def pass3_tin_armor_b():
    profile = [(0.0, 0.54), (0.32, 0.63), (0.68, 0.58), (0.88, 0.44), (1.04, 0.30), (1.08, 0.0)]
    return lathe.lathe(profile, segments=14, material=STONE, name="tin_armor")


def pass3_traveler_coat_a():
    coat = parts.cylinder(0.63, 1.10, material=WOOD, segments=16, name="coat")
    capelet = lathe.transform(parts.wrap(0.48, 0.38, sweep=0.85, material=CLOTH, segments=14), translate=(0, 0.82, 0))
    belt = lathe.transform(parts.band(0.65, 0.08, material=BRONZE, segments=16), translate=(0, 0.45, 0))
    pouches = parts.scatter(parts.cylinder(0.08, 0.15, material=CLOTH, segments=6), count=5, radius=0.64, height=0.40, name="pouches")
    return lathe.merge("traveler_coat", [coat, capelet, belt, pouches])

def pass3_traveler_coat_b():
    profile = [(0.0, 0.63), (0.42, 0.60), (0.78, 0.52), (1.02, 0.40), (1.20, 0.26), (1.24, 0.0)]
    return lathe.lathe(profile, segments=16, material=WOOD, name="traveler_coat")


def pass3_wind_robe_a():
    robe = parts.dome(0.68, 1.16, flatten=0.80, material=CLOTH, segments=16, name="robe")
    gale_ring = lathe.transform(parts.band(0.44, 0.07, material=GLASS, segments=16), translate=(0, 0.60, 0))
    cowl = lathe.transform(parts.wrap(0.36, 0.36, sweep=0.75, material=STONE, segments=14), translate=(0, 0.86, 0))
    feathers = parts.scatter(parts.teardrop(0.08, 0.25, material=STONE, segments=6), count=6, radius=0.46, height=0.68, name="feathers")
    return lathe.merge("wind_robe", [robe, gale_ring, cowl, feathers])

def pass3_wind_robe_b():
    profile = [(0.0, 0.68), (0.38, 0.52), (0.66, 0.42), (0.94, 0.32), (1.14, 0.20), (1.18, 0.0)]
    return lathe.lathe(profile, segments=16, material=CLOTH, name="wind_robe")


def pass3_compass_a():
    housing = parts.disc(0.85, 0.22, bevel=0.06, material=BRONZE, segments=22, name="housing")
    bezel = parts.band(0.82, 0.12, material=GOLD, segments=22, name="bezel")
    glass_cover = lathe.transform(parts.dome(0.72, 0.12, flatten=0.6, material=GLASS, segments=18), translate=(0, 0.12, 0))
    needle_hub = lathe.transform(parts.dome(0.15, 0.10, material=IRON, segments=8), translate=(0, 0.12, 0))
    return lathe.merge("compass", [housing, bezel, glass_cover, needle_hub])

def pass3_compass_b():
    profile = [(0.0, 0.0), (0.0, 0.82), (0.12, 0.85), (0.22, 0.78), (0.26, 0.15), (0.28, 0.0)]
    return lathe.lathe(profile, segments=22, material=BRONZE, name="compass")


def pass3_copper_coin_a():
    core = parts.disc(0.82, 0.14, bevel=0.03, material=BRONZE, segments=24, name="core")
    rim = parts.band(0.78, 0.08, material=BRONZE, segments=24, name="rim")
    seal_stamp = lathe.transform(parts.dome(0.32, 0.06, flatten=0.5, material=GOLD, segments=12), translate=(0, 0.08, 0))
    edge_notches = parts.scatter(parts.cylinder(0.03, 0.14, material=BRONZE, segments=4), count=8, radius=0.81, name="notches")
    return lathe.merge("copper_coin", [core, rim, seal_stamp, edge_notches])

def pass3_copper_coin_b():
    profile = [(-0.07, 0.0), (-0.07, 0.82), (-0.03, 0.84), (0.03, 0.84), (0.07, 0.82), (0.07, 0.0)]
    return lathe.lathe(profile, segments=24, material=BRONZE, name="copper_coin")


def pass3_earplugs_a():
    plug1 = parts.teardrop(0.35, 0.70, material=WAX, segments=12, name="plug1")
    cord = lathe.transform(parts.rod(0.04, 1.2, material=CLOTH, segments=6), rotate=(0, 0, 90), translate=(-0.6, 0.35, 0))
    caps = parts.scatter(parts.disc(0.12, 0.04, material=BRONZE, segments=8), count=2, radius=0.45, height=0.35, name="caps")
    return lathe.merge("earplugs", [plug1, cord, caps])

def pass3_earplugs_b():
    profile = [(0.0, 0.12), (0.25, 0.34), (0.55, 0.30), (0.75, 0.10), (0.80, 0.0)]
    return lathe.lathe(profile, segments=12, material=WAX, name="earplugs")


PASS_3_DEFS = [
    {"stem": "sage_robe", "name": "Sage Robe", "arm_a": pass3_sage_robe_a, "arm_b": pass3_sage_robe_b},
    {"stem": "scale_mail", "name": "Scale Mail", "arm_a": pass3_scale_mail_a, "arm_b": pass3_scale_mail_b},
    {"stem": "silk_robe", "name": "Silk Robe", "arm_a": pass3_silk_robe_a, "arm_b": pass3_silk_robe_b},
    {"stem": "slime_coat", "name": "Slime Coat", "arm_a": pass3_slime_coat_a, "arm_b": pass3_slime_coat_b},
    {"stem": "tin_armor", "name": "Tin Armor", "arm_a": pass3_tin_armor_a, "arm_b": pass3_tin_armor_b},
    {"stem": "traveler_coat", "name": "Traveler Coat", "arm_a": pass3_traveler_coat_a, "arm_b": pass3_traveler_coat_b},
    {"stem": "wind_robe", "name": "Wind Robe", "arm_a": pass3_wind_robe_a, "arm_b": pass3_wind_robe_b},
    {"stem": "compass", "name": "Compass", "arm_a": pass3_compass_a, "arm_b": pass3_compass_b},
    {"stem": "copper_coin", "name": "Copper Coin", "arm_a": pass3_copper_coin_a, "arm_b": pass3_copper_coin_b},
    {"stem": "earplugs", "name": "Earplugs", "arm_a": pass3_earplugs_a, "arm_b": pass3_earplugs_b},
]


# =============================================================================
# PASS 4: Curios & Dungeon Objects (31 - 40)
# =============================================================================

def pass4_golem_shard_a():
    core = parts.dome(0.65, 0.95, flatten=0.35, material=ROUGH_STONE, segments=7, name="core")
    rune_band = lathe.transform(parts.band(0.55, 0.08, material=GOLD, segments=7), translate=(0, 0.40, 0))
    orbit_shards = parts.scatter(parts.teardrop(0.12, 0.30, material=CRYSTAL, segments=5), count=4, radius=0.62, height=0.65, name="shards")
    base_plate = parts.disc(0.70, 0.12, material=ROUGH_STONE, segments=7, name="base")
    return lathe.merge("golem_shard", [core, rune_band, orbit_shards, base_plate])

def pass4_golem_shard_b():
    profile = [(0.0, 0.65), (0.35, 0.60), (0.70, 0.42), (0.95, 0.18), (1.00, 0.0)]
    return lathe.lathe(profile, segments=7, material=ROUGH_STONE, name="golem_shard")


def pass4_iron_nail_a():
    shank = parts.rod(0.10, 1.35, material=IRON, segments=6, name="shank")
    head = lathe.transform(parts.disc(0.36, 0.12, bevel=0.04, material=IRON, segments=8), translate=(0, 1.35, 0))
    barbs = parts.scatter(parts.teardrop(0.08, 0.22, material=IRON, segments=4), count=4, radius=0.14, height=0.65, name="barbs")
    return lathe.merge("iron_nail", [shank, head, barbs])

def pass4_iron_nail_b():
    profile = [(0.0, 0.0), (0.15, 0.08), (1.20, 0.10), (1.25, 0.35), (1.35, 0.35), (1.36, 0.0)]
    return lathe.lathe(profile, segments=8, material=IRON, name="iron_nail")


def pass4_lantern_a():
    base = parts.cylinder(0.52, 0.24, material=IRON, segments=16, name="base")
    chimney = lathe.transform(parts.cylinder(0.42, 0.72, material=GLASS, segments=16), translate=(0, 0.24, 0))
    cap = lathe.transform(parts.dome(0.55, 0.30, flatten=0.3, material=IRON, segments=16), translate=(0, 0.96, 0))
    ring_handle = lathe.transform(parts.band(0.24, 0.06, material=BRONZE, segments=14), translate=(0, 1.32, 0))
    return lathe.merge("lantern", [base, chimney, cap, ring_handle])

def pass4_lantern_b():
    profile = [(0.0, 0.48), (0.24, 0.52), (0.30, 0.42), (0.90, 0.42), (1.00, 0.55), (1.22, 0.20), (1.28, 0.0)]
    return lathe.lathe(profile, segments=16, material=IRON, name="lantern")


def pass4_mimic_tongue_a():
    tongue_body = parts.teardrop(0.48, 1.30, material=SLIME, segments=12, name="tongue")
    root_ring = lathe.transform(parts.band(0.42, 0.08, material=WOOD, segments=12), translate=(0, 0.15, 0))
    teeth_studs = parts.scatter(parts.teardrop(0.08, 0.22, material=BONE, segments=5), count=6, radius=0.38, height=0.70, jitter=0.04, name="teeth")
    return lathe.merge("mimic_tongue", [tongue_body, root_ring, teeth_studs])

def pass4_mimic_tongue_b():
    profile = [(0.0, 0.35), (0.30, 0.48), (0.75, 0.42), (1.15, 0.22), (1.30, 0.0)]
    return lathe.lathe(profile, segments=12, material=SLIME, name="mimic_tongue")


def pass4_phoenix_pinion_a():
    quill = parts.rod(0.05, 1.45, material=GOLD, segments=6, name="quill")
    vane_core = lathe.transform(parts.teardrop(0.42, 1.10, material=GOLD, segments=10), translate=(0, 0.30, 0))
    ember_beads = parts.scatter(parts.disc(0.07, 0.04, material=WAX, segments=6), count=5, radius=0.28, height=0.75, name="embers")
    return lathe.merge("phoenix_pinion", [quill, vane_core, ember_beads])

def pass4_phoenix_pinion_b():
    profile = [(0.0, 0.04), (0.35, 0.25), (0.80, 0.42), (1.20, 0.22), (1.45, 0.0)]
    return lathe.lathe(profile, segments=10, material=GOLD, name="phoenix_pinion")


def pass4_provoke_badge_a():
    shield_disc = parts.disc(0.82, 0.18, bevel=0.05, material=BRONZE, segments=18, name="disc")
    mask_boss = lathe.transform(parts.dome(0.46, 0.26, flatten=0.2, material=GOLD, segments=12), translate=(0, 0.18, 0))
    spikes = parts.scatter(parts.teardrop(0.12, 0.35, material=IRON, segments=5), count=6, radius=0.82, height=0.08, name="spikes")
    return lathe.merge("provoke_badge", [shield_disc, mask_boss, spikes])

def pass4_provoke_badge_b():
    profile = [(-0.09, 0.0), (-0.09, 0.80), (0.05, 0.82), (0.15, 0.46), (0.35, 0.15), (0.38, 0.0)]
    return lathe.lathe(profile, segments=18, material=BRONZE, name="provoke_badge")


def pass4_rock_a():
    boulder = parts.dome(0.72, 0.85, flatten=0.35, material=ROUGH_STONE, segments=8, name="boulder")
    ledge = lathe.transform(parts.disc(0.78, 0.16, material=ROUGH_STONE, segments=7), translate=(0, 0.20, 0))
    fossil_nodule = lathe.transform(parts.dome(0.22, 0.14, material=BONE, segments=6), translate=(0.35, 0.55, 0))
    shards = parts.scatter(parts.teardrop(0.10, 0.18, material=STONE, segments=5), count=3, radius=0.55, height=0.35, name="shards")
    return lathe.merge("rock", [boulder, ledge, fossil_nodule, shards])

def pass4_rock_b():
    profile = [(0.0, 0.75), (0.30, 0.70), (0.60, 0.50), (0.82, 0.25), (0.86, 0.0)]
    return lathe.lathe(profile, segments=8, material=ROUGH_STONE, name="rock")


def pass4_safety_bit_a():
    wheel = parts.band(0.68, 0.14, material=BRONZE, segments=20, name="wheel")
    spokes = parts.scatter(parts.rod(0.05, 0.65, material=IRON, segments=5), count=4, radius=0.32, height=0.0, name="spokes")
    core_hub = parts.cylinder(0.22, 0.28, material=GOLD, segments=12, name="hub")
    loop = lathe.transform(parts.band(0.25, 0.06, material=GOLD, segments=14), translate=(0, 0.72, 0))
    return lathe.merge("safety_bit", [wheel, spokes, core_hub, loop])

def pass4_safety_bit_b():
    profile = [(-0.14, 0.20), (-0.14, 0.70), (0.0, 0.74), (0.14, 0.70), (0.14, 0.20), (0.0, 0.15)]
    return lathe.lathe(profile, segments=20, material=BRONZE, name="safety_bit", closed_profile=True)


def pass4_slime_core_a():
    outer_membrane = parts.teardrop(0.65, 1.20, material=SLIME, segments=14, name="membrane")
    inner_orb = lathe.transform(parts.dome(0.38, 0.50, flatten=0.1, material=CRYSTAL, segments=12), translate=(0, 0.35, 0))
    floating_nodes = parts.scatter(parts.disc(0.08, 0.05, material=GOLD, segments=6), count=4, radius=0.32, height=0.55, name="nodes")
    return lathe.merge("slime_core", [outer_membrane, inner_orb, floating_nodes])

def pass4_slime_core_b():
    profile = [(0.0, 0.0), (0.25, 0.52), (0.60, 0.65), (0.95, 0.42), (1.18, 0.12), (1.20, 0.0)]
    return lathe.lathe(profile, segments=14, material=SLIME, name="slime_core")


def pass4_sniper_eye_a():
    eyepiece = parts.cylinder(0.55, 0.32, material=BRONZE, segments=18, name="eyepiece")
    lens = lathe.transform(parts.disc(0.48, 0.06, material=GLASS, segments=18), translate=(0, 0.16, 0))
    focus_tube = lathe.transform(parts.cylinder(0.38, 0.50, material=BRONZE, segments=16), translate=(0, 0.32, 0))
    knurled_rim = lathe.transform(parts.band(0.58, 0.08, material=GOLD, segments=18), translate=(0, 0.12, 0))
    return lathe.merge("sniper_eye", [eyepiece, lens, focus_tube, knurled_rim])

def pass4_sniper_eye_b():
    profile = [(0.0, 0.55), (0.30, 0.55), (0.34, 0.38), (0.80, 0.38), (0.84, 0.42), (0.86, 0.0)]
    return lathe.lathe(profile, segments=18, material=BRONZE, name="sniper_eye")


PASS_4_DEFS = [
    {"stem": "golem_shard", "name": "Golem Shard", "arm_a": pass4_golem_shard_a, "arm_b": pass4_golem_shard_b},
    {"stem": "iron_nail", "name": "Iron Nail", "arm_a": pass4_iron_nail_a, "arm_b": pass4_iron_nail_b},
    {"stem": "lantern", "name": "Lantern", "arm_a": pass4_lantern_a, "arm_b": pass4_lantern_b},
    {"stem": "mimic_tongue", "name": "Mimic Tongue", "arm_a": pass4_mimic_tongue_a, "arm_b": pass4_mimic_tongue_b},
    {"stem": "phoenix_pinion", "name": "Phoenix Pinion", "arm_a": pass4_phoenix_pinion_a, "arm_b": pass4_phoenix_pinion_b},
    {"stem": "provoke_badge", "name": "Provoke Badge", "arm_a": pass4_provoke_badge_a, "arm_b": pass4_provoke_badge_b},
    {"stem": "rock", "name": "Rock", "arm_a": pass4_rock_a, "arm_b": pass4_rock_b},
    {"stem": "safety_bit", "name": "Safety Bit", "arm_a": pass4_safety_bit_a, "arm_b": pass4_safety_bit_b},
    {"stem": "slime_core", "name": "Slime Core", "arm_a": pass4_slime_core_a, "arm_b": pass4_slime_core_b},
    {"stem": "sniper_eye", "name": "Sniper Eye", "arm_a": pass4_sniper_eye_a, "arm_b": pass4_sniper_eye_b},
]


# =============================================================================
# PASS 5: Relics & Delicacies (41 - 50)
# =============================================================================

def pass5_star_pendant_a():
    gem = parts.disc(0.48, 0.16, bevel=0.06, material=CRYSTAL, segments=12, name="gem")
    orbit_ring = parts.band(0.72, 0.08, material=GOLD, segments=20, name="orbit")
    bail = lathe.transform(parts.band(0.20, 0.05, material=GOLD, segments=12), translate=(0, 0.85, 0))
    spurs = parts.scatter(parts.teardrop(0.08, 0.22, material=GOLD, segments=5), count=4, radius=0.55, height=0.0, name="spurs")
    return lathe.merge("star_pendant", [gem, orbit_ring, bail, spurs])

def pass5_star_pendant_b():
    profile = [(-0.08, 0.0), (-0.08, 0.65), (0.0, 0.72), (0.08, 0.65), (0.08, 0.0)]
    return lathe.lathe(profile, segments=20, material=GOLD, name="star_pendant")


def pass5_daifuku_a():
    rice_cake = parts.dome(0.82, 0.58, flatten=0.60, material=STONE, segments=18, name="cake")
    powder = parts.scatter(parts.disc(0.08, 0.03, material=WAX, segments=6), count=6, radius=0.35, height=0.52, jitter=0.05, name="powder")
    base_cup = parts.disc(0.85, 0.08, material=CLOTH, segments=18, name="cup")
    return lathe.merge("daifuku", [rice_cake, powder, base_cup])

def pass5_daifuku_b():
    profile = [(0.0, 0.78), (0.28, 0.82), (0.50, 0.62), (0.58, 0.35), (0.60, 0.0)]
    return lathe.lathe(profile, segments=18, material=STONE, name="daifuku")


def pass5_feijoada_a():
    clay_pot = parts.bowl(0.90, 0.85, wall=0.12, material=WOOD, segments=20, name="pot")
    stew_fill = lathe.transform(parts.disc(0.80, 0.06, material=IRON, segments=18), translate=(0, 0.70, 0))
    sausage_slices = parts.scatter(parts.disc(0.14, 0.05, material=WAX, segments=8), count=5, radius=0.42, height=0.74, jitter=0.05, name="sausage")
    pot_rim = lathe.transform(parts.band(0.92, 0.08, material=WOOD, segments=20), translate=(0, 0.85, 0))
    return lathe.merge("feijoada", [clay_pot, stew_fill, sausage_slices, pot_rim])

def pass5_feijoada_b():
    profile = [(0.0, 0.40), (0.10, 0.75), (0.55, 0.90), (0.85, 0.85), (0.86, 0.0)]
    return lathe.lathe(profile, segments=20, material=WOOD, name="feijoada")


def pass5_kimchi_a():
    crock_pot = parts.cylinder(0.70, 0.92, material=STONE, segments=16, name="crock")
    crock_lid = lathe.transform(parts.dome(0.74, 0.22, flatten=0.45, material=WOOD, segments=16), translate=(0, 0.92, 0))
    pot_girdle = lathe.transform(parts.band(0.72, 0.08, material=CLOTH, segments=16), translate=(0, 0.48, 0))
    peppers = parts.scatter(parts.teardrop(0.09, 0.24, material=WAX, segments=6), count=4, radius=0.55, height=0.65, name="peppers")
    return lathe.merge("kimchi", [crock_pot, crock_lid, pot_girdle, peppers])

def pass5_kimchi_b():
    profile = [(0.0, 0.55), (0.35, 0.70), (0.85, 0.68), (0.95, 0.58), (1.10, 0.35), (1.15, 0.0)]
    return lathe.lathe(profile, segments=16, material=STONE, name="kimchi")


def pass5_mana_congee_a():
    vessel = parts.bowl(0.88, 0.85, wall=0.10, material=STONE, segments=20, name="vessel")
    porridge = lathe.transform(parts.disc(0.80, 0.06, material=CRYSTAL, segments=18), translate=(0, 0.70, 0))
    seeds = parts.scatter(parts.dome(0.12, 0.08, material=GOLD, segments=7), count=6, radius=0.38, height=0.74, jitter=0.04, name="seeds")
    spoon = lathe.transform(parts.rod(0.04, 1.1, material=WOOD, segments=6), rotate=(0, 0, 75), translate=(-0.35, 0.90, 0))
    return lathe.merge("mana_congee", [vessel, porridge, seeds, spoon])

def pass5_mana_congee_b():
    profile = [(0.0, 0.38), (0.12, 0.70), (0.50, 0.88), (0.85, 0.85), (0.86, 0.0)]
    return lathe.lathe(profile, segments=20, material=STONE, name="mana_congee")


def pass5_mandrake_tempura_a():
    skewer = parts.rod(0.05, 1.55, material=WOOD, segments=6, name="skewer")
    mandrake_body = lathe.transform(parts.teardrop(0.42, 0.90, material=WAX, segments=10), translate=(0, 0.35, 0))
    crisp_bubbles = parts.scatter(parts.dome(0.12, 0.08, material=GOLD, segments=6), count=6, radius=0.44, height=0.65, jitter=0.06, name="crisp")
    return lathe.merge("mandrake_tempura", [skewer, mandrake_body, crisp_bubbles])

def pass5_mandrake_tempura_b():
    profile = [(0.0, 0.04), (0.35, 0.38), (0.75, 0.45), (1.10, 0.28), (1.50, 0.04), (1.55, 0.0)]
    return lathe.lathe(profile, segments=10, material=WAX, name="mandrake_tempura")


def pass5_moa_tamagoyaki_a():
    omelette_roll = parts.cylinder(0.68, 0.55, material=GOLD, segments=16, name="roll")
    nori_band = parts.wrap(0.70, 0.35, sweep=1.0, material=WOOD, segments=16, name="nori")
    garnish = parts.scatter(parts.disc(0.07, 0.03, material=SLIME, segments=6), count=5, radius=0.38, height=0.55, jitter=0.05, name="garnish")
    serving_mat = parts.disc(0.85, 0.08, material=CLOTH, segments=18, name="mat")
    return lathe.merge("moa_tamagoyaki", [omelette_roll, nori_band, garnish, serving_mat])

def pass5_moa_tamagoyaki_b():
    profile = [(0.0, 0.65), (0.50, 0.68), (0.58, 0.55), (0.62, 0.0)]
    return lathe.lathe(profile, segments=16, material=GOLD, name="moa_tamagoyaki")


def pass5_moonfish_moqueca_a():
    clay_pan = parts.bowl(0.92, 0.65, wall=0.10, material=WOOD, segments=22, name="pan")
    simmer_broth = lathe.transform(parts.disc(0.84, 0.06, material=WAX, segments=20), translate=(0, 0.52, 0))
    fish_chunks = parts.scatter(parts.disc(0.18, 0.08, bevel=0.03, material=BONE, segments=8), count=4, radius=0.45, height=0.56, name="fish")
    pan_rim = lathe.transform(parts.band(0.94, 0.08, material=WOOD, segments=22), translate=(0, 0.65, 0))
    return lathe.merge("moonfish_moqueca", [clay_pan, simmer_broth, fish_chunks, pan_rim])

def pass5_moonfish_moqueca_b():
    profile = [(0.0, 0.45), (0.12, 0.80), (0.45, 0.92), (0.65, 0.90), (0.66, 0.0)]
    return lathe.lathe(profile, segments=22, material=WOOD, name="moonfish_moqueca")


def pass5_pao_de_queijo_a():
    central_puff = parts.dome(0.62, 0.58, flatten=0.45, material=WAX, segments=14, name="center")
    outer_puffs = parts.scatter(parts.dome(0.38, 0.36, flatten=0.40, material=WAX, segments=10), count=4, radius=0.48, height=0.08, jitter=0.04, name="puffs")
    basket_rim = parts.band(0.88, 0.09, material=CLOTH, segments=18, name="basket")
    return lathe.merge("pao_de_queijo", [central_puff, outer_puffs, basket_rim])

def pass5_pao_de_queijo_b():
    profile = [(0.0, 0.70), (0.28, 0.75), (0.50, 0.55), (0.62, 0.28), (0.65, 0.0)]
    return lathe.lathe(profile, segments=16, material=WAX, name="pao_de_queijo")


def pass5_risotto_a():
    plate = parts.bowl(0.92, 0.45, wall=0.08, material=STONE, segments=22, name="plate")
    rice_mound = lathe.transform(parts.dome(0.72, 0.24, flatten=0.55, material=GOLD, segments=18), translate=(0, 0.35, 0))
    cheese_shavings = parts.scatter(parts.disc(0.10, 0.03, material=BONE, segments=6), count=6, radius=0.35, height=0.52, jitter=0.05, name="cheese")
    plate_flange = lathe.transform(parts.band(0.94, 0.07, material=STONE, segments=22), translate=(0, 0.45, 0))
    return lathe.merge("risotto", [plate, rice_mound, cheese_shavings, plate_flange])

def pass5_risotto_b():
    profile = [(0.0, 0.45), (0.15, 0.85), (0.40, 0.92), (0.45, 0.70), (0.52, 0.0)]
    return lathe.lathe(profile, segments=22, material=STONE, name="risotto")


PASS_5_DEFS = [
    {"stem": "star_pendant", "name": "Star Pendant", "arm_a": pass5_star_pendant_a, "arm_b": pass5_star_pendant_b},
    {"stem": "daifuku", "name": "Daifuku", "arm_a": pass5_daifuku_a, "arm_b": pass5_daifuku_b},
    {"stem": "feijoada", "name": "Feijoada", "arm_a": pass5_feijoada_a, "arm_b": pass5_feijoada_b},
    {"stem": "kimchi", "name": "Kimchi", "arm_a": pass5_kimchi_a, "arm_b": pass5_kimchi_b},
    {"stem": "mana_congee", "name": "Mana Congee", "arm_a": pass5_mana_congee_a, "arm_b": pass5_mana_congee_b},
    {"stem": "mandrake_tempura", "name": "Mandrake Tempura", "arm_a": pass5_mandrake_tempura_a, "arm_b": pass5_mandrake_tempura_b},
    {"stem": "moa_tamagoyaki", "name": "Moa Tamagoyaki", "arm_a": pass5_moa_tamagoyaki_a, "arm_b": pass5_moa_tamagoyaki_b},
    {"stem": "moonfish_moqueca", "name": "Moonfish Moqueca", "arm_a": pass5_moonfish_moqueca_a, "arm_b": pass5_moonfish_moqueca_b},
    {"stem": "pao_de_queijo", "name": "Pão de Queijo", "arm_a": pass5_pao_de_queijo_a, "arm_b": pass5_pao_de_queijo_b},
    {"stem": "risotto", "name": "Risotto", "arm_a": pass5_risotto_a, "arm_b": pass5_risotto_b},
]


# =============================================================================
# PASS 6: Consumables & Apothecary (51 - 60)
# =============================================================================

def pass6_slime_natto_a():
    bowl = parts.bowl(0.85, 0.75, wall=0.10, material=WOOD, segments=18, name="bowl")
    beans_fill = lathe.transform(parts.disc(0.75, 0.08, material=SLIME, segments=16), translate=(0, 0.60, 0))
    scallions = parts.scatter(parts.cylinder(0.06, 0.08, material=SLIME, segments=6), count=6, radius=0.38, height=0.66, jitter=0.05, name="scallions")
    chopsticks = lathe.transform(parts.rod(0.035, 1.4, material=WOOD, segments=5), rotate=(0, 0, 85), translate=(-0.5, 0.95, 0))
    return lathe.merge("slime_natto", [bowl, beans_fill, scallions, chopsticks])

def pass6_slime_natto_b():
    profile = [(0.0, 0.35), (0.12, 0.68), (0.45, 0.85), (0.75, 0.82), (0.76, 0.0)]
    return lathe.lathe(profile, segments=18, material=WOOD, name="slime_natto")


def pass6_antidote_a():
    bottle_bulb = parts.teardrop(0.55, 0.92, material=GLASS, segments=16, name="bulb")
    neck = lathe.transform(parts.cylinder(0.20, 0.40, material=GLASS, segments=14), translate=(0, 0.90, 0))
    cork = lathe.transform(parts.cylinder(0.18, 0.18, material=WOOD, segments=12), translate=(0, 1.25, 0))
    ribbon_wrap = lathe.transform(parts.wrap(0.56, 0.30, sweep=0.85, material=CLOTH, segments=16), translate=(0, 0.35, 0))
    return lathe.merge("antidote", [bottle_bulb, neck, cork, ribbon_wrap])

def pass6_antidote_b():
    profile = [(0.0, 0.28), (0.35, 0.55), (0.80, 0.42), (0.95, 0.20), (1.30, 0.20), (1.38, 0.24), (1.42, 0.0)]
    return lathe.lathe(profile, segments=16, material=GLASS, name="antidote")


def pass6_bacchus_wine_a():
    carafe = parts.teardrop(0.60, 1.05, material=GLASS, segments=16, name="carafe")
    fluted_neck = lathe.transform(parts.cylinder(0.18, 0.45, material=GLASS, segments=14), translate=(0, 1.00, 0))
    wax_seal = lathe.transform(parts.dome(0.24, 0.16, material=WAX, segments=12), translate=(0, 1.40, 0))
    vine_band = lathe.transform(parts.band(0.62, 0.08, material=GOLD, segments=16), translate=(0, 0.45, 0))
    return lathe.merge("bacchus_wine", [carafe, fluted_neck, wax_seal, vine_band])

def pass6_bacchus_wine_b():
    profile = [(0.0, 0.30), (0.45, 0.60), (0.90, 0.40), (1.05, 0.18), (1.40, 0.18), (1.48, 0.22), (1.52, 0.0)]
    return lathe.lathe(profile, segments=16, material=GLASS, name="bacchus_wine")


def pass6_echo_herbs_a():
    herb_stalks = parts.cylinder(0.38, 1.10, material=SLIME, segments=10, name="stalks")
    twine_tie = lathe.transform(parts.band(0.40, 0.08, material=CLOTH, segments=12), translate=(0, 0.55, 0))
    bell_pendant = lathe.transform(parts.dome(0.18, 0.22, flatten=0.3, material=BRONZE, segments=8), translate=(0.35, 0.50, 0))
    leaf_tips = parts.scatter(parts.teardrop(0.10, 0.28, material=SLIME, segments=5), count=5, radius=0.32, height=1.05, name="leaves")
    return lathe.merge("echo_herbs", [herb_stalks, twine_tie, bell_pendant, leaf_tips])

def pass6_echo_herbs_b():
    profile = [(0.0, 0.15), (0.35, 0.38), (0.75, 0.32), (1.05, 0.45), (1.25, 0.10), (1.30, 0.0)]
    return lathe.lathe(profile, segments=10, material=SLIME, name="echo_herbs")


def pass6_ether_seed_a():
    acorn_cup = parts.bowl(0.55, 0.45, wall=0.10, material=WOOD, segments=16, name="cup")
    crystal_kernel = lathe.transform(parts.teardrop(0.48, 0.95, material=CRYSTAL, segments=14), translate=(0, 0.25, 0))
    sprout = lathe.transform(parts.teardrop(0.12, 0.35, material=GOLD, segments=6), translate=(0, 1.15, 0))
    cup_flange = lathe.transform(parts.band(0.56, 0.06, material=WOOD, segments=16), translate=(0, 0.42, 0))
    return lathe.merge("ether_seed", [acorn_cup, crystal_kernel, sprout, cup_flange])

def pass6_ether_seed_b():
    profile = [(0.0, 0.10), (0.25, 0.52), (0.65, 0.48), (1.05, 0.22), (1.25, 0.0)]
    return lathe.lathe(profile, segments=14, material=CRYSTAL, name="ether_seed")


def pass6_hero_drink_a():
    goblet_bowl = parts.bowl(0.68, 0.72, wall=0.10, material=GOLD, segments=18, name="bowl")
    radiant_fill = lathe.transform(parts.disc(0.60, 0.06, material=CRYSTAL, segments=16), translate=(0, 0.60, 0))
    stem = lathe.transform(parts.cylinder(0.14, 0.55, material=GOLD, segments=12), translate=(0, -0.55, 0))
    foot = lathe.transform(parts.disc(0.58, 0.12, bevel=0.04, material=GOLD, segments=16), translate=(0, -0.55, 0))
    studs = parts.scatter(parts.disc(0.06, 0.03, material=CRYSTAL, segments=6), count=6, radius=0.66, height=0.68, name="studs")
    return lathe.merge("hero_drink", [goblet_bowl, radiant_fill, stem, foot, studs])

def pass6_hero_drink_b():
    profile = [(-0.55, 0.0), (-0.55, 0.55), (-0.45, 0.14), (0.0, 0.14), (0.25, 0.55), (0.65, 0.68), (0.72, 0.0)]
    return lathe.lathe(profile, segments=18, material=GOLD, name="hero_drink")


def pass6_remedy_a():
    crock_jar = parts.cylinder(0.58, 0.85, material=STONE, segments=16, name="jar")
    paper_cover = lathe.transform(parts.dome(0.62, 0.18, flatten=0.5, material=CLOTH, segments=16), translate=(0, 0.85, 0))
    twine_neck = lathe.transform(parts.band(0.54, 0.07, material=WOOD, segments=14), translate=(0, 0.82, 0))
    label_patch = lathe.transform(parts.wrap(0.60, 0.35, sweep=0.60, material=CLOTH, segments=16), translate=(0, 0.25, 0))
    return lathe.merge("remedy", [crock_jar, paper_cover, twine_neck, label_patch])

def pass6_remedy_b():
    profile = [(0.0, 0.52), (0.40, 0.58), (0.80, 0.55), (0.88, 0.46), (1.00, 0.32), (1.04, 0.0)]
    return lathe.lathe(profile, segments=16, material=STONE, name="remedy")


def pass6_sigil_ink_a():
    inkwell = parts.cylinder(0.62, 0.65, material=GLASS, segments=14, name="inkwell")
    screw_cap = lathe.transform(parts.cylinder(0.32, 0.28, material=BRONZE, segments=12), translate=(0, 0.65, 0))
    dropper_rod = lathe.transform(parts.rod(0.04, 1.25, material=GLASS, segments=6), translate=(0, 0.35, 0))
    label_band = lathe.transform(parts.wrap(0.64, 0.32, sweep=0.85, material=CLOTH, segments=14), translate=(0, 0.15, 0))
    return lathe.merge("sigil_ink", [inkwell, screw_cap, dropper_rod, label_band])

def pass6_sigil_ink_b():
    profile = [(0.0, 0.58), (0.35, 0.62), (0.65, 0.60), (0.68, 0.30), (0.90, 0.30), (0.94, 0.0)]
    return lathe.lathe(profile, segments=14, material=GLASS, name="sigil_ink")


def pass6_town_portal_a():
    parchment_roll = parts.cylinder(0.42, 1.25, material=CLOTH, segments=14, name="roll")
    top_cap = lathe.transform(parts.disc(0.46, 0.08, material=WOOD, segments=12), translate=(0, 1.25, 0))
    wax_seal = lathe.transform(parts.disc(0.22, 0.06, material=WAX, segments=10), translate=(0.42, 0.60, 0))
    ribbon = lathe.transform(parts.band(0.44, 0.07, material=GOLD, segments=14), translate=(0, 0.60, 0))
    return lathe.merge("town_portal", [parchment_roll, top_cap, wax_seal, ribbon])

def pass6_town_portal_b():
    profile = [(0.0, 0.38), (0.08, 0.42), (0.60, 0.44), (1.18, 0.42), (1.25, 0.38), (1.26, 0.0)]
    return lathe.lathe(profile, segments=14, material=CLOTH, name="town_portal")


def pass6_turbo_ether_a():
    flask_body = parts.cylinder(0.58, 0.88, material=GLASS, segments=16, name="flask")
    cage_bands = lathe.transform(parts.band(0.60, 0.07, material=GOLD, segments=16), translate=(0, 0.44, 0))
    core_orb = lathe.transform(parts.dome(0.35, 0.45, flatten=0.2, material=CRYSTAL, segments=12), translate=(0, 0.22, 0))
    lightning_rod_cap = lathe.transform(parts.teardrop(0.22, 0.55, material=GOLD, segments=8), translate=(0, 0.88, 0))
    return lathe.merge("turbo_ether", [flask_body, cage_bands, core_orb, lightning_rod_cap])

def pass6_turbo_ether_b():
    profile = [(0.0, 0.38), (0.35, 0.58), (0.75, 0.56), (0.90, 0.28), (1.25, 0.18), (1.40, 0.0)]
    return lathe.lathe(profile, segments=16, material=GLASS, name="turbo_ether")


PASS_6_DEFS = [
    {"stem": "slime_natto", "name": "Slime Natto", "arm_a": pass6_slime_natto_a, "arm_b": pass6_slime_natto_b},
    {"stem": "antidote", "name": "Antidote", "arm_a": pass6_antidote_a, "arm_b": pass6_antidote_b},
    {"stem": "bacchus_wine", "name": "Bacchus Wine", "arm_a": pass6_bacchus_wine_a, "arm_b": pass6_bacchus_wine_b},
    {"stem": "echo_herbs", "name": "Echo Herbs", "arm_a": pass6_echo_herbs_a, "arm_b": pass6_echo_herbs_b},
    {"stem": "ether_seed", "name": "Ether Seed", "arm_a": pass6_ether_seed_a, "arm_b": pass6_ether_seed_b},
    {"stem": "hero_drink", "name": "Hero Drink", "arm_a": pass6_hero_drink_a, "arm_b": pass6_hero_drink_b},
    {"stem": "remedy", "name": "Remedy", "arm_a": pass6_remedy_a, "arm_b": pass6_remedy_b},
    {"stem": "sigil_ink", "name": "Sigil Ink", "arm_a": pass6_sigil_ink_a, "arm_b": pass6_sigil_ink_b},
    {"stem": "town_portal", "name": "Town Portal", "arm_a": pass6_town_portal_a, "arm_b": pass6_town_portal_b},
    {"stem": "turbo_ether", "name": "Turbo Ether", "arm_a": pass6_turbo_ether_a, "arm_b": pass6_turbo_ether_b},
]

ALL_PASSES = [
    PASS_1_DEFS,
    PASS_2_DEFS,
    PASS_3_DEFS,
    PASS_4_DEFS,
    PASS_5_DEFS,
    PASS_6_DEFS,
]
