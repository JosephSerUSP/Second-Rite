-- Explicit presentation profile for the #599 tiny-character experiment.
--
-- This is deliberately NOT a production character asset schema. It exists so
-- the real Map renderer can pressure-test the three prototypes before their
-- experimental bake format is promoted into Project authoring.
local player_character_visual = {}

local ROOT = "experiments/tiny-character-pipeline/renders/24x24/"

local PROFILES = {
    {
        id = "knight",
        label = "Knight / volumetric",
        dir = ROOT .. "knight_volumetric/",
    },
    {
        id = "rogue",
        label = "Rogue / faceted",
        dir = ROOT .. "rogue_faceted/",
    },
    {
        id = "mage",
        label = "Mage / compressed depth",
        dir = ROOT .. "mage_planar/",
    },
}

local BY_ID = {}
for i, profile in ipairs(PROFILES) do
    profile.index = i
    BY_ID[profile.id] = profile
end

local currentId = "knight"
local DIRECTION_NAME = { N = "north", E = "east", S = "south", W = "west" }
local WALK_FRAMES = { 1, 5, 9, 13 }

local function profileFor(id)
    local profile = BY_ID[id or currentId]
    if not profile then
        error("unknown tiny-character profile: " .. tostring(id), 3)
    end
    return profile
end

function player_character_visual.profileIds()
    local ids = {}
    for _, profile in ipairs(PROFILES) do ids[#ids + 1] = profile.id end
    return ids
end

function player_character_visual.current()
    return currentId
end

function player_character_visual.set(id)
    profileFor(id)
    currentId = id
    return profileFor(id)
end

function player_character_visual.cycle()
    local current = profileFor(currentId)
    local nextProfile = PROFILES[current.index % #PROFILES + 1]
    currentId = nextProfile.id
    return nextProfile
end

function player_character_visual.label(id)
    return profileFor(id).label
end

local function directionalStill(profile, facing)
    local direction = DIRECTION_NAME[facing]
    if not direction then error("tiny-character visual requires cardinal facing", 3) end
    return profile.dir .. "dir_" .. direction .. ".png"
end

-- #599 currently bakes one Walk action view after resetting root rotation to
-- zero, which its own turnaround vocabulary defines as SOUTH. Use four evenly
-- sampled poses from that real 16-frame bake only for south-facing movement;
-- other directions intentionally fall back to the correct directional still
-- instead of lying about directional Walk coverage.
local function southWalkFrame(profile, clock)
    local sampleIndex = math.floor((clock or 0) * 8) % #WALK_FRAMES + 1
    local frame = WALK_FRAMES[sampleIndex]
    return profile.dir .. string.format("walk_f%02d.png", frame)
end

function player_character_visual.resolve(snapshot, clock, profileId)
    if type(snapshot) ~= "table" then
        error("tiny-character visual requires a character snapshot", 2)
    end
    local profile = profileFor(profileId)
    if snapshot.clip == "walk" and snapshot.facing == "S" then
        return southWalkFrame(profile, clock)
    end
    return directionalStill(profile, snapshot.facing)
end

return player_character_visual
