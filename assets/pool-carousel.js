function poolNames(pool) {
  const value = pool.five_star || pool.characters || '';
  return (Array.isArray(value) ? value : value.split('、')).map(name => name.trim()).filter(Boolean);
}

function poolIsRerun(pool, name) {
  return (pool.rerun_characters || []).includes(name) ||
    (pool.is_rerun_banner === true && !pool.new_characters?.includes(name));
}

function poolBadgeClass(label) {
  return 'rerun-tag pool-badge-' + ({ NEW: 'new', 當期PU: 'pickup', 復刻: 'rerun' }[label]);
}

function artForName(entries, gameId, name) {
  if (entries?.[name] || gameId !== 'starrail') return entries?.[name];
  const normalize = value => value.replace(/[\s·・•･‧]/g, '');
  const key = Object.keys(entries || {}).find(candidate => normalize(candidate) === normalize(name));
  return entries?.[key];
}

function poolDuration(rerun) {
  return rerun ? 3500 : 10000;
}

function estimatedUpdate(game, today) {
  if (/^\d{4}-\d{2}-\d{2}$/.test(game.date || '')) return null;
  const gap = { genshin: 1, starrail: 1, zzz: 1, wuwa: 1, nte: 0, endfield: 0 }[game.id];
  if (gap === undefined) return null;
  const pools = [...(game.phases || []), ...(game.special_banners || [])];
  const dates = pools.filter(pool => !pool.time_unverified &&
    (game.id === 'endfield'
      ? /版本維護開始/.test(pool.end || '')
      : /下半|招募二|特殊跨期招募/.test(pool.label || '')) &&
    !/自選|免費|贈送|獨立|集錄/.test(pool.label || ''))
    .map(pool => String(displayTime(pool.end) || '').match(/^\d{4}-\d{2}-\d{2}/)?.[0])
    .filter(Boolean).sort();
  const end = dates.at(-1);
  if (!end) return null;
  const epoch = Date.parse(end + 'T00:00:00Z');
  if (!Number.isFinite(epoch) || new Date(epoch).toISOString().slice(0, 10) !== end) return null;
  const estimate = new Date(epoch + gap * 86400000).toISOString().slice(0, 10);
  return estimate >= today ? estimate : null;
}

