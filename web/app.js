// MovieBox Cosmic Edition v1.4.0 (Client Hub Engine)
let currentCatalog = { media: [], apks: [], live_tv: [], manhwa: [], novels: [], music: [], radio: [], wishlist: [] };
let activeFilter = 'all';
let activeLiveFilter = 'all';
let currentPlayingItem = null;
let currentStreamMode = 'direct';
let currentMusicList = [];
let currentMusicIndex = 0;
let arcadeAnimationId = null;

// --- 1. Live Digital Cinema Clock ---
function initClock() {
  const clockEl = document.getElementById('clock-display');
  function update() {
    const now = new Date();
    const h = String(now.getHours()).padStart(2, '0');
    const m = String(now.getMinutes()).padStart(2, '0');
    const s = String(now.getSeconds()).padStart(2, '0');
    if (clockEl) clockEl.textContent = `${h}:${m}:${s}`;
  }
  update();
  setInterval(update, 1000);
}

// --- 2. Tab Navigation ---
function initTabs() {
  const tabs = document.querySelectorAll('.tab-btn');
  tabs.forEach(btn => {
    btn.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      btn.classList.add('active');
      const target = btn.dataset.tab;
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
      const activeContent = document.getElementById(`tab-${target}`);
      if (activeContent) activeContent.classList.add('active');
    });
  });

  // Readers toggle
  document.getElementById('toggle-manhwa-view')?.addEventListener('click', () => {
    document.getElementById('toggle-manhwa-view').classList.add('active');
    document.getElementById('toggle-novels-view').classList.remove('active');
    document.getElementById('manhwa-shelf').style.display = 'grid';
    document.getElementById('novels-shelf').style.display = 'none';
  });
  document.getElementById('toggle-novels-view')?.addEventListener('click', () => {
    document.getElementById('toggle-novels-view').classList.add('active');
    document.getElementById('toggle-manhwa-view').classList.remove('active');
    document.getElementById('novels-shelf').style.display = 'grid';
    document.getElementById('manhwa-shelf').style.display = 'none';
  });

  // Music tabs toggle
  document.getElementById('btn-music-tracks')?.addEventListener('click', () => {
    document.getElementById('btn-music-tracks').classList.add('active');
    document.getElementById('btn-music-radio').classList.remove('active');
    renderMusicTracks();
  });
  document.getElementById('btn-music-radio')?.addEventListener('click', () => {
    document.getElementById('btn-music-radio').classList.add('active');
    document.getElementById('btn-music-tracks').classList.remove('active');
    renderRadioStations();
  });

  // Phone Gamepad Toggle
  document.getElementById('btn-open-gamepad-mode')?.addEventListener('click', () => {
    const modal = document.getElementById('gamepad-modal');
    if (modal) {
      modal.style.display = 'flex';
      modal.classList.add('active');
    }
  });
  document.getElementById('btn-close-gamepad')?.addEventListener('click', () => {
    const modal = document.getElementById('gamepad-modal');
    if (modal) {
      modal.style.display = 'none';
      modal.classList.remove('active');
    }
  });
}

// --- 3. Filter Pills ---
function initFilters() {
  document.querySelectorAll('#movie-filter-pills .pill-btn').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('#movie-filter-pills .pill-btn').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      activeFilter = pill.dataset.filter;
      renderMovies();
    });
  });

  document.querySelectorAll('#live-filter-pills .pill-btn').forEach(pill => {
    pill.addEventListener('click', () => {
      document.querySelectorAll('#live-filter-pills .pill-btn').forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      activeLiveFilter = pill.dataset.liveFilter;
      renderLiveTV();
    });
  });

  document.getElementById('search-input')?.addEventListener('input', () => {
    renderMovies();
    renderLiveTV();
    renderApps();
    renderMusicTracks();
  });
}

// --- 4. Fetch Catalog Data ---
async function fetchCatalog() {
  try {
    const res = await fetch('/api/catalog');
    if (!res.ok) throw new Error('Catalog fetch failed');
    currentCatalog = await res.json();

    const nodeInfo = document.getElementById('node-info');
    if (nodeInfo && currentCatalog.self) {
      nodeInfo.textContent = `${currentCatalog.self.name} (${currentCatalog.self.ip})`;
    }

    const netText = document.getElementById('net-text');
    if (netText) {
      const peerCount = (currentCatalog.peers || []).length;
      if (peerCount > 0) {
        netText.textContent = `🌌 Cosmic Mesh Linked: ${peerCount} peer node(s) connected.`;
      } else {
        netText.textContent = `🌌 Cinema Hub Active (${currentCatalog.self.ip}). Cross-device playback ready.`;
      }
    }

    renderMovies();
    renderLiveTV();
    renderApps();
    renderMusicTracks();
    renderReaders();
    renderWishlist();
  } catch (err) {
    console.error('Catalog error:', err);
  }
}

