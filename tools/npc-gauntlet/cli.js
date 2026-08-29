#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const http = require('http');
const lab = require('./server');
const source = require('./lib/sources');

function usage() { return 'Usage: node tools/npc-gauntlet/cli.js serve --project <root> [--port 4177]\n       node tools/npc-gauntlet/cli.js sources --project <root>\n       node tools/npc-gauntlet/cli.js preflight --project <root> --experiment <file.json>\n'; }
function value(args, key) { const i = args.indexOf(key); return i < 0 ? null : args[i + 1]; }
async function main(argv) {
    if (argv.includes('--help') || argv.includes('-h')) { process.stdout.write(usage()); return 0; }
    const command = argv[0] && !argv[0].startsWith('--') ? argv[0] : 'serve'; const args = command === 'serve' ? argv : argv.slice(1); const project = value(args, '--project');
    if (!project) throw new Error('--project is required');
    if (command === 'sources') { console.log(JSON.stringify({ sources: source.discoverSources(project), candidates: source.npcCandidates(project) }, null, 2)); return 0; }
    if (command === 'preflight') { const file = value(args, '--experiment'); if (!file) throw new Error('--experiment is required'); console.log(JSON.stringify(await lab.preflight({ projectRoot: project, experiment: JSON.parse(fs.readFileSync(path.resolve(file), 'utf8')) }), null, 2)); return 0; }
    if (command !== 'serve') throw new Error(`unknown command '${command}'`);
    const port = value(args, '--port') || '4177', parsed = lab.parseArgs(['--project', project, '--port', port]), app = lab.createApp({ projectRoot: parsed.project }), listener = http.createServer(app.handler);
    await new Promise((resolve, reject) => { listener.once('error', reject); listener.listen(parsed.port, parsed.host, resolve); });
    console.log(`NPC Gauntlet Lab running at http://${parsed.host}:${parsed.port}`);
    await new Promise(resolve => { const stop = () => listener.close(resolve); process.once('SIGINT', stop); process.once('SIGTERM', stop); }); return 0;
}
if (require.main === module) main(process.argv.slice(2)).then(code => { process.exitCode = code; }).catch(error => { process.stderr.write(`NPC Gauntlet Lab failed: ${error.message}\n${usage()}`); process.exitCode = 1; });
module.exports = { main, usage };
