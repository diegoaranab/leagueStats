const params = new URLSearchParams(location.search);
const direction = params.get('direction') === 'b' ? 'b' : 'a';
const face = ['paired', 'current'].includes(params.get('type')) ? params.get('type') : 'space';
const roles = {top:'Top', jungle:'Jungle', middle:'Mid', bottom:'ADC', support:'Support'};
const options = {
  region:{na:'North America', lan:'Latin America North', las:'Latin America South'},
  rank:{iron:'Iron', bronze:'Bronze', silver:'Silver', gold:'Gold', platinum:'Platinum', emerald:'Emerald', diamond:'Diamond', master:'Master'},
  window:{current:'Current patch', '7d':'Last 7 days', '14d':'Last 14 days'},
  difficulty:{all:'All levels', easy:'Easy', medium:'Medium', hard:'Hard'},
  order:{rank:'Pick ranking', win_rate:'Win rate', pick_rate:'Pick rate', difficulty:'Difficulty', ban:'Ban priority'}
};
const modeLabels = {solo:'Solo Queue', team:'Flex / Clash'};
const descriptions = {solo:'Ranked ladder picks and bans.', team:'Draft picks, bans and team lineup.'};
const state = {
  screen:['solo','team'].includes(params.get('screen')) ? params.get('screen') : 'home',
  mode:params.get('queue') === 'team' || params.get('screen') === 'team' ? 'team' : 'solo',
  region:params.get('region') || 'na',
  rank:params.get('rank') || 'diamond',
  window:params.get('window') || '7d',
  role:params.get('role') in roles ? params.get('role') : 'top',
  order:params.get('order') in options.order ? params.get('order') : 'rank',
  difficulty:params.get('difficulty') in options.difficulty ? params.get('difficulty') : 'all',
  view:direction === 'b' && params.get('screen') === 'team' && params.get('view') === 'draft' ? 'draft' : 'picks',
  inspected:null
};
const app = document.querySelector('#app');
document.body.className = direction + ' type-' + face;
const iconPaths = {
  arrow:'M4 12h15m-6-6 6 6-6 6',
  chevron:'m9 5 7 7-7 7',
  down:'m6 9 6 6 6-6',
  check:'m5 12 4 4L19 6',
  top:'M5 19V5h14M19 9v10H9',
  jungle:'m12 3 6 8-6 10-6-10Zm0 0v18',
  middle:'M5 19 19 5M5 12V5h7m0 14h7v-7',
  bottom:'M19 5v14H5M5 15V5h10',
  support:'m3 8 6 2 3-5 3 5 6-2-4 7-5 4-5-4Z',
  ban:'M6.3 6.3l11.4 11.4M20 12a8 8 0 1 1-16 0 8 8 0 0 1 16 0Z',
  lineup:'M4 7h16M4 12h16M4 17h16',
  warning:'M12 8v5m0 3v.1M3 19 12 4l9 15Z',
  sliders:'M4 7h16M4 17h16M8 4v6m8 4v6'
};