(function poolCarousel() {
  const badgeStyles = document.createElement('style');
  badgeStyles.textContent = `
    .pool-slide > .rerun-tag {
      align-self: flex-start;
      width: max-content;
      max-width: 100%;
      font-size: clamp(1rem, 1.7vw, 1.22rem);
      line-height: 1.15;
      padding: 3px 8px;
    }
    .history-character-backdrop img.history-banner-art { object-position: var(--character-focus, center 42%); }
    .history-character-backdrop img.history-nikke-art { object-position: var(--character-focus, right 36%); }
    .history-costume-phase.phasebox { min-height: 0; }
    .history-costume-phase.phasebox:has(img) {
      min-height: clamp(240px, 26vw, 320px) !important;
      display: flex !important;
      align-items: end;
    }
    .history-costume-phase .phase-copy { max-width: 56%; }
    .history-costume-phase .phase-backdrop img { width: 55%; object-fit: scale-down; object-position: center; mask-image: none; }
    .history-costume-phase .phase-backdrop:has(img)::after {
      background: linear-gradient(90deg, #17263e 20%, #17263ec9 40%, transparent 71%);
    }
    @media (max-width: 600px) {
      .history-costume-phase.phasebox:has(img) { min-height: 0 !important; padding-top: 248px !important; }
      .history-costume-phase .phase-copy { max-width: none; }
      .history-costume-phase .phase-backdrop img { width: 100%; height: 240px; object-position: center; mask-image: none; }
      .history-costume-phase .phase-backdrop:has(img)::after {
        background: linear-gradient(180deg, transparent 160px, #17263e 263px);
      }
      .pool-slide img.pool-narrow-art { object-fit: contain; object-position: right center; }
      .history-character-backdrop img.history-banner-art { object-position: var(--character-mobile-focus, var(--character-focus, center 42%)); }
      .history-character-backdrop img.history-nikke-art { object-position: var(--character-mobile-focus, var(--character-focus, right 36%)); }
      .history-character-backdrop img.history-narrow-art { object-fit: contain; object-position: right center; }
    }
    .cards > .card > .overview-heading { display: grid; gap: 9px; }
    .overview-heading > .row { min-width: 0; }
    .overview-heading .logo { flex: 0 0 auto; }
    .overview-heading .name { overflow-wrap: normal; word-break: normal; }
    .overview-heading .countdown-head { justify-content: flex-start; }
    .overview-heading .countdown-head .pill { white-space: normal; max-width: 100%; }
    .overview-estimated-date { margin-top: 5px; color: #b9cff0; font-size: .87rem; }
    .rerun-tag.pool-badge-new { color: #b6ffca; background: #123d2e; border-color: #67d697; }
    .rerun-tag.pool-badge-pickup { color: #bcecff; background: #12374e; border-color: #70c9f0; }
    .rerun-tag.pool-badge-rerun { color: #ffe0a6; background: #4a321c; border-color: #d49a57; }
  `;
  document.head.append(badgeStyles);
  const hero = document.querySelector('.pool-hero');
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const catalogs = [{}, {}];
  let currentKey;
  let currentSlide = hero.firstElementChild;
  let preloaded;
  let heroUntil = 0;
  let historyArt = {};
 function instant(value,isStart){
  const str=String(value||'');
  if(/^\d{4}-\d\d-\d\dT.*(?:Z|[+-]\d\d:\d\d)$/.test(str))return Date.parse(str);
  const m=str.match(/^(\d{4}-\d\d-\d\d)(?:\s+(\d\d:\d\d))?(?:[（(].*[）)])?$/);
  if(!m||(!m[2]&&!isStart))return NaN;
  // Date-only starts are safely in the past after their local calendar day.
  return Date.parse(m[1]+'T'+(m[2]||'00:00')+':00+08:00')+(m[2]?0:86400000);
 }

  function activeCharacters(now) {
    const items = new Map();
    for (const game of seed) {
      const phases = [...(game.phases || []), ...(game.special_banners || []), ...(game.next_phases || [])];
      for (const phase of phases) {
        const end = instant(phase.end, false);
        if (phase.time_unverified || !(instant(phase.start, true) <= now && now < end)) continue;
        for (const name of poolNames(phase)) {
          if (poolIsRerun(phase, name)) continue;
          const key = [game.id, name, end].join('|');
          if (!items.has(key)) items.set(key, { key, name, game, phase, end });
        }
      }
    }
    return [...items.values()];
  }

  function sources({ game, name, phase }) {
    return [...new Set([['starrail', 'nikke'].includes(game.id) ? artForName(historyArt[game.id], game.id, name)?.background : null,
      artForName(catalogs[0][game.id], game.id, name), artForName(catalogs[1][game.id], game.id, name),
      artForName(game.character_art, game.id, name), phase.banner_image].filter(Boolean))];
  }

  function remaining(end, now) {
    const minutes = Math.ceil((end - now) / 60000);
    if (minutes < 60) return '剩餘 ' + minutes + ' 分鐘';
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return '剩餘 ' + hours + ' 小時';
    return '剩餘 ' + Math.floor(hours / 24) + ' 天 ' + hours % 24 + ' 小時';
  }

  function addText(parent, tag, className, value) {
    const el = document.createElement(tag);
    el.className = className;
    el.textContent = value;
    parent.append(el);
  }

  function render(advance = false) {
    const now = Date.now();
    const items = activeCharacters(now);
    const previous = items.findIndex(item => item.key === currentKey);
    const index = previous < 0 ? 0 : (previous + Number(advance)) % items.length;
    const item = items[index];
    const urls = item ? sources(item) : [];
    const key = item?.key || '';
    if (currentKey === key && currentSlide.dataset.src === urls.join('|')) {
      if (item) currentSlide.querySelector('.pool-time').textContent = remaining(item.end, now);
      return;
    }

    const slide = document.createElement('div');
    slide.className = 'pool-slide';
    slide.dataset.src = urls.join('|');
    if (item) {
      slide.style.setProperty('--pool-color', item.game.color);
      if (urls.length) {
        const image = document.createElement('img');
        image.alt = '';
        let urlIndex = 0;
        image.onerror = () => {
          if (++urlIndex < urls.length) image.src = urls[urlIndex];
          else image.remove();
        };
        image.onload = () => {
          image.classList.toggle('pool-narrow-art', image.naturalWidth < image.naturalHeight);
          const art = artForName(historyArt[item.game.id], item.game.id, item.name);
          if (art?.focus && art.background === urls[urlIndex]) image.style.setProperty('--character-focus', art.focus);
        };
        image.src = urls[0];
        slide.append(image);
      }
      addText(slide, 'span', 'pool-game', item.game.name);
      addText(slide, 'span', 'pool-label', item.phase.label || '當期角色卡池');
      addText(slide, 'h1', '', item.name);
      addText(slide, 'span', poolBadgeClass('當期PU'), '當期PU');
      addText(slide, 'strong', 'pool-time', remaining(item.end, now));
    } else {
      addText(slide, 'h1', '', '目前沒有可倒數的卡池');
      addText(slide, 'span', 'pool-label', '等待卡池時間確認');
    }

    const outgoing = currentSlide;
    if (advance && previous >= 0 && item && key !== currentKey && !reducedMotion.matches) {
      outgoing.setAttribute('aria-hidden', 'true');
      outgoing.classList.remove('pool-enter');
      outgoing.classList.add('pool-exit');
      slide.classList.add('pool-enter');
      setTimeout(() => outgoing.remove(), 560);
    } else outgoing.remove();
    hero.append(slide);
    currentKey = key;
    heroUntil = now + poolDuration(item && poolIsRerun(item.phase, item.name));
    currentSlide = slide;
    const next = items.length > 1 && sources(items[(index + 1) % items.length])[0];
    if (next) {
      preloaded = new Image();
      preloaded.src = next;
    }
  }

  const phaseStates = new WeakMap();
  const failedUrls = new Set();

  function paintPhase(layer, advance) {
    let state = phaseStates.get(layer);
    if (!state) {
      state = { names: JSON.parse(layer.dataset.names), current: '', pending: '', until: 0 };
      phaseStates.set(layer, state);
    }
    const game = seed.find(game => game.id === layer.dataset.game);
    const bounds = layer.getBoundingClientRect();
    if (bounds.bottom < -200 || bounds.top > window.innerHeight + 200) return;
    if (!game || state.pending || (state.current && (!advance || Date.now() < state.until))) return;
    const poster = layer.dataset.poster;
    const perName = JSON.parse(layer.dataset.art || '{}');
    const reruns = JSON.parse(layer.dataset.reruns || '[]');
    const entries = state.names.map((name, index) => {
      const art = perName[name];
      const matching = sources({ game, name, phase: {} });
      const candidates = [
        art?.background, ...(game.id === 'starrail' ? matching : []),
        index === 0 ? poster : null, ...matching, art?.portrait
      ];
      const url = candidates.find(value => value && !failedUrls.has(value));
      return { name, url, portrait: url === art?.portrait ||
        (url === poster && layer.classList.contains('history-portrait-backdrop')) };
    }).filter(item => item.url);
    if (!entries.length && poster && !failedUrls.has(poster)) entries.push({ name: '', url: poster });
    if (!entries.length) return;
    const index = entries.findIndex(item => item.name === state.current);
    const item = entries[index < 0 ? 0 : (index + 1) % entries.length];
    if (item.name === state.current && layer.firstElementChild) return;
    state.pending = item.url;
    const img = new Image();
    img.alt = '';
    const namedArt = artForName(historyArt[game.id], game.id, item.name);
    if (namedArt?.focus && namedArt.background === item.url) {
      img.style.setProperty('--character-focus', namedArt.focus);
    }
    if (layer.classList.contains('history-character-backdrop') && game.id !== 'bd2') {
      img.classList.add('history-banner-art');
    }
    if (layer.classList.contains('history-character-backdrop') && !item.portrait) {
      if (item.url.includes('/image/character_portrait/')) {
        const focus = node => ({
          '1213': '56% 50%', '1507': '55% 48%', '1415': '52% 59%', '1401': '54% 49%', '1225': '42% 49%', '1317': '62% 49%'
        })[node] || 'center 53%';
        img.style.width = 'min(60%, 310px)';
        img.style.objectPosition = focus(item.url.split('/').at(-1).split('.')[0]);
        img.style.maskImage = 'linear-gradient(90deg, transparent, black 18%)';
      } else if (game.id === 'nikke') {
        img.classList.add('history-nikke-art');
      }
    }
    if (item.portrait && game.id === 'bd2') {
      img.style.objectFit = 'scale-down';
    } else if (item.portrait) {
      img.style.width = 'min(32%, 135px)';
      img.style.objectFit = 'contain';
      img.style.objectPosition = 'center';
    }
    img.onload = () => {
      state.pending = '';
      if (!layer.isConnected) return;
      if (!item.portrait && img.naturalWidth < img.naturalHeight && game.id !== 'bd2') {
        img.classList.add('history-narrow-art');
      }
      const old = layer.lastElementChild;
      if (old && advance && !reducedMotion.matches) {
        old.classList.remove('pool-enter');
        old.classList.add('pool-exit');
        img.classList.add('pool-enter');
        setTimeout(() => old.remove(), 560);
      } else layer.replaceChildren();
      layer.append(img);
      state.current = item.name;
      state.until = Date.now() + poolDuration(reruns.includes(item.name));
    };
    img.onerror = () => {
      failedUrls.add(item.url);
      state.pending = '';
      if (layer.isConnected) paintPhase(layer, true);
    };
    img.src = item.url;
  }

  function paintPhases(advance = false) {
    document.querySelectorAll('.phase-backdrop').forEach(layer => paintPhase(layer, advance));
  }

  const originalHistoryRelease = isHistoryReleased;
  isHistoryReleased = function (entry) {
    if (!originalHistoryRelease(entry) || entry.mergedIntoVersion) return false;
    const now = Date.now();
    const game = seed.find(item => item.id === entry.game);
    const scheduled = [...(game?.phases || []), ...(game?.special_banners || []), ...(game?.next_phases || [])];
    return (entry.phases || []).every(phase => {
      const end = instant(phase.end || phase.end_date, true);
      if (Number.isFinite(end) && now < end) return false;
      const matching = scheduled.find(item => historyPhaseKey(item) === historyPhaseKey(phase));
      if (!matching) return true;
      const scheduledEnd = instant(matching.end, true);
      return Number.isFinite(scheduledEnd) && scheduledEnd <= now;
    });
  };

  function historyPhaseKey(phase) {
    const start = displayTime(phase.start || phase.start_date);
    const names = String(phase.characters || phase.five_star || '').split('、').map(name => name.trim()).sort();
    return [String(start || '').slice(0, 10), names.join('、')].join('|');
  }

  function mergeHistoricalBannerDetails() {
    const versions = new Map();
    for (const entry of verifiedHistory) {
      if (entry.game === 'endfield' || !/^\d+\.\d+(?:\.\d+)?$/.test(entry.version)) continue;
      for (const phase of entry.phases || []) {
        versions.set(entry.game + '|' + historyPhaseKey(phase), phase);
      }
    }
    for (const entry of verifiedHistory) {
      if (/^\d+\.\d+(?:\.\d+)?$/.test(entry.version) || !entry.phases?.length) continue;
      const pairs = entry.phases.map(phase => [phase, versions.get(entry.game + '|' + historyPhaseKey(phase))]);
      if (pairs.some(([, canonical]) => !canonical)) continue;
      for (const [earlier, canonical] of pairs) {
        for (const [key, value] of Object.entries(earlier)) {
          if (value != null && (canonical[key] == null || canonical[key] === '')) canonical[key] = value;
        }
        if (earlier.banner_image) canonical.banner_image = earlier.banner_image;
      }
      entry.mergedIntoVersion = true;
    }
  }

  function restoreHistoryPosters() {
    let changed = false;
    for (const entry of verifiedHistory) {
      for (const phase of entry.phases || []) {
        if (phase.banner_image || phase.portrait_image) continue;
        const names = String(phase.five_star || phase.characters || '').split('、');
        const game = seed.find(game => game.id === entry.game);
        const startDay = displayTime(phase.start || phase.start_date)?.slice(0, 10);
        const matchingBanner = startDay && [
          ...(game?.phases || []), ...(game?.special_banners || []), ...(game?.next_phases || [])
        ].find(banner => banner.banner_image && banner.characters === names.join('、') &&
          displayTime(banner.start)?.slice(0, 10) === startDay);
        const sources = names.map(name => name.trim()).flatMap(name => [
          catalogs[0][entry.game]?.[name], catalogs[1][entry.game]?.[name],
          game?.character_art?.[name]
        ]);
        const poster = matchingBanner?.banner_image || sources.find(Boolean);
        if (poster) {
          phase.banner_image = poster;
          changed = true;
        }
      }
    }
    return changed;
  }

  let reviewedHistory = {};
  fetch('./data/history-reviewed.json', { cache: 'no-cache' }).then(async response => {
    if (!response.ok) return;
    const data = await response.json();
    if (data.schema !== 1) return;
    reviewedHistory = data.games;
    if (tab === 'history') window.render();
  }).catch(error => console.warn('Historical banner artwork:', error.message));

  function applyReviewedHistory() {
    for (const entry of verifiedHistory) {
      const fixes = reviewedHistory[entry.game];
      if (!fixes) continue;
      for (const pool of entry.phases || []) {
        const key = [entry.version, String(pool.start_date || pool.start || '').slice(0, 10),
          pool.five_star || pool.characters || ''].join('|');
        if (fixes[key]) Object.assign(pool, fixes[key]);
      }
    }
  }

  const historyLabels = {
    genshin: ['五星角色', '五星武器'],
    starrail: ['五星角色', '五星光錐'],
    zzz: ['S級代理人', 'S級音擎'],
    wuwa: ['五星共鳴者', '五星武器'],
    endfield: ['六星幹員', '六星武器'],
    nte: ['S級角色', 'S級弧盤'], bd2: ['服裝'], gfl2: ['精英人形'], nikke: ['SSR 角色']
  };

  const endfieldArmory = {
    ...Object.fromEntries([
      ['萊萬汀','2026-01-22','熔火灼痕','熔鑄申領','熔鑄火焰','https://endfield.hypergryph.com/news/9352'],
      ['潔爾佩塔','2026-02-07','輕飄飄的信使','迅行申領','使命必達','https://www.animattoys.com/detail/6Yp9Vdj3/%E6%98%8E%E6%97%A5%E6%96%B9%E8%88%9F%E7%B5%82%E6%9C%AB%E5%9C%B010%E7%89%88%E6%9C%AC%E6%9C%80%E6%96%B0%E6%B6%88%E6%81%AF'],
      ['伊馮','2026-02-24','熱烈色彩','繪塗申領','藝術暴君','https://endfield.hypergryph.com/news/3811'],
      ['湯湯','2026-03-12','河流的女兒','新芽申領','落草','8907'],
      ['洛西','2026-03-29','狼珀','緋珀申領','狼之緋','8907'],
      ['莊方宜','2026-04-17','春雷動，萬物生','行舟申領','孤舟','0751'],
      ['弭弗','2026-06-05','拳出無悔','絳結申領','赤纓','0758'],
      ['卡繆','2026-06-26','逐罪者','染赤申領','鍍紅祝福','0758'],
      ['訣','2026-07-16','臨淵望北','軍列申領','四二式·肅陣','5200'],
      ['小刻','2026-11-25','鍛砧、行囊與蜜糖','恣遊申領','甜美交易','0740']
    ].map(([operator, start, origin, pool, name, source]) => [
      operator + '|' + start, { origin, pool, name, start,
        end: '自「' + origin + '」起，第 3 次特許尋訪結束後',
        source: source.startsWith('https://') ? source : 'https://endfield.gryphline.com/zh-tw/news/' + source }
    ])),
    '伊馮|2026-09-24': {
      origin: '絢麗異彩', pool: '點繪申領（重構）', name: '藝術暴君',
      start: '2026-09-24 12:00', end: '版本更新維護前',
      source: 'https://endfield.gryphline.com/zh-tw/news/5208'
    },
    '梨諾|2026-08-09': {
      origin: '晨星於此閃耀', pool: '明曜申領', name: '曜夜的首演',
      start: '2026-08-09 12:00', end: '自「晨星於此閃耀」起，第 3 次特許尋訪結束後',
      source: 'https://endfield.gryphline.com/zh-tw/news/5200'
    },
    '提弗洛斯|2026-09-02': {
      origin: '冬獵', pool: '幽寒申領', name: '寒夜幽影',
      start: '2026-09-02（版本更新後）', end: '自「冬獵」起，第 3 次特許尋訪結束後',
      source: 'https://endfield.gryphline.com/zh-tw/news/5208'
    },
    '湯湯|2026-10-29': {
      origin: '祖泉的新流', pool: '細枝申領（重構）', name: '落草',
      start: '2026-10-29 12:00', end: '2026-11-19 11:59',
      source: 'https://endfield.gryphline.com/zh-tw/news/6179'
    },
    '祀|2026-10-15': {
      origin: '萬物更新', pool: '篆玉申領', name: '玉中身', start: '2026-10-15 12:00',
      end: '自「萬物更新」起，第 3 次特許尋訪結束後',
      source: 'https://endfield.gryphline.com/zh-tw/news/2652'
    },
    '明河|2026-11-05': {
      origin: '煙火邀星河', pool: '月映申領', name: '喚月', start: '2026-11-05 12:00',
      end: '自「煙火邀星河」起，第 3 次特許尋訪結束後',
      source: 'https://endfield.gryphline.com/zh-tw/news/6178'
    }
  };

  function historicalArmory(pool) {
    const key = [pool.five_star || pool.characters, String(displayTime(pool.start || pool.start_date) || '').slice(0, 10)].join('|');
    const correction = endfieldArmory[key];
    const records = (pool.weapon_pools || []).map(item => {
      const verified = Object.values(endfieldArmory).find(value =>
        value.pool === item.pool || value.origin === item.origin);
      return verified ? { ...item, ...verified } : item;
    });
    if (correction && !records.some(item => item.pool === correction.pool)) records.push(correction);
    if (key === '萊萬汀、潔爾佩塔|2026-05-14') {
      records.push(...[['熔灼申領','熔鑄火焰'], ['疾行申領','使命必達']].map(([pool, name]) => ({
        pool, name, start: '2026-05-14 12:00', end: '「輝光慶典」特殊尋訪結束後',
        source: 'https://endfield.gryphline.com/zh-tw/news/0751'
      })));
    }
    return [...new Map(records.map(item => [[item.pool, item.name, item.start].join('|'), item])).values()];
  }

  const endfieldVersions = [
    ['2026-11-25', '1.7'], ['2026-10-15', '1.6'], ['2026-09-02', '1.5'],
    ['2026-07-16', '1.4'], ['2026-06-05', '1.3'], ['2026-04-17', '1.2'],
    ['2026-03-12', '1.1'], ['2026-01-22', '1.0']
  ];

  function prepareEndfieldHistory() {
    const entries = verifiedHistory.filter(entry => entry.game === 'endfield');
    const named = new Map(entries.filter(entry => !/^\d+\.\d+$/.test(entry.version))
      .flatMap(entry => (entry.phases || []).map(pool => [historyPhaseKey(pool), pool])));
    for (const entry of entries) {
      if (!/^\d+\.\d+$/.test(entry.version)) {
        entry.version_number = endfieldVersions.find(([start]) => entry.date >= start)?.[1];
        continue;
      }
      // Archive feed and named historical records can contain the same pools.
      const matches = (entry.phases || []).map(pool => [pool, named.get(historyPhaseKey(pool))]);
      if (!matches.length || matches.some(([, target]) => !target)) continue;
      entry.mergedIntoVersion = true;
      for (const [source, target] of matches) {
        if (source.start) target.start = source.start;
        if (source.end) target.end = source.end;
        if (!target.banner_image && source.banner_image) target.banner_image = source.banner_image;
        if (!target.source && source.source) target.source = source.source;
      }
    }
  }

  function archivedPools(entry) {
    const groups = new Map();
    for (const pool of entry.phases || []) {
      const start = String(displayTime(pool.start || pool.start_date) || '');
      const end = String(displayTime(pool.end || pool.end_date) || '');
      const label = String(pool.phase || pool.label || '');
      const exceptional = entry.game === 'endfield' || pool.pool_type || /自選|集錄|獨立|贈送|特殊/.test(label);
      const key = start && end && !exceptional ? [start, end].join('|') : pool;
      const previous = groups.get(key);
      const names = poolNames(pool);
      const portraitList = pool.portraits || [];
      const image = {};
      names.forEach((name, index) => {
        const art = artForName(historyArt[entry.game], entry.game, name);
        const portrait = portraitList.length === names.length ? portraitList[index] : null;
        image[name] = {
          background: art?.byVersion?.[entry.version] || art?.background || (entry.game !== 'starrail' && entry.game !== 'wuwa' && names.length === 1 ? pool.banner_image : null),
          portrait: art?.portrait || portrait || (names.length === 1 ? pool.portrait_image : null)
        };
      });
      const reruns = names.filter(name => poolIsRerun(pool, name));
      if (previous) {
        const merged = [...new Set([...poolNames(previous), ...names])];
        previous.five_star = merged.join('、');
        previous.rerun_characters = [...new Set([...previous.rerun_characters, ...reruns])];
        previous.character_art = { ...previous.character_art, ...image };
        previous.weapons = [...new Set([previous.weapons, pool.weapons].filter(Boolean))].join('、');
      } else {
        groups.set(key, { ...pool, five_star: names.join('、'), rerun_characters: reruns, character_art: image });
      }
    }
    return [...groups.values()];
  }

  function renderHistoryDetails() {
    const labels = historyLabels[gameFilter];
    if (!labels) return;
    const records = verifiedHistory.filter(entry =>
      entry.game === gameFilter && isHistoryReleased(entry) &&
      JSON.stringify(entry).toLowerCase().includes(q.toLowerCase())
    ).sort((a, b) => (b.date || '').localeCompare(a.date || ''));
    const cards = app.querySelectorAll('article[data-history-game]');
    if (cards.length !== records.length) return;

    cards.forEach((card, index) => {
      const entry = records[index];
      if (entry.game === 'endfield' && entry.version_number) {
        const heading = card.querySelector(':scope > .row strong');
        if (heading) heading.textContent += '（' + entry.version_number + '）';
      }
      const boxes = card.querySelector('.phasehistory');
      if (!boxes) return;
      boxes.replaceChildren();
      for (const pool of archivedPools(entry)) {
        const box = document.createElement('div');
        box.className = 'phasebox history-phase illustrated-phase';
        const names = poolNames(pool);
        if (entry.game === 'bd2') box.classList.add('history-costume-phase');
        if (names.length || pool.banner_image) {
          const layer = document.createElement('div');
          layer.className = 'phase-backdrop history-character-backdrop';
          layer.dataset.game = entry.game;
          layer.dataset.names = JSON.stringify(names);
          layer.dataset.art = JSON.stringify(pool.character_art || {});
          layer.dataset.reruns = JSON.stringify(names.filter(name => poolIsRerun(pool, name)));
          // Wuthering Waves multi-character pool art must come from the named
          // resonator's announcement, never a shared phase image.
          layer.dataset.poster = entry.game === 'wuwa' ? '' : pool.banner_image || pool.portrait_image || '';
          if (!pool.banner_image && pool.portrait_image) layer.classList.add('history-portrait-backdrop');
          layer.setAttribute('aria-hidden', 'true');
          if (entry.game !== 'bd2') box.style.minHeight = entry.game === 'starrail' ? '160px' : '128px';
          box.append(layer);
        }
        const copy = document.createElement('div');
        copy.className = 'history-phase-copy phase-copy';
        addText(copy, 'b', '', pool.banner_name || pool.phase || pool.label || '限定卡池');
        const start = displayTime(pool.start || pool.start_date) || '待核對';
        const end = displayTime(pool.end || pool.end_date) || '待核對';
        addText(copy, 'div', 'small', start + ' ～ ' + end);
        const characters = document.createElement('div');
        characters.append(labels[0] + '：');
        names.forEach((value, i) => {
          if (i) characters.append('、');
          characters.append(value);
          const label = poolIsRerun(pool, value) ? '復刻' : '當期PU';
          addText(characters, 'span', poolBadgeClass(label), label);
        });
        if (!names.length) characters.append('待核對');
        copy.append(characters);
        if (entry.game === 'endfield') {
          const armory = historicalArmory(pool);
          if (!armory.length) addText(copy, 'div', '', labels[1] + '：' + (pool.weapons || '申領資料待核對'));
          for (const weapon of armory) {
            const line = document.createElement('div');
            line.className = 'weapon-line';
            const text = document.createElement('strong');
            text.append((weapon.pool || '武器申領') + '：' + (weapon.name || '待核對'));
            const date = String(start).slice(0, 10);
            const own = endfieldArmory[names.join('、') + '|' + date];
            if ((own && weapon.pool === own.pool && weapon.name === own.name) ||
                (entry.version === '輝光慶典' && ['熔灼申領','疾行申領'].includes(weapon.pool))) {
              addText(text, 'span', poolBadgeClass('當期PU'), '當期PU');
            }
            line.append(text);
            addText(line, 'div', 'small', (weapon.start || '開始待核對') + ' ～ ' + (weapon.end || '結束待核對'));
            if (officialURL(weapon.source)) {
              const link = document.createElement('a');
              link.href = weapon.source;
              link.target = '_blank';
              link.rel = 'noopener noreferrer';
              link.textContent = '武器申領公告';
              line.append(link);
            }
            copy.append(line);
          }
        } else {
          if (labels[1]) addText(copy, 'div', '', labels[1] + '：' + (pool.weapons || '待核對'));
          if (pool.weapon_banner_name) addText(copy, 'div', 'small', pool.weapon_banner_name);
          if (entry.game === 'zzz' && officialURL(pool.weapon_source)) {
            const link = document.createElement('a');
            link.href = pool.weapon_source;
            link.target = '_blank';
            link.rel = 'noopener noreferrer';
            link.textContent = '音擎資料來源';
            copy.append(link);
          }
        }
        box.append(copy);
        boxes.append(box);
      }
      const slug = { starrail: 'hsr', gfl2: 'gf2' }[entry.game] || entry.game;
      const reference = document.createElement('a');
      reference.href = 'https://bannerhistory.app/tw/' + slug + '-pickup-history';
      reference.target = '_blank';
      reference.rel = 'noopener noreferrer';
      reference.textContent = '繁中卡池比對';
      reference.style.marginInlineStart = '12px';
      card.append(reference);
    });
  }

  const sortKnownDates = sortGames;
  sortGames = function (a, b) {
    const today = taiwanTodayISO();
    return sortKnownDates(
      { date: a.date || estimatedUpdate(a, today) },
      { date: b.date || estimatedUpdate(b, today) }
    );
  };

  function decorateOverview() {
    const today = taiwanTodayISO();
    for (const button of app.querySelectorAll('[data-open]')) {
      const card = button.closest('article');
      const game = seed.find(item => item.id === button.dataset.open);
      if (!card || !game) continue;
      card.querySelector(':scope > .row')?.classList.add('overview-heading');
      const estimate = estimatedUpdate(game, today);
      if (!estimate) continue;
      const date = card.querySelector('.summaryline .date');
      if (!date) continue;
      addText(date.parentElement, 'div', 'overview-estimated-date', '預計更新日期：' + estimate + '（依卡池時程推估）');
    }
  }

  const renderSite = window.render;
  window.render = function () {
    if (tab === 'history' || tab === 'quality') {
      applyReviewedHistory();
      mergeHistoricalBannerDetails();
      prepareEndfieldHistory();
    }
    if (tab === 'history') restoreHistoryPosters();
    const result = renderSite();
    if (tab === 'history') renderHistoryDetails();
    if (tab === 'timeline') decorateOverview();
    return result;
  };

  new MutationObserver(() => paintPhases()).observe(document.getElementById('app'), { childList: true });

  ['character-art', 'discovered-art'].forEach(async (catalog, i) => {
    try {
      const response = await fetch('./data/' + catalog + '.json?v=phase2', { cache: 'no-cache' });
      if (response.ok) catalogs[i] = await response.json();
      render();
      if (tab === 'history' && restoreHistoryPosters()) window.render();
      paintPhases();
    } catch { /* Existing card data remains available offline. */ }
  });
  fetch('./data/history-character-art.json', { cache: 'no-cache' }).then(async response => {
    if (!response.ok) return;
    historyArt = await response.json();
    if (tab === 'history') window.render();
  }).catch(error => console.warn('Historical character images:', error.message));

  let timer;
  function resume() {
    clearInterval(timer);
    if (document.hidden) return;
    render();
    paintPhases();
    timer = setInterval(() => { render(Date.now() >= heroUntil); paintPhases(true); }, 250);
  }
  document.addEventListener('visibilitychange', resume);
  resume();
})();

