#!/usr/bin/env python3
"""Run external AI critics for Second Gate: Pale Crossing.
1 call to OpenAI (Luna / GPT-4o-mini or GPT-4o)
2 independent calls to OpenRouter (Free tier models)
Saves results into projects/labs/pale-crossing/CRITIQUE.md
"""
import os
import json
import urllib.request
import urllib.error

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

CRITIQUE_PROMPT = f"""You are an insightful, perceptive, and uncompromising game critic and narrative design analyst evaluating an experimental authored indie RPG campaign:
{CAMPAIGN_SUMMARY}

Please provide an honest, thorough, multi-faceted critique covering:
1. **Mechanical & Thematic Resonance**: How well does the Summoner MP traversal tension (MPD per step) interlock with the emotional attachment to Saban and the temptation of heavier summons like Cerberus?
2. **Stratum Transition & Anachronism**: How effectively does the shift from Bellroot medieval fantasy into the contemporary São Paulo Metro stratum (Estação Sé) operate? Does it maintain atmospheric coherence and uncanny surrealism?
3. **Pacing & Climax Structure**: Assess the progression from the Borrowed Room through the Three-Bell resonance, Red Dragon battle, and the dual ending choice at the Pale Crossing.
4. **Distinct Strengths & Notable Rough Edges**: What are the most memorable authored moments, and where are the potential pitfalls or design tensions?
5. **Verdict & Rating (1–5 scale)** with a one-sentence final judgment.

Write with sharp analytical clarity.
"""

def query_openai(api_key):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are Luna, an incisive narrative and gameplay critic specializing in first-person dungeon RPGs and evocative ludonarrative design."},
            {"role": "user", "content": CRITIQUE_PROMPT}
        ],
        "temperature": 0.7
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

def query_openrouter(api_key, model_name, critic_name):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/JosephSerUSP/Second-Rite",
        "X-Title": "Second Rite Pale Crossing Critique"
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": f"You are {critic_name}, an independent game designer and RPG systems critic reviewing an experimental campaign interpretation."},
            {"role": "user", "content": CRITIQUE_PROMPT}
        ],
        "temperature": 0.7
    }
    req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    with urllib.request.urlopen(req, timeout=45) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]

def main():
    openai_key = os.environ.get("OPENAI_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")

    critiques = {}

    print("Querying Critic 1: Luna (OpenAI)...")
    if openai_key:
        try:
            critiques["Luna (OpenAI GPT-4o-mini)"] = query_openai(openai_key)
            print("OK: Received Luna critique.")
        except Exception as e:
            print(f"WARN: OpenAI query failed: {e}")
            critiques["Luna (OpenAI)"] = f"Critique generation failed: {e}"
    else:
        print("WARN: OPENAI_API_KEY not found.")

    print("Querying Critic 2: OpenRouter Critic A...")
    if openrouter_key:
        models = [
            ("google/gemma-4-31b-it:free", "OpenRouter Critic A (Gemma 4 31B Free)"),
            ("nvidia/nemotron-3.5-lightning:free", "OpenRouter Critic B (Nemotron 3.5 Free)")
        ]
        for model_id, critic_title in models:
            try:
                print(f"Querying {critic_title} ({model_id})...")
                res = query_openrouter(openrouter_key, model_id, critic_title)
                critiques[critic_title] = res
                print(f"OK: Received {critic_title} critique.")
            except Exception as e:
                print(f"WARN: OpenRouter query for {model_id} failed: {e}")
                # Try fallback free model
                try:
                    fallback_id = "openai/gpt-oss-20b:free"
                    print(f"Retrying with fallback {fallback_id}...")
                    res = query_openrouter(openrouter_key, fallback_id, critic_title)
                    critiques[critic_title] = res
                    print(f"OK: Received {critic_title} critique via fallback.")
                except Exception as e2:
                    critiques[critic_title] = f"Critique generation unavailable: {e2}"

    # Build CRITIQUE.md
    output_path = "projects/labs/pale-crossing/CRITIQUE.md"
    content = "# Second Gate: Pale Crossing — External AI Critics\n\n"
    content += "> *Note: These reviews are stored as external design perspectives and hidden from top-level summaries until the owner plays and forms their own evaluation.* \n\n"
    
    for title, review in critiques.items():
        content += f"## Critique by {title}\n\n"
        content += review.strip() + "\n\n---\n\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"CRITIQUE.md written successfully to {output_path} ({len(critiques)} reviews).")

if __name__ == "__main__":
    main()
