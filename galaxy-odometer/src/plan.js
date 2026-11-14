// タイムライン(ナレーション実測)→ シーン時刻・通過点・効果音イベント。
// ブラウザ(render.html)と Node(tools/export_plan.js → 音声ミックス)で同じものを使う。
(function (root) {
  const V_GAL = 227, EARTH_D = 12742, GOAL_T = EARTH_D / V_GAL;

  // メーターが実際にその距離を通過する時刻に出す「通過点」(km ÷ 227 秒後)。
  // 都市間は東京駅起点の大圏(直線)距離の概算、天体は NASA の平均半径 × 2。planet はゲージにも刻む。
  const MILESTONES = [
    { km: 400, label: '東京→大阪', big: true },
    { km: 830, label: '東京→札幌' },
    { km: 1550, label: '東京→那覇' },
    { km: 3000, label: '日本列島の長さ' },
    { km: 3475, label: '月の直径', short: '月', planet: true },
    { km: 4879, label: '水星の直径', short: '水星', planet: true },
    { km: 6200, label: '東京→ホノルル' },
    { km: 6779, label: '火星の直径', short: '火星', planet: true },
    { km: 7820, label: '東京→シドニー' },
    { km: 9560, label: '東京→ロンドン' },
    { km: 10850, label: '東京→ニューヨーク' },
    { km: 12104, label: '金星の直径', short: '金星', planet: true },
  ];

  function buildPlan(TL) {
    const Q = TL.cues, c = (name) => (name in Q ? Q[name] : NaN);
    const S = {
      hook: 0, hit500: 500 / V_GAL, k1000: 1000 / V_GAL, k10000: 10000 / V_GAL,
      who: c('who'), noStop: c('noStop'), suspects: c('suspects'),
      spin: c('spin0'), spinSpeed: c('spinSpeed'), sound: c('sound'), spinV: c('spin2'), spinLane: c('spinLane'),
      orbit: c('orb0'), orbitSpeed: c('orbitSpeed'), osaka: c('orb2'), osakaSec: c('osakaSec'), orbitV: c('orb3'), orbitLane: c('orbitLane'),
      bridge: c('bridge'), bridgeNo: c('bridgeNo'),
      zoom: c('rev1'), bigger: c('bigger'),
      galaxy: c('rev2'), solar: c('solar'), turning: c('turning'),
      rev3: c('rev3'), galaxySpeed: c('galaxySpeed'), galaxyV: c('galaxyV'), match: c('match'),
      tease: c('tease'), teaseGoal: c('teaseGoal'), teaseThing: c('teaseThing'), teaseOne: c('teaseOne'),
      parker: c('parker'), parkerRec: c('parkerRec'), parkerWin: c('parkerWin'),
      lap: c('lap1'), lapYears: c('lapYears'), dino: c('lap2'), dinoWord: c('dinoWord'), human: c('lap3'), humanFrac: c('humanFrac'),
      year: c('year'), yearNum: c('yearNum'),
      never: c('never'), neverWord: c('neverWord'),
      goal: c('goal'), already: c('already'), payoff: c('payoff'), payoffOne: c('payoffOne'), behind: c('behind'), loop: c('loop'),
      goalT: GOAL_T, end: TL.duration,
    };
    const ms = MILESTONES.map(m => ({ ...m, t: m.km / V_GAL }));

    // 効果音: {t, name, gain}。映像のキューと同じ時刻を使う。
    const sfx = [];
    const add = (t, name, gain = 1, extra = {}) => { if (t != null && isFinite(t) && t < TL.duration) sfx.push({ t: Math.max(0, t), name, gain, ...extra }); };
    add(0, 'impact', 0.75);
    add(S.hit500, 'impact', 1.0);
    for (const m of ms) add(m.t, 'tick', m.big ? 0.9 : m.planet ? 0.8 : 0.55);
    add(S.who - 0.05, 'whoosh', 0.6);
    add(S.noStop, 'hit', 0.5);
    [0, 0.2, 0.4].forEach((d, i) => add(S.suspects + d, 'pop', 0.6, { f: 520 + i * 110 }));
    for (const k of ['spin', 'spinV', 'orbit', 'orbitV', 'galaxyV', 'tease', 'parker', 'lap', 'dino', 'human', 'year', 'never', 'goal']) add(S[k] - 0.08, 'whoosh', 0.5);
    add(S.spinSpeed, 'hit', 0.7); add(S.sound, 'pop', 0.6);
    add(S.spinLane + 0.5, 'buzz', 0.7);
    add(S.orbitSpeed, 'hit', 0.7); add(S.osakaSec, 'pop', 0.6);
    add(S.orbitLane + 0.5, 'buzz', 0.7);
    add(S.bridgeNo, 'buzz', 0.55);
    add(S.zoom, 'subdrop', 0.7);
    add(S.galaxy - 1.3, 'riser', 0.7, { dur: 1.3 });
    add(S.galaxy, 'impact', 1.0);
    add(S.solar, 'pop', 0.5);
    add(S.galaxySpeed, 'hit', 0.9);
    add(S.match, 'ding', 0.8); add(S.match, 'sparkle', 0.5);
    add(S.teaseGoal, 'hit', 0.6); add(S.teaseOne, 'pop', 0.6);
    add(S.parkerWin, 'hit', 0.8);
    add(S.lapYears, 'impact', 0.75);
    add(S.dinoWord, 'hit', 0.6);
    add(S.humanFrac, 'hit', 0.7);
    add(S.k10000, 'ding', 0.5);
    add(S.yearNum, 'hit', 0.7);
    add(S.neverWord, 'subdrop', 0.5);
    add(S.payoff - 2.0, 'riser', 0.8, { dur: 2.0 });
    add(S.payoff, 'impact', 1.0); add(S.payoff + 0.02, 'ding', 0.6);
    add(S.behind, 'pop', 0.5);
    add(TL.duration - 0.85, 'riser', 0.55, { dur: 0.85 });     // ループの継ぎ目へ向けて上げ、次の 0 秒のインパクトにつなぐ
    sfx.sort((a, b) => a.t - b.t);
    return { S, milestones: ms, sfx, GOAL_T, duration: TL.duration };
  }

  root.buildPlan = buildPlan;
  root.MILESTONES = MILESTONES;
  if (typeof module !== 'undefined') module.exports = { buildPlan, MILESTONES };
})(typeof window !== 'undefined' ? window : globalThis);