// --- 5. Render Movies ---
function renderMovies() {
  const grid = document.getElementById('movies-grid');
  const countPill = document.getElementById('media-count');
  if (!grid) return;

  const query = (document.getElementById('search-input')?.value || '').toLowerCase().trim();
  let list = currentCatalog.media || [];

  if (activeFilter === 'Sci-Fi') list = list.filter(m => m.category === 'Sci-Fi');
  else if (activeFilter === 'Action') list = list.filter(m => m.category === 'Action');
  else if (activeFilter === 'on-pc') list = list.filter(m => m.offloaded || m.is_pc);
  else if (activeFilter === 'on-phone') list = list.filter(m => !m.is_pc);

  if (query) {
    list = list.filter(m => 
      (m.title || '').toLowerCase().includes(query) ||
      (m.category || '').toLowerCase().includes(query) ||
      (m.year || '').includes(query)
    );
  }

  if (countPill) countPill.textContent = `${list.length} items`;
  if (list.length === 0) {
    grid.innerHTML = `<div class="empty-state">No matching movies found in local storage.</div>`;
    return;
  }

  grid.innerHTML = list.map(m => `
    <div class="movie-card" data-id="${m.id}">
      <div class="card-poster">
        <img src="${m.thumb_url || '/api/thumb/' + m.id}" alt="${m.title}" loading="lazy" onerror="this.src='/api/thumb/${m.id}'">
        <span class="poster-badge-top-left">${m.resolution || '1080p'}</span>
        <span class="poster-badge-top-right">${m.year || ''}</span>
      </div>
      <div class="card-body">
        <div class="card-title" title="${m.title}">${m.title}</div>
        <div class="card-tags">
          <span class="tag tag-blue">${m.category || 'Movie'}</span>
          <span class="tag">${m.audio || 'English 5.1'}</span>
          <span class="tag">${m.size || ''}</span>
          ${m.is_pc || m.offloaded ? '<span class="tag tag-green">💻 On PC</span>' : '<span class="tag tag-blue">📱 On Phone</span>'}
        </div>
        <div class="card-actions">
          <button class="btn-play" onclick="playMedia('${m.id}', 'direct')">▶ Stream</button>
          <button class="btn-remux" onclick="playMedia('${m.id}', 'transmux')" title="Live transmux for MKV/No VLC">⚡ Transmux</button>
        </div>
      </div>
    </div>
  `).join('');
}

// --- 6. Music Engine & Radio ---
function renderMusicTracks() {
  const grid = document.getElementById('music-grid');
  const countPill = document.getElementById('music-count');
  if (!grid) return;

  const list = currentCatalog.music || [];
  currentMusicList = list;
  if (countPill) countPill.textContent = `${list.length} tracks`;

  if (list.length === 0) {
    grid.innerHTML = `<div class="empty-state">No music files found in /sdcard/Music or storage.</div>`;
    return;
  }

  grid.innerHTML = list.map((trk, i) => `
    <div class="movie-card" onclick="playMusicTrack(${i})">
      <div class="card-poster" style="display:flex; align-items:center; justify-content:center; background:#0a1226;">
        <span style="font-size:2.8rem;">🎵</span>
        <span class="poster-badge-top-left">${trk.format}</span>
        <span class="poster-badge-top-right">${trk.size}</span>
      </div>
      <div class="card-body">
        <div class="card-title">${trk.title}</div>
        <div class="card-actions">
          <button class="btn-play" style="width:100%;">▶ Play Track</button>
        </div>
      </div>
    </div>
  `).join('');
}

function renderRadioStations() {
  const grid = document.getElementById('music-grid');
  if (!grid) return;

  const list = currentCatalog.radio || [];
  grid.innerHTML = list.map(st => `
    <div class="movie-card" onclick="playRadioStream('${encodeURIComponent(st.url)}', '${encodeURIComponent(st.title)}')">
      <div class="card-poster" style="display:flex; align-items:center; justify-content:center; background:#061f18;">
        <span style="font-size:2.8rem;">📻</span>
        <span class="poster-badge-top-left">Radio</span>
      </div>
      <div class="card-body">
        <div class="card-title">${st.title}</div>
        <div class="card-actions">
          <button class="btn-play" style="width:100%;">▶ Tune In Live</button>
        </div>
      </div>
    </div>
  `).join('');
}

