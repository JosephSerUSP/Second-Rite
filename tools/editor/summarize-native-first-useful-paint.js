'use strict';
const fs = require('fs');
const path = require('path');
const cp = require('child_process');

function stat(values) {
  const a = values.filter(Number.isFinite).sort((x,y)=>x-y);
  if (!a.length) return 'n/a';
  const median = a[Math.floor(a.length/2)];
  return `${median.toFixed(2)} ms median (${a[0].toFixed(2)}–${a[a.length-1].toFixed(2)} ms, n=${a.length})`;
}
function fmt(v) { return Number.isFinite(v) ? `${v.toFixed(2)} ms` : 'n/a'; }
function esc(s) { return String(s || '').replace(/\|/g,'\\|').replace(/\r?\n/g,' '); }
function shortBase(base) { return String(base || '').slice(0,8); }

const tracePath = process.argv[2] || path.join('tmp','issue-751-native-trace.json');
const outPath = process.argv[3] || path.join('docs','reports','issue-751-native-first-useful-paint-hosted.md');
const logPath = process.argv[4] || path.join('tmp','issue-751-native-trace.log');
let body = '';
let base = cp.execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
if (fs.existsSync(tracePath)) {
  const r = JSON.parse(fs.readFileSync(tracePath,'utf8')); base = r.base || base;
  const lines = [];
  lines.push('# Thestra Studio native first-useful-paint trace — 2026-08-18','');
  lines.push(`Hosted Windows native Electron evidence for #751 on \`${shortBase(base)}\` (post-#766). The harness drives the branded Electron Database surface through Chromium CDP input; it does not patch Studio production code.`,'');
  lines.push('## Startup','');
  lines.push(`- Electron spawn → main renderer target discovered: **${fmt(r.startup.mainTargetMs)}**.`);
  lines.push(`- Electron spawn → main semantic Database boot observed: **${fmt(r.startup.mainReadyMs)}**.`);
  lines.push(`- Electron spawn → native Database surface semantic boot observed: **${fmt(r.startup.dbReadyMs)}**.`);
  lines.push(`- Page targets before opening Database: **${r.startup.pageTargetsBeforeDatabase.length}** (${r.startup.pageTargetsBeforeDatabase.map(esc).join(', ')}).`);
  const d=r.startup.nativeDataReplay;
  lines.push(`- Native-renderer \`/data\` replay: **${fmt(d.totalMs)}** total; headers ${fmt(d.headersMs)}, body ${fmt(d.bodyMs)}, JSON.parse **${fmt(d.jsonMs)}**, ${(d.bytes/1024/1024).toFixed(2)} MiB.`);
  const cats = xs => Object.entries((xs||[]).reduce((o,x)=>(o[x.category]=(o[x.category]||0)+1,o),{})).map(([k,v])=>`${k}=${v}`).join(', ') || 'none';
  lines.push(`- Main startup resources begun before semantic ready: ${cats(r.startup.mainResources)}.`);
  lines.push(`- Database startup resources begun before semantic ready: ${cats(r.startup.databaseResources)}.`,'');
  lines.push('## Entry switching','');
  lines.push('| tab | click → sync | click → first useful paint | optional completion | longest task |','|---|---:|---:|---:|---:|');
  for (const tab of ['items','units','animations']) {
    const rows=r.switches[tab].map(x=>x.summary);
    const optional=tab==='units'?rows.map(x=>x.provenanceMs):tab==='animations'?rows.map(x=>x.previewMs):[];
    lines.push(`| ${tab} | ${stat(rows.map(x=>x.syncMs))} | ${stat(rows.map(x=>x.paintMs))} | ${optional.length?stat(optional):'n/a'} | ${stat(rows.map(x=>x.longestTaskMs))} |`);
  }
  lines.push('','### Units cold/warm detail','');
  lines.push('| phase | row | sync | first useful paint | provenance | growth curves | layout/style metrics |','|---|---|---:|---:|---:|---:|---|');
  for (const x of r.switches.units.map(x=>x.summary)) {
    const p=x.perf||{};
    lines.push(`| ${esc(x.phase)} | ${esc(x.row)} | ${fmt(x.syncMs)} | ${fmt(x.paintMs)} | ${fmt(x.provenanceMs)} | ${x.growthCalls} calls / ${fmt(x.growthMs)} | layout ${fmt(p.LayoutDuration)}, style ${fmt(p.RecalcStyleDuration)} |`);
  }
  lines.push('','### Animations detail','');
  lines.push('| phase | row | sync | first useful paint | `/preview-anim` | optional timeout |','|---|---|---:|---:|---:|---|');
  for (const x of r.switches.animations.map(x=>x.summary)) lines.push(`| ${esc(x.phase)} | ${esc(x.row)} | ${fmt(x.syncMs)} | ${fmt(x.paintMs)} | ${fmt(x.previewMs)} | ${x.optionalTimedOut?'yes':'no'} |`);
  lines.push('','## Interpretation boundary','',
    '- First useful paint is a two-`requestAnimationFrame` paint opportunity after the real row click has synchronously rebuilt the form; optional image/runtime preview work is tracked separately.',
    '- Browser layout/recalc/script/task deltas come from Chromium `Performance.getMetrics`, not sleeps.',
    '- The startup resource list is filtered by request **start** time, so a runtime consultation that began before semantic boot but completed later remains visible.',
    '- This investigation does not attribute present latency to the pre-#766 expanded Three geometry path.','');
  body=lines.join('\n');
} else {
  const log=fs.existsSync(logPath)?fs.readFileSync(logPath,'utf8'):'(no harness log captured)';
  body=['# Thestra Studio native first-useful-paint trace — hosted run failed','',`No trace JSON was produced on \`${shortBase(base)}\`. Last harness output:`,'','```text',log.split(/\r?\n/).slice(-120).join('\n'),'```',''].join('\n');
}
body += `\nAgent-Signature:\n  platform: ChatGPT Web\n  model: GPT-5.6 Sol\n  role: research\n  task: "#751"\n  base: ${shortBase(base)}\n`;
fs.mkdirSync(path.dirname(outPath),{recursive:true});
fs.writeFileSync(outPath,body+'\n','utf8');
console.log(`summary: ${outPath}`);