// Official records may have a confirmed opening time and a pending closing time.
{
  const parseDatedVersion = syncedVersion;
  syncedVersion = function (record) {
    const dated = parseDatedVersion(record);
    if (dated || record?.end !== null) return dated;
    const start = verifiedTime(record.start);
    if (!start) return null;
    const temporaryEnd = new Date(Date.parse(start) + 60000).toISOString();
    const parsed = parseDatedVersion({ ...record, end: temporaryEnd });
    if (!parsed) return null;
    return { ...parsed, end: null, phases: parsed.phases.map(p => ({
      ...p, end: p.end || p.end_note || null
    })) };
  };

  const applyOfficialFeed = applyVersionFeed;
  applyVersionFeed = function (game, patch) {
    const incoming = syncedVersion(patch.current_version);
    if (incoming && incoming.version !== game.current && game.version_start) {
      const localStart = verifiedTime(game.version_start) ||
        verifiedTime(game.version_start.replace(/^(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}).*$/, '$1T$2:00+08:00'));
      if (localStart && Date.parse(localStart) > Date.parse(incoming.start)) return true;
      Object.assign(game, {
        next: incoming.version,
        next_version_start: incoming.start,
        next_version_end: incoming.end,
        next_version_source: incoming.source,
        next_phases: incoming.phases
      });
      advanceWebsiteVersions();
    }
    const displayedPhases = game.phases || [];
    // A rejected record cannot replace a previously displayed version.
    const { current_version, ...otherFields } = patch;
    const accepted = !current_version || incoming ? patch : otherFields;
    const applied = applyOfficialFeed(game, accepted);
    if (incoming) game.phases = game.phases.map(p => ({ ...p, end: p.end || p.end_note || null }));
    if (applied && incoming?.version === game.current) {
      game.source_status = '官方版本公告';
      game.phases = mergeHistoryPhases(displayedPhases, game.phases);
      game.banner = game.phases.map(p => p.characters).join('、') || '待官方公布';
    }
    if (!game.preview_date && patch.upcoming_preview) {
      const previewStart = verifiedTime(patch.upcoming_preview.start);
      game.preview_date = previewStart && Date.parse(previewStart) >= Date.now() ? displayTime(previewStart) : null;
      game.preview_url = game.preview_date ? officialURL(patch.upcoming_preview?.url) : null;
    }
    return applied || Boolean(game.preview_date && patch.upcoming_preview);
  };
}

