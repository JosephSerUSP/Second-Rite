#!/usr/bin/env python3
import os
import json
import urllib.request

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY")

CAMPAIGN_SUMMARY = """
Title: Second Gate: Pale Crossing
Format: Complete, compressed, playable campaign interpretation (First-person dungeon RPG / Thestra Project).
Playtime: 45–75 minutes.

Protagonist & Core Economy:
- Protagonist is an outsider Summoner arriving at the border village of St. Maria with their bonded starting companion: Saban, a Level 3 Moa specializing in Cooking discipline.
- Summoner Traversal Economy: Summons exert MP Drain (MPD) on every step taken in the labyrinth. Saban drains 2 MPD while providing combat utility and warm, grounding camp dialogue.
- Optional High-Risk Contracts:
  * Cerberus (Level 4, Fire Claw, ATK 28) offers massive damage but a punishing MPD 6 drain.
  * Daphne (Level 3, Undine Healer) provides water recovery with moderate MPD 4 drain.
- Managing summon party composition against remaining MP dictates how deep an expedition can safely reach before forcing a retreat to St. Maria.

Campaign Trajectory & Stratum Progression:
1. Act I: St. Maria Hub & Bellroot Entry (Maps 1 & 2)
   - St. Maria: Room 3 in Passage House (resting with Saban), Registrar Celina issuing Crossing Writ #198, Alicia (bakery & lunch errand to forge), Laura (blacksmith), Geraldo (tavern rumors), Sister Agnes (chapel vigil).
   - Floor 1 (Entry Vault): Ines's chalk mark ("SENI" — warning about MP depletion), first contract chamber (Cerberus challenge), treasure cache, stairs down.

2. Act I (cont.): Bellroot Chasm (Map 3)
   - Floor 2: The Salt Table (harvesting Bell Salt to restore summon skill charges), Daphne's spring alcove (optional recruitment), Bellroot Recovery Font.
   - The Rupture Hatch: A massive industrial yellow steel bulkhead door hissing with pneumatic pressure and smelling of ozone and subway rail.

3. Act II: Subterranean Rupture — São Paulo Metro Stratum (Maps 4 & 5)
   - Floor 3 (Estação Sé — Concourse): Authentic bilingual signage, fluorescent flicker, turnstiles (Catracas) locked by optical reader, ticket booth granting Item 208: Metro Transit Pass, PA speaker echoing 'Atenção passageiros. Permaneçam atrás da faixa amarela.'
   - Floor 4 (Platform 2 & Ghost Tracks): Abandoned commuter train with Item 209: Lost Commuter's Bag, sub-boss battle against Guardian Talos (concrete and rebar construct blocking the rails), and the Astral Breach where subway rails terminate into a starry chasm.

4. Revisit: The Vigil of the Bells in St. Maria
   - Bellroot bells ring across the valley; twilight prayer in chapel; Yukio reflects on summoner survival; acquisition of Thestra Lantern.

5. Act III: The Rusted Choir & Pale Crossing (Maps 6, 7 & 8)
   - Floor 5 (The Rusted Choir): Cathedral spires intersecting suspended subway rails.
     * The Borrowed Room: An exact replica of Room 3 from St. Maria, where Saban's feather is found, granting +50 Max HP and deep emotional grounding.
     * The Three-Bell Resonance: Bell of Salt (West) + Bell of Iron (East) harmonized at the Bell of Dusk (Center) to rumble open the Ashen Gate.
     * Stratum Boss: Ashen Guardian / Red Dragon (Level 10) guarding the First Scale.
   - Floor 6 (The Pale Crossing): Thestra Seam pedestal suspended over the astral void.
     * Choice A: Return with Saban & Seal the Pale Gate (re-emerging into morning light at St. Maria).
     * Choice B: Cross the Boundary & Awaken the Second Rite (stepping into the infinite tapestry of the Gate).
   - Map 8 (Epilogue — The Morning After): Authored resolution crawl detailing the fates of St. Maria, Alicia, Laura, Celina, Yukio, and the enduring bond with Saban.
"""

CRITIQUE_PROMPT = f"""You are an insightful, perceptive, and uncompromising game critic evaluating an experimental authored indie RPG campaign:
{CAMPAIGN_SUMMARY}

Please provide a structured critical review covering:
1. **Mechanical & Thematic Resonance**: Summoner MP traversal tension (MPD per step) vs emotional attachment to Saban and temptation of heavy summons (Cerberus/Daphne).
2. **Stratum Transition & Anachronism**: Shift from Bellroot into the São Paulo Metro stratum (Estação Sé).
3. **Pacing & Climax Structure**: Progression through the Borrowed Room, 3-Bell resonance, Red Dragon battle, and dual ending.
4. **Distinct Strengths & Notable Rough Edges**: Key highlights and potential design tensions.
5. **Verdict & Rating (1–5 scale)** with a one-sentence final judgment.
"""

def query(model):
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps({
            "model": model,
            "messages": [
                {"role": "system", "content": "You are an incisive indie RPG systems and narrative critic."},
                {"role": "user", "content": CRITIQUE_PROMPT}
            ],
            "max_tokens": 1000
        }).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_KEY}"
        }
    )
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

def main():
    critique_path = "projects/labs/pale-crossing/CRITIQUE.md"
    with open(critique_path, "r", encoding="utf-8") as f:
        current = f.read()

    base_content = current.split("## Critique by OpenRouter")[0].strip()

    # Query Critic A
    print("Fetching Critic A (poolside/laguna-xs-2.1:free)...", flush=True)
    try:
        rev_a = query("poolside/laguna-xs-2.1:free")
        base_content += f"\n\n---\n\n## Critique by OpenRouter Critic A (Laguna XS Free)\n\n{rev_a.strip()}\n"
        print("OK: Critic A fetched.", flush=True)
    except Exception as e:
        print(f"Error Critic A: {e}", flush=True)

    # Query Critic B
    print("Fetching Critic B (dots-studio/dots-3-note-preview:free)...", flush=True)
    try:
        rev_b = query("dots-studio/dots-3-note-preview:free")
        base_content += f"\n\n---\n\n## Critique by OpenRouter Critic B (Dots 3 Free)\n\n{rev_b.strip()}\n"
        print("OK: Critic B fetched.", flush=True)
    except Exception as e:
        print(f"Error Critic B: {e}", flush=True)
        # Try fallback
        try:
            print("Retrying Critic B with nvidia/nemotron-3.5-lightning:free...", flush=True)
            rev_b = query("nvidia/nemotron-3.5-lightning:free")
            base_content += f"\n\n---\n\n## Critique by OpenRouter Critic B (Nemotron 3.5 Free)\n\n{rev_b.strip()}\n"
            print("OK: Critic B fallback fetched.", flush=True)
        except Exception as e2:
            print(f"Error Critic B fallback: {e2}", flush=True)

    with open(critique_path, "w", encoding="utf-8") as f:
        f.write(base_content + "\n")
    print("Successfully updated CRITIQUE.md!", flush=True)

if __name__ == "__main__":
    main()
