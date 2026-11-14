// build/timeline.json → build/plan.json(効果音イベントとシーン時刻。音声ミックス用)
const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const TL = JSON.parse(fs.readFileSync(path.join(root, 'build', 'timeline.json'), 'utf8'));
const { buildPlan } = require(path.join(root, 'src', 'plan.js'));
const plan = buildPlan(TL);
fs.writeFileSync(path.join(root, 'build', 'plan.json'), JSON.stringify(plan, null, 1));
console.log('wrote build/plan.json', plan.sfx.length, 'sfx events, duration', plan.duration);