function playMusicTrack(index) {
  if (!currentMusicList[index]) return;
  currentMusicIndex = index;
  const track = currentMusicList[index];

  const bar = document.getElementById('music-player-bar');
  if (bar) {
    bar.style.display = 'flex';
    bar.classList.add('active');
  }

  const audio = document.getElementById('audio-engine');
  const title = document.getElementById('music-bar-title');
  const sub = document.getElementById('music-bar-sub');
  const playBtn = document.getElementById('btn-music-play');

  if (title) title.textContent = track.title;
  if (sub) sub.textContent = `${track.format} • ${track.size}`;

  audio.src = track.stream_url;
  audio.play().catch(() => {});
  if (playBtn) playBtn.textContent = '⏸';
}

function playRadioStream(urlEnc, titleEnc) {
  const url = decodeURIComponent(urlEnc);
  const title = decodeURIComponent(titleEnc);

  const bar = document.getElementById('music-player-bar');
  if (bar) {
    bar.style.display = 'flex';
    bar.classList.add('active');
  }

  const audio = document.getElementById('audio-engine');
  const titleEl = document.getElementById('music-bar-title');
  const subEl = document.getElementById('music-bar-sub');
  const playBtn = document.getElementById('btn-music-play');

  if (titleEl) titleEl.textContent = title;
  if (subEl) subEl.textContent = 'Live Cosmic Web Radio';

  audio.src = url;
  audio.play().catch(() => {});
  if (playBtn) playBtn.textContent = '⏸';
}

// --- 7. Built-in Cosmic Arcade Game ("Cosmic Starfighter") ---
function startArcadeGame(gameType) {
  const modal = document.getElementById('arcade-modal');
  const canvas = document.getElementById('arcade-canvas');
  const ctx = canvas.getContext('2d');
  if (modal) {
    modal.style.display = 'flex';
    modal.classList.add('active');
  }

  // Cancel any running loop
  if (arcadeAnimationId) cancelAnimationFrame(arcadeAnimationId);

  // Game state
  let player = { x: canvas.width / 2 - 16, y: canvas.height - 48, w: 32, h: 32, speed: 6 };
  let lasers = [];
  let enemies = [];
  let score = 0;
  let keys = {};

  window.onkeydown = (e) => { keys[e.code] = true; };
  window.onkeyup = (e) => { keys[e.code] = false; };

  // Spawn enemy every 60 frames
  let frame = 0;

  function loop() {
    frame++;
    // Controls: Keyboard or Phone Gamepad
    if (keys['ArrowLeft'] || keys['KeyA']) player.x -= player.speed;
    if (keys['ArrowRight'] || keys['KeyD']) player.x += player.speed;
    if (keys['ArrowUp'] || keys['KeyW']) player.y -= player.speed;
    if (keys['ArrowDown'] || keys['KeyS']) player.y += player.speed;

    // Bounds
    player.x = Math.max(0, Math.min(canvas.width - player.w, player.x));
    player.y = Math.max(0, Math.min(canvas.height - player.h, player.y));

    // Fire laser
    if ((keys['Space'] || keys['KeyZ']) && frame % 12 === 0) {
      lasers.push({ x: player.x + 14, y: player.y, w: 4, h: 12, speed: 9 });
    }

    // Spawn enemies
    if (frame % 45 === 0) {
      enemies.push({ x: Math.random() * (canvas.width - 30), y: -30, w: 28, h: 28, speed: 2 + Math.random() * 2 });
    }

    // Update lasers
    lasers.forEach(l => l.y -= l.speed);
    lasers = lasers.filter(l => l.y > -20);

    // Update enemies
    enemies.forEach(e => e.y += e.speed);

    // Bullet-Enemy Collisions
    lasers.forEach((l, lIdx) => {
      enemies.forEach((en, eIdx) => {
        if (l.x < en.x + en.w && l.x + l.w > en.x && l.y < en.y + en.h && l.y + l.h > en.y) {
          enemies.splice(eIdx, 1);
          lasers.splice(lIdx, 1);
          score += 100;
        }
      });
    });

    enemies = enemies.filter(en => en.y < canvas.height + 40);

    // Render Cosmic Starfield & Entities
    ctx.fillStyle = '#05070f';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Stars
    ctx.fillStyle = 'rgba(255, 255, 255, 0.4)';
    for (let i = 0; i < 20; i++) {
      ctx.fillRect((frame * 2 + i * 40) % canvas.width, (i * 37) % canvas.height, 2, 2);
    }

    // Draw Player Ship (Cosmic Blue & Aurora Green)
    ctx.fillStyle = '#00e676';
    ctx.beginPath();
    ctx.moveTo(player.x + 16, player.y);
    ctx.lineTo(player.x, player.y + 32);
    ctx.lineTo(player.x + 32, player.y + 32);
    ctx.closePath();
    ctx.fill();

    // Draw Lasers
    ctx.fillStyle = '#00a8ff';
    lasers.forEach(l => ctx.fillRect(l.x, l.y, l.w, l.h));

    // Draw Enemies (Neon Crimson/Violet)
    ctx.fillStyle = '#f43f5e';
    enemies.forEach(en => {
      ctx.fillRect(en.x, en.y, en.w, en.h);
    });

    // Score
    ctx.fillStyle = '#ffffff';
    ctx.font = '16px "SF Mono", monospace';
    ctx.fillText(`SCORE: ${score}`, 16, 24);

    arcadeAnimationId = requestAnimationFrame(loop);
  }

  arcadeAnimationId = requestAnimationFrame(loop);
}

