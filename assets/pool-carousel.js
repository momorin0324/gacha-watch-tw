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
    if (!urls.length && poster && !failedUrls.has(poster)) urls.push(poster);
    if (!urls.length || state.pending) return;
    const index = urls.indexOf(state.current);
    const next = urls[index < 0 ? 0 : (index + Number(advance)) % urls.length];
    if (next === state.current) return;
    state.pending = next;
    const img = new Image();
    img.alt = '';
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

  const renderSite = window.render;
  window.render = function () {
    if (tab === 'history') restoreHistoryPosters();
    return renderSite();
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
    const applied = applyOfficialFeed(game, patch);
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
