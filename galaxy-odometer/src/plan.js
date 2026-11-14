// タイムライン(ナレーション実測)→ シーン時刻・通過点・効果音イベント。
// ブラウザ(render.html)と Node(tools/export_plan.js → 音声ミックス)で同じものを使う。
(function (root) {
  const V_GAL = 227, EARTH_D = 12742, GOAL_T = EARTH_D / V_GAL;

  // メーターが実際にその距離を通過する時刻に出す「通過点」。km は検証済みの値。
  const MILESTONES = [
    { km: 400, label: '東京→大阪', big: true },      // 直線(大圏)距離の概算。東京駅起点
    { km: 1550, label: '東京→那覇' },
    { km: 3475, label: '月の直径' },                  // NASA: 平均半径 1737.4km × 2
    { km: 6200, label: '東京→ホノルル' },
    { km: 6779, label: '火星の直径' },                // NASA: 平均半径 3389.5km × 2
    { km: 9560, label: '東京→ロンドン' },
    { km: 12104, label: '金星の直径' },               // NASA: 平均半径 6051.8km × 2
  ];

  function buildPlan(TL) {
    const Q = TL.cues, c = (name, def) => (name in Q ? Q[name] : def);
    const S = {
      hook: 0,
      hit500: 500 / V_GAL,
      promise: c('promise'), suspects: c('suspects'),
      spin: c('spin1'), spinSpeed: c('spinSpeed'), sound: c('sound'), spinV: c('spin2'), spinLane: c('spinLane'),
      orbit: c('orbit1'), orbitSpeed: c('orbitSpeed'), osaka: c('osaka'), orbitV: c('orbitV'), orbitLane: c('orbitLane'),
      galaxy: c('galaxy1'), galaxyWord: c('galaxyWord'), galaxySpeed: c('galaxySpeed'), galaxyV: c('galaxyV'), match: c('match'),
      parker: c('parker'), parkerWin: c('parkerWin'),
      lap: c('lap1'), lapYears: c('lapYears'), dino: c('lap2'), dinoWord: c('dinoWord'), human: c('lap3'), humanFrac: c('humanFrac'),
      goal: c('goal'), riser: c('riser'),
      payoff: GOAL_T, loop: c('loop'), end: TL.duration,
    };
    const ms = MILESTONES.map(m => ({ ...m, t: m.km / V_GAL }));

    // 効果音: {t, name, gain, pan}
    const sfx = [];
    const add = (t, name, gain = 1, extra = {}) => { if (t != null && isFinite(t)) sfx.push({ t: Math.max(0, t), name, gain, ...extra }); };
    add(0, 'impact', 0.55);
    add(S.hit500, 'impact', 1.0);
    for (const m of ms) add(m.t, 'tick', m.big ? 0.9 : 0.6);
    add(S.promise, 'whoosh', 0.6);
    if (S.suspects != null) [0, 0.22, 0.44].forEach((d, i) => add(S.suspects + d, 'pop', 0.6, { f: 520 + i * 110 }));
    for (const k of ['spin', 'spinV', 'orbit', 'orbitV', 'galaxyV', 'parker', 'lap', 'dino', 'human', 'goal']) add(S[k] != null ? S[k] - 0.08 : null, 'whoosh', 0.5);
    add(S.spinSpeed, 'hit', 0.7); add(S.sound, 'pop', 0.6);
    add(S.spinLane != null ? S.spinLane + 0.45 : null, 'buzz', 0.7);
    add(S.orbitSpeed, 'hit', 0.7); add(S.osaka, 'pop', 0.6);
    add(S.orbitLane != null ? S.orbitLane + 0.45 : null, 'buzz', 0.7);
    add(S.galaxy != null ? S.galaxy - 1.25 : null, 'riser', 0.7, { dur: 1.25 });
    add(S.galaxy, 'subdrop', 0.9);
    add(S.galaxyWord, 'impact', 0.9);
    add(S.galaxySpeed, 'hit', 0.8);
    add(S.match, 'ding', 0.8); add(S.match, 'sparkle', 0.5);
    add(S.parkerWin, 'hit', 0.8);
    add(S.lapYears, 'impact', 0.8);
    add(S.dinoWord, 'hit', 0.6);
    add(S.humanFrac, 'hit', 0.7);
    add(GOAL_T - 2.2, 'riser', 0.85, { dur: 2.2 });
    add(GOAL_T, 'impact', 1.1); add(GOAL_T, 'ding', 0.7); add(GOAL_T + 0.05, 'sparkle', 0.6);
    sfx.sort((a, b) => a.t - b.t);
    return { S, milestones: ms, sfx, GOAL_T, duration: TL.duration };
  }

  root.buildPlan = buildPlan;
  root.MILESTONES = MILESTONES;
  if (typeof module !== 'undefined') module.exports = { buildPlan, MILESTONES };
})(typeof window !== 'undefined' ? window : globalThis);
