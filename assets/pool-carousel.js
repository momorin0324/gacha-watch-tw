(function poolCarousel() {
  const hero = document.querySelector('.pool-hero');
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  const catalogs = [{}, {}];
  let currentKey;
  let currentSlide = hero.firstElementChild;
  let preloaded;
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
        for (const name of String(phase.characters || '').split('、').map(n => n.trim()).filter(Boolean)) {
          const key = [game.id, name, end].join('|');
          if (!items.has(key)) items.set(key, { key, name, game, phase, end });
        }
      }
    }
    return [...items.values()];
  }

  function sources({ game, name, phase }) {
    return [...new Set([catalogs[0][game.id]?.[name], catalogs[1][game.id]?.[name],
      game.character_art?.[name], phase.banner_image].filter(Boolean))];
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
        image.src = urls[0];
        slide.append(image);
      }
      addText(slide, 'span', 'pool-game', item.game.name);
      addText(slide, 'span', 'pool-label', item.phase.label || '當期角色卡池');
      addText(slide, 'h1', '', item.name);
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
      state = { names: JSON.parse(layer.dataset.names), current: '', pending: '' };
      phaseStates.set(layer, state);
    }
    const game = seed.find(game => game.id === layer.dataset.game);
    if (!game) return;
    const urls = [...new Set(state.names.map(name =>
      sources({ game, name, phase: {} }).find(url => !failedUrls.has(url))
    ).filter(Boolean))];
    const poster = layer.dataset.poster;
    if (poster && !failedUrls.has(poster)) urls.splice(0, urls.length, poster);
    if (!urls.length || state.pending) return;
    const index = urls.indexOf(state.current);
    const next = urls[index < 0 ? 0 : (index + Number(advance)) % urls.length];
    if (next === state.current) return;
    state.pending = next;
    const img = new Image();
    img.alt = '';
    if (layer.classList.contains('history-character-backdrop')) {
      img.style.objectPosition = 'center 22%';
      if (layer.classList.contains('history-portrait-backdrop')) {
        img.style.width = 'min(32%, 135px)';
        img.style.objectFit = 'contain';
        img.style.objectPosition = 'center';
      }
    }
    img.onload = () => {
      state.pending = '';
      if (!layer.isConnected) return;
      const old = layer.lastElementChild;
      if (old && advance && !reducedMotion.matches) {
        old.classList.remove('pool-enter');
        old.classList.add('pool-exit');
        img.classList.add('pool-enter');
        setTimeout(() => old.remove(), 560);
      } else layer.replaceChildren();
      layer.append(img);
      state.current = next;
    };
    img.onerror = () => {
      failedUrls.add(next);
      state.pending = '';
      if (layer.isConnected) paintPhase(layer, false);
    };
    img.src = next;
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
      if (!/^\d+\.\d+(?:\.\d+)?$/.test(entry.version)) continue;
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
        if (phase.banner_image) continue;
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
    nte: ['S級角色', 'S級弧盤']
  };

  const endfieldArmory = {
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
    return [...new Map(records.map(item => [[item.pool, item.name, item.start].join('|'), item])).values()];
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
      const boxes = card.querySelector('.phasehistory');
      if (!boxes) return;
      boxes.replaceChildren();
      for (const pool of entry.phases || []) {
        const box = document.createElement('div');
        box.className = 'phasebox history-phase illustrated-phase';
        const name = pool.five_star || pool.characters || '';
        const names = (Array.isArray(name) ? name : name.split('、')).map(value => value.trim()).filter(Boolean);
        if (names.length || pool.banner_image) {
          const layer = document.createElement('div');
          layer.className = 'phase-backdrop history-character-backdrop';
          layer.dataset.game = entry.game;
          layer.dataset.names = JSON.stringify(names);
          layer.dataset.poster = pool.banner_image || pool.portrait_image || '';
          if (!pool.banner_image && pool.portrait_image) layer.classList.add('history-portrait-backdrop');
          layer.setAttribute('aria-hidden', 'true');
          box.style.minHeight = '128px';
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
          if ((pool.rerun_characters || []).includes(value)) addText(characters, 'span', 'rerun-tag', '復刻');
        });
        if (!names.length) characters.append('待核對');
        copy.append(characters);
        if (entry.game === 'endfield') {
          const armory = historicalArmory(pool);
          if (!armory.length) addText(copy, 'div', '', labels[1] + '：' + (pool.weapons || '申領資料待核對'));
          for (const weapon of armory) {
            const line = document.createElement('div');
            line.className = 'weapon-line';
            addText(line, 'strong', '', (weapon.pool || '武器申領') + '：' + (weapon.name || '待核對'));
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
          addText(copy, 'div', '', labels[1] + '：' + (pool.weapons || '待核對'));
          if (pool.weapon_banner_name) addText(copy, 'div', 'small', pool.weapon_banner_name);
        }
        box.append(copy);
        boxes.append(box);
      }
      const slug = { starrail: 'hsr' }[entry.game] || entry.game;
      const reference = document.createElement('a');
      reference.href = 'https://bannerhistory.app/tw/' + slug + '-pickup-history';
      reference.target = '_blank';
      reference.rel = 'noopener noreferrer';
      reference.textContent = '繁中卡池比對';
      reference.style.marginInlineStart = '12px';
      card.append(reference);
    });
  }

  const renderSite = window.render;
  window.render = function () {
    if (tab === 'history' || tab === 'quality') {
      applyReviewedHistory();
      mergeHistoricalBannerDetails();
    }
    if (tab === 'history') restoreHistoryPosters();
    const result = renderSite();
    if (tab === 'history') renderHistoryDetails();
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
  let timer;
  function resume() {
    clearInterval(timer);
    if (document.hidden) return;
    render();
    paintPhases();
    timer = setInterval(() => { render(true); paintPhases(true); }, 4000);
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
  phase = function (game, pool) {
    const names = String(pool.characters || '').split('、').filter(Boolean);
    const explicit = Array.isArray(pool.rerun_characters);
    return renderPhase(game, explicit ? {
      ...pool,
      disable_inferred_rerun: false,
      new_characters: names.filter(name => !pool.rerun_characters.includes(name.trim()))
    } : pool);
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

// A cached feed can finish before this script installs the open-ended version parser.
gachaSyncV132();