// Field-level editorial updates remain available while official feeds catch up.
{
  let snapshot = {};
  const applyFeed = applyVersionFeed;
  const renderPhase = phase;
  const confirmedDebuts = {
    starrail: { '4.7': ['星神★阿哈'] },
    endfield: { '1.6': ['祀', '明河'], '1.7': ['小刻'] },
    promilia: { '1.0 公測': ['塗山小玉', '源千代'] },
    nikke: { 'SKY ON THE ROCK': ['思凱'] },
    zzz: { '3.4': ['挽晝', '知更鳥', '卡芙卡'] },
    gfl2: { '伊利昂之圍・中篇': ['亞斯特莉亞'] }
  };
  phase = function (game, pool) {
    const names = poolNames(pool);
    const reruns = names.filter(name => poolIsRerun(pool, name));
    const version = game.next_phases?.includes(pool) ? game.next : game.current;
    const known = confirmedDebuts[game.id]?.[version] || [];
    const explicit = Array.isArray(pool.rerun_characters);
    const markup = renderPhase(game, explicit ? {
      ...pool,
      disable_inferred_rerun: false,
      new_characters: names.filter(name => !reruns.includes(name))
    } : pool);
    const template = document.createElement('template');
    template.innerHTML = markup;
    const layer = template.content.querySelector('.phase-backdrop');
    if (layer) layer.dataset.reruns = JSON.stringify(reruns);
    const heading = template.content.querySelector('.phase-heading strong');
    if (heading && names.length) {
      heading.textContent = pool.label + ' · ';
      names.forEach((name, index) => {
        if (index) heading.append('、');
        heading.append(name);
        const rerun = reruns.includes(name);
        if (rerun || known.includes(name) || pool.new_characters?.includes(name) || (explicit && !/待|預告/.test(name))) {
          const badge = document.createElement('span');
          badge.textContent = rerun ? '復刻' : 'NEW';
          badge.className = poolBadgeClass(badge.textContent);
          heading.append(badge);
        }
      });
    }
    return template.innerHTML;
  };

  function arrangeBanners(game) {
    const isRerun = pool => {
      const names = String(pool.characters || '').split('、').map(name => name.trim()).filter(Boolean);
      return names.length > 0 && names.every(name => pool.rerun_characters?.includes(name));
    };
    const row = snapshot[game.id];
    const matchesVersion = row && (game.current === row.for_version || game.current === row.current ||
      (game.id === 'promilia' && game.current === row.next));
    const snapshotArt = matchesVersion ? row.phase_art || {} : {};
    for (const pool of [...game.phases, ...(game.special_banners || []), ...(game.next_phases || [])]) {
      const detail = snapshotArt[pool.characters];
      if (detail) Object.assign(pool, detail);
    }
    const currentReruns = game.phases.filter(isRerun);
    if (currentReruns.length) {
      const special = [...(game.special_banners || []), ...currentReruns];
      game.special_banners = mergeHistoryPhases([], special);
      game.phases = game.phases.filter(pool => !isRerun(pool));
    }
    if (game.next_phases) {
      game.next_phases = [...game.next_phases.filter(pool => !isRerun(pool)), ...game.next_phases.filter(isRerun)];
    }
  }

  function applySnapshot(game) {
    const row = snapshot[game.id];
    if (!row || (game.current !== row.for_version && game.current !== row.current)) return false;
    const { for_version, replace_phases, phase_art, next, date, status, next_phases, next_version_start,
      next_version_source, preview_date, preview_url, ...current } = row;
    if (current.phases) {
      if (replace_phases) {
        current.phases = current.phases.map(pool => {
          const previous = game.phases.find(item => item.characters === pool.characters && item.start === pool.start);
          return { ...previous, ...pool, banner_image: pool.banner_image || previous?.banner_image };
        });
      } else {
        current.phases = current.phases.length ? mergeHistoryPhases(game.phases, current.phases) : [];
      }
    }
    Object.assign(game, current);
    if (!game.next_version_start || game.next_version_start === next_version_start) {
      Object.assign(game, { next, date, status });
      if (next_phases) game.next_phases = next_phases;
      if (next_version_start) Object.assign(game, { next_version_start, next_version_source });
      if (preview_date && !game.preview_date) game.preview_date = preview_date;
      if (preview_url) game.preview_url = preview_url;
    }
    return true;
  }

  applyVersionFeed = function (game, patch) {
    const applied = applyFeed(game, patch);
    const refreshed = applySnapshot(game);
    arrangeBanners(game);
    return refreshed || applied;
  };

  const renderSite = window.render;
  window.render = function () {
    seed.forEach(arrangeBanners);
    return renderSite();
  };

  fetch('./data/site-snapshot.json', { cache: 'no-cache' }).then(async response => {
    if (!response.ok) return;
    const payload = await response.json();
    if (payload.schema !== 1) return;
    snapshot = payload.games;
    seed.forEach(applySnapshot);
    advanceWebsiteVersions();
    seed.forEach(arrangeBanners);
    window.render();
  }).catch(error => console.warn('Gacha snapshot:', error.message));
}