// --- 8. Phone Virtual Gamepad Touch Handlers ---
function initVirtualGamepad() {
  const buttons = document.querySelectorAll('.gamepad-overlay button[data-btn]');
  buttons.forEach(btn => {
    const btnKey = btn.dataset.btn;
    function sendState(isPressed) {
      fetch('/api/gamepad/input', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [btnKey]: isPressed })
      }).catch(() => {});
    }

    btn.addEventListener('touchstart', (e) => { e.preventDefault(); sendState(true); });
    btn.addEventListener('touchend', (e) => { e.preventDefault(); sendState(false); });
    btn.addEventListener('mousedown', () => sendState(true));
    btn.addEventListener('mouseup', () => sendState(false));
  });
}

// --- 9. In-Browser Cinema Player Modal ---
function playMedia(itemId, mode = 'direct') {
  const item = (currentCatalog.media || []).find(m => m.id === itemId);
  if (!item) return;

  currentPlayingItem = item;
  currentStreamMode = mode;

  const modal = document.getElementById('player-modal');
  const video = document.getElementById('cinema-video');
  const title = document.getElementById('player-title');
  const modeBtn = document.getElementById('btn-toggle-stream-mode');

  if (title) title.textContent = `${item.title} (${item.year || 'Cinema'})`;
  if (modeBtn) {
    modeBtn.textContent = mode === 'direct' ? 'Direct Stream' : 'Live Transmux';
    modeBtn.onclick = () => {
      playMedia(item.id, currentStreamMode === 'direct' ? 'transmux' : 'direct');
    };
  }

  let playUrl = mode === 'transmux' ? (item.live_url || `/play/live/${item.id}`) : (item.stream_url || item.url);
  video.onerror = () => {
    if (currentStreamMode === 'direct') {
      console.warn(`Direct playback failed for ${item.title}, auto-switching to live transmux...`);
      playMedia(itemId, 'transmux');
    }
  };
  video.src = playUrl;
  if (modal) {
    modal.style.display = 'flex';
    modal.classList.add('active');
  }
  video.play().catch(() => {});
}

function closePlayer() {
  const modal = document.getElementById('player-modal');
  const video = document.getElementById('cinema-video');
  if (video) {
    video.onerror = null;
    video.pause();
    video.src = '';
  }
  if (modal) {
    modal.style.display = 'none';
    modal.classList.remove('active');
  }
}

// --- 10. Live TV & Apps Vault ---
function renderLiveTV() {
  const grid = document.getElementById('live-grid');
  const countPill = document.getElementById('live-count');
  if (!grid) return;

  let list = currentCatalog.live_tv || [];
  if (activeLiveFilter !== 'all') {
    list = list.filter(ch => (ch.category || '').toLowerCase() === activeLiveFilter.toLowerCase());
  }
  if (countPill) countPill.textContent = `${list.length} channels`;

  grid.innerHTML = list.map(ch => `
    <div class="movie-card" onclick="playLiveStream('${encodeURIComponent(ch.url)}', '${encodeURIComponent(ch.title)}')">
      <div class="card-poster" style="display:flex; align-items:center; justify-content:center; background:#070d1a;">
        <span style="font-size: 2.4rem;">📺</span>
        <span class="poster-badge-top-left">${ch.category || 'Live'}</span>
      </div>
      <div class="card-body">
        <div class="card-title">${ch.title}</div>
        <div class="card-actions">
          <button class="btn-play" style="width:100%;">▶ Watch Live</button>
        </div>
      </div>
    </div>
  `).join('');
}

