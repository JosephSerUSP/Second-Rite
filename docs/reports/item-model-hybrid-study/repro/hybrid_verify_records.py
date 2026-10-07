"""Retain readable verification logs with original and normalized byte hashes."""
from pathlib import Path
import json,hashlib,shutil
out=Path('docs/reports/item-model-hybrid-study/verification');out.mkdir(exist_ok=True)
logs=['compile-check','compiler-tests','conformance-tests','painted-tests','g1','g2','g3','g4','unit','save','source-audit'];records={}
for name in logs:
 original=Path('out/work')/('hybrid-'+name+'.txt');raw=original.read_bytes()
 encoding='utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig'
 text=raw.decode(encoding).replace('\r\n','\n').replace('\r','\n')
 text='\n'.join(line.rstrip() for line in text.splitlines()).rstrip()+'\n'
 (out/(name+'.txt')).write_text(text,encoding='utf-8',newline='\n')
 records[name]={'log':name+'.txt','originalEncoding':encoding,'originalSHA256':hashlib.sha256(raw).hexdigest(),'retainedSHA256':hashlib.sha256((out/(name+'.txt')).read_bytes()).hexdigest()}
required={'compile-check':'ITEM BLEND COMPILE OK: 6 source(s)','compiler-tests':'Ran 16 tests','conformance-tests':'Ran 1 test','painted-tests':'Ran 11 tests','g1':'VALIDATE OK','g2':"Golden log matches for fixture 'growth'.",'g3':"Golden UI log matches for scene 'reserve'.",'g4':'Engine state doc matches.','unit':'ALL UNIT TESTS OK','save':'SAVETEST OK'}
for name,marker in required.items():assert marker in (out/(name+'.txt')).read_text(encoding='utf-8'),name;records[name]['marker']=marker
for name in ['compiler-tests','conformance-tests','painted-tests']:assert '\nOK\n' in (out/(name+'.txt')).read_text(encoding='utf-8')
record={'platform':'local Windows','blender':'5.2.2 LTS, pinned','logs':records,'unavailable':'7 native Effekseer world-effect assertions','normalization':'Decode BOM-aware original logs, normalize line endings to LF and trim trailing whitespace/empty EOF lines; retain UTF-8 review copies. Original hashes recorded separately.','limits':'G1-G4/unit/save run on fresh canonical shipping Project, not the study-only Project. No G5/G6 or Linux byte check; no baseline rewrite. Core/UV/topology evidence is local review, not aesthetic acceptance.'}
(out/'checks.json').write_text(json.dumps(record,indent=2)+'\n');shutil.copy2(Path(__file__),out.parent/'repro/hybrid_verify_records.py');print('VERIFICATION LOGS RETAINED AND SUCCESS MARKERS VERIFIED')