// Search results rebuild the page, so keep the input in place until IME commits.
(function bindCompositionSafeSearch() {
  const isSearch = el => el?.id === 'search' || el?.id === 'history-search';
  let composing = null;
  let pendingRender = false;
  let commitTimer;
  const renderPage = window.render;

  window.render = function () {
    if (composing?.isConnected) {
      pendingRender = true;
      return;
    }
    pendingRender = false;
    const field = document.activeElement;
    const selection = isSearch(field) && [field.selectionStart, field.selectionEnd, field.selectionDirection];
    renderPage();
    if (!selection) return;
    const replacement = document.getElementById(field.id);
    if (!replacement || replacement === field) return;
    replacement.focus({ preventScroll: true });
    replacement.setSelectionRange(...selection);
  };

  function applySearch(field) {
    if (field.value === q && !pendingRender) return;
    q = field.value;
    window.render();
  }

  app.addEventListener('compositionstart', event => {
    if (!isSearch(event.target)) return;
    clearTimeout(commitTimer);
    composing = event.target;
  });

  app.addEventListener('compositionend', event => {
    const field = event.target;
    if (composing !== field) return;
    // Allow the final input event to update the value before reading it.
    commitTimer = setTimeout(() => {
      composing = null;
      if (field.isConnected) applySearch(field);
      else if (pendingRender) window.render();
    }, 0);
  });

  app.addEventListener('input', event => {
    const field = event.target;
    if (!isSearch(field)) return;
    event.stopImmediatePropagation();
    if (event.isComposing || composing === field) return;
    applySearch(field);
  }, true);
})();

// A cached feed can finish before this script installs the open-ended version parser.
gachaSyncV132();