function playLiveStream(urlEncoded, titleEncoded) {
  const url = decodeURIComponent(urlEncoded);
  const title = decodeURIComponent(titleEncoded);
  const modal = document.getElementById('player-modal');
  const video = document.getElementById('cinema-video');
  const titleEl = document.getElementById('player-title');

  if (titleEl) titleEl.textContent = `📺 Live: ${title}`;
  video.src = url;
  if (modal) {
    modal.style.display = 'flex';
    modal.classList.add('active');
  }
  video.play().catch(() => {});
}

function renderApps() {
  const grid = document.getElementById('apps-grid');
  const countPill = document.getElementById('apk-count');
  if (!grid) return;

  const list = currentCatalog.apks || [];
  if (countPill) countPill.textContent = `${list.length} apps`;
  grid.innerHTML = list.map(app => `
    <div class="app-card">
      <div class="app-info">
        <h4>${app.title}</h4>
        <p>${app.platform} • ${app.size}</p>
      </div>
      <a href="${app.url}" class="btn-download" download>Download</a>
    </div>
  `).join('');
}

function renderReaders() {
  const mShelf = document.getElementById('manhwa-shelf');
  const nShelf = document.getElementById('novels-shelf');
  const mList = currentCatalog.manhwa || [];
  if (mShelf) {
    mShelf.innerHTML = mList.map(item => `
      <div class="movie-card">
        <div class="card-poster" style="display:flex; align-items:center; justify-content:center; background:#071224;">
          <span style="font-size:2.8rem;">📚</span>
          <span class="poster-badge-top-left">Webtoon</span>
        </div>
        <div class="card-body">
          <div class="card-title">${item.title}</div>
        </div>
      </div>
    `).join('');
  }
}

function renderWishlist() {
  const listEl = document.getElementById('wishlist-list');
  if (!listEl) return;
  const list = currentCatalog.wishlist || [];
  listEl.innerHTML = list.map(item => `
    <div class="wish-item">
      <div>
        <h4 style="font-size: 1rem; color: #fff;">${item.title}</h4>
        <p style="font-size: 0.8rem; color: #94a3b8;">${item.notes || 'Wanted'}</p>
      </div>
    </div>
  `).join('');
}

// --- 11. Initializer ---
document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initTabs();
  initFilters();
  initVirtualGamepad();
  fetchCatalog();
  setInterval(fetchCatalog, 8000);

  // Music controls
  const audio = document.getElementById('audio-engine');
  const playBtn = document.getElementById('btn-music-play');
  playBtn?.addEventListener('click', () => {
    if (audio.paused) {
      audio.play().catch(() => {});
      playBtn.textContent = '⏸';
    } else {
      audio.pause();
      playBtn.textContent = '▶';
    }
  });

  document.getElementById('btn-music-prev')?.addEventListener('click', () => {
    if (currentMusicList.length > 0) {
      playMusicTrack((currentMusicIndex - 1 + currentMusicList.length) % currentMusicList.length);
    }
  });
  document.getElementById('btn-music-next')?.addEventListener('click', () => {
    if (currentMusicList.length > 0) {
      playMusicTrack((currentMusicIndex + 1) % currentMusicList.length);
    }
  });

  // Modal close buttons
  document.getElementById('btn-close-player')?.addEventListener('click', closePlayer);
  document.getElementById('btn-close-arcade')?.addEventListener('click', () => {
    if (arcadeAnimationId) cancelAnimationFrame(arcadeAnimationId);
    const modal = document.getElementById('arcade-modal');
    if (modal) {
      modal.style.display = 'none';
      modal.classList.remove('active');
    }
  });

  // Keyboard Shortcuts
  window.addEventListener('keydown', (e) => {
    const modal = document.getElementById('player-modal');
    if (!modal || !modal.classList.contains('active')) return;
    const video = document.getElementById('cinema-video');
    if (e.code === 'Space') { e.preventDefault(); if (video.paused) video.play(); else video.pause(); }
    else if (e.code === 'KeyF') { e.preventDefault(); if (!document.fullscreenElement) video.requestFullscreen(); else document.exitFullscreen(); }
    else if (e.code === 'ArrowRight') { video.currentTime += 10; }
    else if (e.code === 'ArrowLeft') { video.currentTime -= 10; }
  });
});