function icon(name) {
  return '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="' + iconPaths[name] + '"/></svg>';
}
function text(str) {
  return String(str).replace(/[&<>"']/g, c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
}
function href(screen, extra = {}) {
  const values = {direction, screen, type:face === 'space' ? null : face,
    queue:screen === 'home' ? state.mode : null, region:state.region === 'na' ? null : state.region,
    rank:state.rank === 'diamond' ? null : state.rank, window:state.window === '7d' ? null : state.window,
    role:state.role === 'top' || screen === 'home' ? null : state.role,
    order:state.order !== 'rank' && screen === state.screen ? state.order : null,
    difficulty:state.difficulty !== 'all' && screen === state.screen ? state.difficulty : null,
    ...extra};
  return '?' + new URLSearchParams(Object.entries(values).filter(([,value]) => value)).toString();
}
function portrait(c, size = 46) {
  return '<img class="portrait" src="assets/' + text(c.portrait) + '" alt="" width="' + size + '" height="' + size + '">';
}
function headingControls() {
  return '<header class="topbar"><div class="wrap top-inner"><a class="wordmark" href="' + href('home', {queue:'solo'}) +
    '"><span class="mark" aria-hidden="true"><i></i><i></i><i></i></span>LeagueStats</a>' +
    (state.screen === 'home' ? '<span class="header-note">League of Legends</span>' :
    '<nav class="queue-nav" aria-label="Queue"><a ' + (state.mode === 'solo' ? 'aria-current="page" ' : '') + 'href="' +
    href('solo') + '">Solo</a><a ' + (state.mode === 'team' ? 'aria-current="page" ' : '') + 'href="' +
    href('team') + '">Flex / Clash</a></nav>') + '</div></header>';
}
function select(key, label, list = options[key]) {
  return '<label class="field"><span>' + label + '</span><span class="select-wrap"><select name="' + key + '">' +
    Object.entries(list).map(([value, name]) => '<option value="' + value + '"' +
      (value === state[key] ? ' selected' : '') + '>' + name + '</option>').join('') + '</select>' +
    '<span class="field-value" aria-hidden="true"><span>' + text(list[state[key]] || list[Object.keys(list)[0]]) +
    '</span>' + icon('down') + '</span></span></label>';
}
function setup() {
  return '<form class="setup" aria-label="Match setup"><fieldset><legend>Queue</legend><div class="mode-options">' +
    Object.entries(modeLabels).map(([mode, name]) =>
      '<label class="mode-choice"><input type="radio" name="queue" value="' + mode + '"' +
      (mode === state.mode ? ' checked' : '') + '><span><strong>' + name + '</strong><small>' + descriptions[mode] +
      '</small></span></label>').join('') + '</div></fieldset>' +
    '<div class="setup-fields">' + select('region','Region') + select('rank','Rank') + select('window','Window') +
    '</div><button class="action" type="submit">View recommendations</button></form>';
}
const pct = value => value == null ? '—' : value.toFixed(1) + '%';
const numeric = value => value == null ? '—' : value;
const rank = (c, mode = state.mode) => (mode === 'team' ? c.teamplay_rank : c.filtered_rank) ?? c.filtered_rank ?? c.rank;
const byRank = (a,b) => rank(a) - rank(b) || a.name.localeCompare(b.name);
const difficulty = c => c.difficulty ? c.difficulty[0].toUpperCase() + c.difficulty.slice(1) + ' difficulty' : 'Difficulty unavailable';
const score = c => c.flex_clash_score == null ? '—' : Math.round(c.flex_clash_score * 100);
const isTeam = () => state.mode === 'team';
const hasSnapshot = () => state.region === 'na' && state.rank === 'diamond' && state.window === '7d';
function sample() {
  return '<section class="home-sample" aria-labelledby="sample"><div class="sample-title"><h2 id="sample">Example rankings</h2><span>Solo Queue / Top</span></div>' +
    snapshot.solo.top.slice(0,3).map(c => '<div class="sample-row"><span class="ranknum">#' + rank(c,'solo') + '</span>' +
      portrait(c,38) + '<strong>' + text(c.name) + '</strong><span><b>' + pct(c.win_rate) + '</b><small>Win rate</small></span></div>').join('') +
    '<p>NA, Diamond, last 7 days</p></section>';
}
function home() {
  const title = direction === 'a' ? 'Know who to lock in.' : 'Who should you pick?';
  return '<main class="wrap home" id="main" tabindex="-1"><div class="home-intro"><h1>' + title +
    '</h1><p>Find a strong champion for your queue and role, and see why.</p></div>' +
    setup() + (direction === 'a' ? sample() : '') + '</main>';
}
function context() {
  const region = {na:'NA',lan:'LAN',las:'LAS'}[state.region];
  return '<div class="results-context"><p aria-label="Match context">' +
    text(region || state.region) + '<span aria-hidden="true"> / </span>' + text(options.rank[state.rank] || state.rank) +
    '<span aria-hidden="true"> / </span>' + text(options.window[state.window] || state.window) +
    '</p><a class="plain" href="' + href('home') + '">Change setup' + icon('chevron') + '</a></div>';
}
function rolesBar() {
  return '<nav class="roles" aria-label="Role">' + Object.entries(roles).map(([key, label]) => '<a href="' +
    href(state.screen, {role:key === 'top' ? null : key, view:state.view === 'draft' ? 'draft' : null}) +
    '"' + (key === state.role ? ' aria-current="true"' : '') + '>' + icon(key) + label + '</a>').join('') + '</nav>';
}
function viewBar() {
  return '<nav class="view-nav" aria-label="Flex and Clash view"><a ' + (state.view === 'picks' ? 'aria-current="page" ' : '') +
    'href="' + href('team') + '">Picks</a><a ' + (state.view === 'draft' ? 'aria-current="page" ' : '') +
    'href="' + href('team', {view:'draft'}) + '">Draft <small>Bans &amp; lineup</small></a></nav>';
}
function filters() {
  return '<div class="filters">' + select('order','Sort by') + select('difficulty','Difficulty') + '</div>';
}
function sourceBuild(c) {
  return '<a class="plain" href="' + text(c.champion_url) + '">View source build' + icon('arrow') + '</a>';
}
function dataStatus() {
  return isTeam() ? '<details class="data-status"><summary>' + icon('warning') + '<span>Some pro records are incomplete</span>' +
    icon('down') + '</summary><p>Read pro pick and ban counts with that coverage in mind. Pro games through November 21.</p></details>' :
    '<p class="healthy">' + icon('check') + 'Ladder data updated November 22</p>';
}
function getPicks() {
  const pool = hasSnapshot() ? snapshot[state.mode][state.role] : [];
  const priority = pool.filter(c => isTeam() ? c.teamplay_ban_rank > 0 : c.pbi > 0)
    .sort((a,b) => isTeam() ? a.teamplay_ban_rank - b.teamplay_ban_rank : b.pbi - a.pbi || byRank(a,b));
  const eligible = pool.filter(c => state.difficulty === 'all' || state.difficulty === c.difficulty).sort(byRank);
  const top = eligible[0];
  const banRank = c => priority.indexOf(c) === -1 ? Infinity : priority.indexOf(c) + 1;
  const orderFns = {
    rank:byRank, win_rate:(a,b) => (b.win_rate ?? -1) - (a.win_rate ?? -1),
    pick_rate:(a,b) => (b.pick_rate ?? -1) - (a.pick_rate ?? -1),
    difficulty:(a,b) => (a.difficulty_order ?? 999) - (b.difficulty_order ?? 999),
    ban:(a,b) => banRank(a) - banRank(b)
  };
  return {top, picks:eligible.sort(orderFns[state.order]), bans:priority.slice(0,3), banRank};
}
function evidence(c, banRank) {
  const base = isTeam() ? [['Draft score', score(c)], ['Pro picks', numeric(c.pro_pick_count)], ['Pro bans', numeric(c.pro_ban_count)]] :
    [['Win rate', pct(c.win_rate)], ['Pick rate', pct(c.pick_rate)], ['Best win est.', pct(c.best_win_est)]];
  if (state.order === 'ban') return [base[0], ['Ban priority', Number.isFinite(banRank(c)) ? '#' + banRank(c) : '—'], base[2]];
  if (isTeam() && state.order === 'win_rate') return [base[0], ['Win rate', pct(c.win_rate)], base[2]];
  if (isTeam() && state.order === 'pick_rate') return [base[0], ['Pick rate', pct(c.pick_rate)], base[2]];
  return base;
}
function activeMetric(label) {
  return label === options.order[state.order];
}
function stats(c, banRank) {
  return '<dl class="metrics">' + evidence(c, banRank).map(([label,value]) => '<div' +
    (activeMetric(label) ? ' class="active-metric"' : '') + '><dt>' + label + '</dt><dd>' + value + '</dd></div>').join('') + '</dl>';
}
function reason(c) {
  return isTeam() ? 'Highest-ranked eligible ' + roles[state.role] + ' pick. Draft score weighs pro presence and ladder strength.' :
    'Rated ' + c.tier + ' for ' + roles[state.role] + ' in this ladder snapshot.';
}
function extraEvidence(c, banRank) {
  const pos = banRank(c);
  return '<p>' + (isTeam() ?
    'Ladder win rate ' + pct(c.win_rate) + ' / Ladder pick rate ' + pct(c.pick_rate) + ' / ' + numeric(c.pro_flex_roles) + ' pro roles' :
    'Mastery gap ' + pct(c.mastery_gap_pct) + ' / Lane delta ' + numeric(c.delta?.toFixed(1))) +
    (Number.isFinite(pos) ? ' / Ban priority #' + pos : '') + '</p><p>' +
    (isTeam() ? 'Draft score weighs pro draft evidence at 90% and ladder strength at 10%.' :
      'Best win estimate adds the source lane delta to the observed win rate.') + '</p>' + sourceBuild(c);
}
function banList(bans) {
  const order = bans.map((c,i) => '<li><span class="ban-position">' + (i+1) + '</span>' + portrait(c,34) +
    '<strong>' + text(c.name) + '</strong></li>').join('');
  return '<section class="bans" aria-labelledby="bans-title"><h2 id="bans-title" tabindex="-1">' + icon('ban') +
    (isTeam() ? 'Bans to consider' : 'Recommended bans') + '</h2><p>' +
    (isTeam() ? 'Deny these ' + roles[state.role] + ' picks if your team can’t secure them.' : 'Ban priorities for ' + roles[state.role] + ' across all difficulty levels.') +
    '</p><ol>' + order + '</ol></section>';
}
function roster() {
  const candidates = Object.keys(roles).map(key => snapshot.team[key].filter(c => c.difficulty === 'easy').sort((a,b) => a.teamplay_rank - b.teamplay_rank));
  let best = null;
  function search(chosen, total) {
    if (best && total > best.total) return;
    if (chosen.length === candidates.length) {
      if (!best || total < best.total) best = {chosen,total};
      return;
    }
    for (const next of candidates[chosen.length]) {
      if (!chosen.some(c => c.name === next.name)) search([...chosen,next],total + next.teamplay_rank);
    }
  }
  search([],0);
  return best?.chosen || [];
}
function lineup() {
  const slots = roster();
  return '<section class="lineup" id="lineup" tabindex="-1" aria-labelledby="lineup-title"><h2 id="lineup-title">' + icon('lineup') + 'Five-role lineup</h2>' +
    '<p>Five distinct Easy picks, ranked together for Flex / Clash.</p><details class="roster"><summary>' +
    '<span class="build-copy">Build lineup</span><span class="hide-copy">Hide lineup</span>' + icon('down') + '</summary>' +
    (slots.length ? '<ol>' + slots.map(c => '<li>' + portrait(c,34) + '<span><small>' + roles[c.lane] +
      '</small><strong>' + text(c.name) + '</strong></span><small class="slot-score">Draft ' + score(c) + '</small></li>').join('') + '</ol>' :
      '<p>Try another match context to fill all five roles.</p>') + '</details></section>';
}
function rankedRow(c, top, banRank) {
  const recommended = c === top;
  return '<li class="ranked-row' + (recommended ? ' canonical' : '') + '" id="pick-' + rank(c) + '">' +
    '<div class="ranked-grid"><span class="ranknum" aria-label="Recommendation rank ' + rank(c) + '">#' + rank(c) + '</span>' +
    portrait(c,46) + '<div class="champion"><h3>' + text(c.name) + '</h3><p>' + difficulty(c) + '</p></div>' +
    (recommended ? '<span class="pick-label">' + icon('check') + 'Top recommendation</span>' : '') + stats(c,banRank) + '</div>' +
    (recommended ? '<p class="row-reason">' + reason(c) + '</p>' : '') +
    '<details class="rank-details"><summary aria-label="Evidence for ' + text(c.name) + '">' +
    icon('down') + '</summary>' +
    '<div class="row-extra">' + extraEvidence(c,banRank) + '</div></details></li>';
}
function empty() {
  return '<section class="empty"><h2>' + (hasSnapshot() ? 'No picks at this difficulty' : 'This context has no prototype snapshot') +
    '</h2><p>' + (hasSnapshot() ? 'Try all difficulty levels for this role.' : 'This demo uses North America, Diamond, last 7 days.') +
    '</p>' + (hasSnapshot() ? '<button class="secondary" data-clear>Clear difficulty</button>' :
    '<a class="plain" href="?direction=' + direction + '&screen=' + state.screen + '">Open the reference results' + icon('arrow') + '</a>') + '</section>';
}
function ranking({top,picks,bans,banRank}) {
  const first = picks[0];
  return '<div class="a-results"><section class="rankings" id="ranked-picks" tabindex="-1" aria-labelledby="ranking-title"><div class="list-heading">' +
    '<div><h2 id="ranking-title">Ranked picks</h2><p>' + picks.length + (picks.length === 1 ? ' eligible pick' : ' eligible picks') + '</p></div>' +
    filters() + '</div>' + (isTeam() ? dataStatus() : '') + (top && top !== first ? '<p class="alternate-order">Top recommendation <a href="#pick-' + rank(top) + '">' +
    text(top.name) + ' (#' + rank(top) + ')</a></p>' : '') +
    (picks.length ? '<ol class="rank-list" aria-label="Champions in selected sort order">' + picks.map(c => rankedRow(c,top,banRank)).join('') + '</ol>' : empty()) +
    '</section><aside class="draft-rail" id="draft-tools" tabindex="-1" aria-label="' + (isTeam() ? 'Draft tools' : 'Ban priorities') + '">' +
    (isTeam() ? '<h2 class="draft-title">Draft</h2>' : '') + banList(bans) + (isTeam() ? lineup() : '') +
    (isTeam() ? '<a class="plain return-to-picks" href="#ranked-picks">Back to picks</a>' : dataStatus()) + '</aside></div>';
}
function pickBrief(c, top, banRank) {
  const recommended = c === top;
  return '<section class="pick-brief" aria-labelledby="brief-title"><div class="brief-lead">' + portrait(c,84) +
    '<div><p class="brief-kicker">' + (recommended ? icon('check') + 'Top recommendation' : 'Alternative / Rank #' + rank(c)) +
    '</p><h2 id="brief-title">' + text(c.name) + '</h2><p>' + difficulty(c) + '</p></div></div>' +
    '<p class="brief-reason">' + (recommended ? reason(c) : 'Compare this pick’s evidence with the top recommendation.') + '</p>' +
    stats(c,banRank) + '<div class="brief-actions"><details><summary>More evidence ' + icon('down') + '</summary><div class="brief-extra">' +
    extraEvidence(c,banRank) + '</div></details>' + (recommended ? '' : '<button class="plain" data-inspect="">Back to ' + text(top.name) + '</button>') +
    '</div></section>';
}
function shortlist({top,picks,bans,banRank}) {
  const inspected = picks.find(c => c.name === state.inspected) || top;
  const alternatives = picks.filter(c => c !== top);
  const sortIndex = ['pick_rate','win_rate','ban'].includes(state.order)
    ? (isTeam() || state.order === 'ban' ? 1 : state.order === 'pick_rate' ? 1 : 0) : 0;
  const sortStats = c => evidence(c,banRank)[sortIndex];
  return '<div class="b-picks">' +
    (isTeam() || !hasSnapshot() ? '' : '<a class="ban-jump plain" href="#bans-title">See recommended bans' + icon('down') + '</a>') +
    (top ? pickBrief(inspected,top,banRank) : '') + (isTeam() ? dataStatus() : '') +
    '<section class="shortlist" aria-labelledby="shortlist-title"><div class="list-heading"><div><h2 id="shortlist-title">Compare alternatives</h2>' +
    '<p>' + alternatives.length + (alternatives.length === 1 ? ' alternative' : ' alternatives') + '</p></div>' + filters() + '</div>' +
    (top ? '<ol>' + alternatives.map(c => '<li><button data-inspect="' + text(c.name) + '" class="choice-row"' +
      (c === inspected ? ' aria-pressed="true"' : ' aria-pressed="false"') + '>' + portrait(c,38) +
      '<span class="choice-name"><strong>' + text(c.name) + '</strong><small>' + difficulty(c) + '</small></span>' +
      '<span class="choice-stat"><b>' + sortStats(c)[1] + '</b><small>' + sortStats(c)[0] + '</small></span>' + icon('chevron') + '</button></li>').join('') +
      '</ol>' : empty()) + '</section>' +
    (isTeam() ? '' : '<aside class="b-bans">' + banList(bans) + dataStatus() + '</aside>') + '</div>';
}
function results() {
  const data = getPicks();
  return '<main class="wrap results" id="main" tabindex="-1"><div class="results-heading"><div><h1>' +
    (isTeam() ? 'Flex / Clash' : 'Solo picks') + '</h1>' + context() + '</div>' +
    (direction === 'b' && isTeam() ? viewBar() : '') + '</div>' + rolesBar() +
    (isTeam() && direction === 'b' && state.view === 'draft' && hasSnapshot() ?
      '<div class="draft-page"><div><h2>Draft priorities</h2><p>Ban by role, or build a lineup for all five roles.</p></div>' +
      '<div class="draft-workspace">' + banList(data.bans) + lineup() + '</div>' + dataStatus() + '</div>' :
      !hasSnapshot() ? empty() :
      direction === 'a' ? '<div class="quick-jumps"><a class="plain" href="#draft-tools">' +
        (isTeam() ? 'Draft tools (bans &amp; lineup)' : 'Recommended bans') + icon('down') + '</a></div>' + ranking(data) : shortlist(data)) + '</main>';
}
function update({focus, scroll = scrollY} = {}) {
  app.innerHTML = headingControls() + (state.screen === 'home' ? home() : results());
  const target = focus && document.querySelector(focus);
  target?.focus({preventScroll:true});
  scrollTo(0,scroll);
}
app.addEventListener('submit', event => {
  event.preventDefault();
  const setup = new FormData(event.target);
  for (const key of ['region','rank','window']) state[key] = setup.get(key);
  location.href = href(setup.get('queue'),{role:null, order:null, difficulty:null});
});
app.addEventListener('change', event => {
  const control = event.target;
  if (state.screen === 'home') {
    if (control.matches('select')) control.parentElement.querySelector('.field-value span').textContent = control.selectedOptions[0].textContent;
    return;
  }
  state[control.name] = control.value;
  state.inspected = null;
  history.replaceState(null,'',href(state.screen));
  update({focus:'select[name="' + control.name + '"]'});
});
app.addEventListener('click', event => {
  const inspect = event.target.closest('[data-inspect]');
  if (inspect) {
    state.inspected = inspect.dataset.inspect;
    update({scroll:0});
    const heading = document.querySelector('#brief-title');
    heading.tabIndex = -1;
    heading.focus({preventScroll:true});
    heading.scrollIntoView({block:'nearest'});
  }
  if (event.target.closest('[data-clear]')) {
    state.difficulty = 'all';
    history.replaceState(null,'',href(state.screen));
    update({focus:'select[name="difficulty"]'});
  }
});
if (state.screen === 'team' || state.screen === 'solo') state.mode = state.screen;
update({scroll:0});

if (location.hash) requestAnimationFrame(() => document.getElementById(location.hash.slice(1))?.scrollIntoView());
