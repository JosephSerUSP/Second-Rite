"""Adversarial image rater. Never logs API secrets; each call preserves evidence."""
import base64, json, os, sys, urllib.request, urllib.error
from pathlib import Path

SCORE_KEYS=['identity','silhouette','palette','shape_language','proportions','game_scale_readability','pose_clarity','animation_weight','foot_contact','locomotion_clarity','gesture_clarity','character_specific_motion','secondary_motion','face_non_uncanny','anchor_stability','render_consistency','technical_compliance','cross_character_distinctness','world_cohesion','scale_cohesion','palette_separation','silhouette_separation']
SCHEMA={"type":"object","additionalProperties":False,"properties":{
 "verdict":{"type":"string","enum":["FAIL","PASS"]},"scores":{"type":"object","additionalProperties":False,"properties":{k:{"type":"number"} for k in SCORE_KEYS},"required":SCORE_KEYS},
 "blockers":{"type":"array","items":{"type":"string"}},"high_value_changes":{"type":"array","items":{"type":"string"}},
 "optional_notes":{"type":"array","items":{"type":"string"}},"regressions_from_previous":{"type":"array","items":{"type":"string"}},
 "strongest_improvements":{"type":"array","items":{"type":"string"}},"single_most_important_next_change":{"type":"string"}},
 "required":["verdict","scores","blockers","high_value_changes","optional_notes","regressions_from_previous","strongest_improvements","single_most_important_next_change"]}
PROMPT="""You are Luna, an adversarial art director and sprite-readability critic. Do not congratulate. Judge actual 192px game scale first. Find actionable flaws: generic identity, weak silhouettes/hands, texture noise, scale cheating, floaty foot contact, anchor jitter, interpolation stiffness, missing anticipation/settle, uncanny faces, or convergence between characters. PASS only if every applicable major score is >=8, mean >=8.5, blockers empty, and no major regression. Return the requested JSON schema."""
def main():
 if len(sys.argv)<3: raise SystemExit('usage: luna_evaluate.py ROUND_DIR IMAGE...')
 if not os.getenv('OPENAI_API_KEY'): raise SystemExit('OPENAI_API_KEY is not set; no substitute evaluator is used.')
 out=Path(sys.argv[1]); out.mkdir(parents=True,exist_ok=True)
 content=[{"type":"input_text","text":PROMPT}]
 for p in map(Path,sys.argv[2:]):
  data=base64.b64encode(p.read_bytes()).decode('ascii')
  content.append({"type":"input_text","text":p.name})
  content.append({"type":"input_image","image_url":"data:image/png;base64,"+data,"detail":"original"})
 payload={"model":"gpt-5.6-luna","reasoning":{"effort":"medium"},"input":[{"role":"user","content":content}],"text":{"format":{"type":"json_schema","name":"sprite_gauntlet","strict":True,"schema":SCHEMA}}}
 req=urllib.request.Request('https://api.openai.com/v1/responses',data=json.dumps(payload).encode('utf8'),headers={"Authorization":"Bearer "+os.environ['OPENAI_API_KEY'],"Content-Type":"application/json"},method='POST')
 try:
  with urllib.request.urlopen(req,timeout=180) as f: response=json.load(f)
 except urllib.error.HTTPError as e:
  raise SystemExit('Luna API request failed: HTTP %s: %s' % (e.code,e.read().decode('utf8','replace')[:1000]))
 text=''.join(part.get('text','') for item in response.get('output',[]) for part in item.get('content',[]) if part.get('type')=='output_text')
 value=json.loads(text); (out/'luna.json').write_text(json.dumps(value,indent=2),encoding='utf8'); print(json.dumps(value,indent=2))
if __name__=='__main__': main()
