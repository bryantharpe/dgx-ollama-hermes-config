// State
const state = {
  talks: [],
  speakers: [],
  booths: [],
  contacts: [],
  pinnedBooths: [],
  currentDay: 'Day 1',
  activeTag: null,
  currentView: 'schedule',
  badge: null
};

// DOM Elements
const views = {
  schedule: document.getElementById('view-schedule'),
  expo: document.getElementById('view-expo'),
  qr: document.getElementById('view-qr'),
  contacts: document.getElementById('view-contacts')
};
const navBtns = document.querySelectorAll('.nav-btn');
const cmdPalette = document.getElementById('cmd-palette');
const cmdInput = document.getElementById('cmd-input');
const cmdResults = document.getElementById('cmd-results');
const talksList = document.getElementById('talks-list');
const tagFilters = document.getElementById('tag-filters');
const talkDetail = document.getElementById('talk-detail');
const detailTitle = document.getElementById('detail-title');
const detailInfo = document.getElementById('detail-info');
const detailDesc = document.getElementById('detail-desc');
const closeDetail = document.getElementById('close-detail');
const dayBtns = document.querySelectorAll('.day-btn');
const expoMap = document.getElementById('expo-map');
const expoSearch = document.getElementById('expo-search');
const calcRouteBtn = document.getElementById('calc-route-btn');
const contactsList = document.getElementById('contacts-list');

// Initialize
document.addEventListener('DOMContentLoaded', async () => {
  await loadInitialData();
  setupEventListeners();
  renderSchedule();
  renderTagFilters();
  renderContacts();
});

async function loadInitialData() {
  try {
    const [talksRes, speakersRes, boothsRes, badgeRes] = await Promise.all([
      fetch('/api/talks'),
      fetch('/api/speakers'),
      fetch('/api/booths'),
      fetch('/api/badge')
    ]);
    state.talks = await talksRes.json();
    state.speakers = await speakersRes.json();
    state.booths = await boothsRes.json();
    state.badge = await badgeRes.json();
    
    const pinnedRes = await fetch('/api/booths/pinned');
    state.pinnedBooths = await pinnedRes.json();
    
    renderBadge();
  } catch (err) {
    console.error('Failed to load data:', err);
  }
}

function setupEventListeners() {
  navBtns.forEach(btn => {
    btn.addEventListener('click', () => switchView(btn.dataset.view));
  });

  document.addEventListener('keydown', (e) => {
    if (e.ctrlKey && e.key === 'k') {
      e.preventDefault();
      toggleCmdPalette();
    }
  });
  
  cmdInput.addEventListener('input', debounce(() => searchCmdPalette(), 150));
  cmdInput.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      toggleCmdPalette(false);
    } else if (e.key === 'Enter' && cmdResults.querySelector('.cmd-result:hover')) {
      const result = cmdResults.querySelector('.cmd-result:hover');
      if (result) {
        result.click();
      }
    }
  });
  closeDetail.addEventListener('click', () => {
    talkDetail.classList.add('hidden');
  });
  
  dayBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      dayBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.currentDay = btn.dataset.day;
      renderSchedule();
    });
  });

  expoSearch.addEventListener('input', debounce(() => filterExpoBooths(), 150));
  calcRouteBtn.addEventListener('click', calculateRoute);
  document.addEventListener('click', (e) => {
    if (e.target.closest('.pin-btn')) {
      const boothId = parseInt(e.target.closest('.pin-btn').dataset.id);
      togglePinBooth(boothId);
    }
    if (e.target.closest('.booth-item')) {
      showBoothDetail(e.target.closest('.booth-item').dataset.id);
    }
    if (e.target.closest('.close-detail')) {
      document.getElementById('booth-detail').classList.add('hidden');
    }
  });

  document.getElementById('start-scan').addEventListener('click', startCamera);
  document.getElementById('start-scan').addEventListener('click', function() {
    if (this.dataset.stopped === 'true') {
      this.textContent = 'Start Camera';
      this.dataset.stopped = 'false';
      document.getElementById('qr-scanning').classList.add('hidden');
      document.getElementById('qr-generation').classList.remove('hidden');
      const video = document.getElementById('camera');
      if (video.srcObject) {
        video.srcObject.getTracks().forEach(track => track.stop());
        video.srcObject = null;
        video.style.display = 'none';
      }
    }
  });

  contactsList.addEventListener('click', (e) => {
    if (e.target.closest('.delete-btn')) {
      const contactId = parseInt(e.target.closest('.delete-btn').dataset.id);
      deleteContact(contactId);
    }
  });
}

function switchView(viewName) {
  state.currentView = viewName;
  Object.values(views).forEach(v => v.classList.remove('active'));
  views[viewName].classList.add('active');
  navBtns.forEach(b => b.classList.toggle('active', b.dataset.view === viewName));
  
  if (viewName === 'expo') {
    renderExpoMap();
  }
}

function toggleCmdPalette(forceState) {
  if (forceState === false || cmdPalette.classList.contains('active')) {
    cmdPalette.classList.remove('active');
    cmdInput.value = '';
    cmdResults.innerHTML = '';
  } else {
    cmdPalette.classList.add('active');
    cmdInput.focus();
  }
}

function debounce(fn, delay) {
  let timeout;
  return (...args) => {
    clearTimeout(timeout);
    timeout = setTimeout(() => fn.apply(null, args), delay);
  };
}

async function searchCmdPalette() {
  const query = cmdInput.value.trim();
  if (!query) {
    cmdResults.innerHTML = '';
    return;
  }
  
  try {
    const res = await fetch(`/api/talks/search?q=${encodeURIComponent(query)}`);
    const results = await res.json();
    
    cmdResults.innerHTML = results.map(talk => {
      const speaker = state.speakers.find(s => s.id === talk.speaker_id);
      return `<div class="cmd-result" data-id="${talk.id}">
        <div class="cmd-title">${escapeHtml(talk.title)}</div>
        <div class="cmd-meta">
          <span>${speaker ? escapeHtml(speaker.name) : 'Unknown'}</span>
          <span>${talk.day} ${talk.start_time}</span>
          <span>${talk.room}</span>
        </div>
        <div class="cmd-tags">${talk.tags.split(',').map(t => `<span class="tag">${escapeHtml(t.trim())}</span>`).join('')}</div>
      </div>`;
    }).join('');
    
    cmdResults.querySelectorAll('.cmd-result').forEach(result => {
      result.addEventListener('click', () => {
        const talk = state.talks.find(t => t.id === parseInt(result.dataset.id));
        if (talk) {
          showScheduleDetail(talk, true);
          toggleCmdPalette(false);
        }
      });
    });
  } catch (err) {
    console.error('Search failed:', err);
  }
}

function renderSchedule() {
  const filteredTalks = state.talks.filter(t => {
    if (state.activeTag && !t.tags.includes(state.activeTag)) return false;
    return t.day === state.currentDay;
  });
  
  talksList.innerHTML = filteredTalks.map(talk => {
    const speaker = state.speakers.find(s => s.id === talk.speaker_id);
    const timeRange = `${talk.start_time} - ${talk.end_time}`;
    const tags = talk.tags.split(',').map(t => `<span class="tag">${escapeHtml(t.trim())}</span>`).join('');
    
    return `<div class="talk-card" data-id="${talk.id}">
      <div class="talk-time">${timeRange}</div>
      <div class="talk-info">
        <div class="talk-title">${escapeHtml(talk.title)}</div>
        <div class="talk-speaker">${speaker ? escapeHtml(speaker.name) : 'TBA'}</div>
        <div class="talk-room">${escapeHtml(talk.room)}</div>
        <div class="talk-tags">${tags}</div>
      </div>
    </div>`;
  }).join('');
  
  talksList.querySelectorAll('.talk-card').forEach(card => {
    card.addEventListener('click', () => {
      const talk = state.talks.find(t => t.id === parseInt(card.dataset.id));
      if (talk) showScheduleDetail(talk);
    });
  });
}

function renderTagFilters() {
  const allTags = new Set();
  state.talks.forEach(t => t.tags.split(',').forEach(tag => allTags.add(tag.trim())));
  
  const tags = Array.from(allTags).sort();
  tagFilters.innerHTML = `<button class="tag-btn active" data-tag="">All</button>` +
    tags.map(tag => `<button class="tag-btn" data-tag="${tag}">${escapeHtml(tag)}</button>`).join('');
  
  tagFilters.querySelectorAll('.tag-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      tagFilters.querySelectorAll('.tag-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.activeTag = btn.dataset.tag || null;
      renderSchedule();
    });
  });
}

function showScheduleDetail(talk, replaceContent = false) {
  talkDetail.classList.remove('hidden');
  const speaker = state.speakers.find(s => s.id === talk.speaker_id);
  detailTitle.textContent = talk.title;
  detailInfo.innerHTML = `
    <div>${speaker ? `Speaker: ${escapeHtml(speaker.name)}` : 'TBA'}</div>
    <div>${talk.day} | ${talk.start_time} - ${talk.end_time}</div>
    <div>${escapeHtml(talk.room)}</div>
  `;
  detailDesc.textContent = talk.description || 'No description available.';
  detailDesc.classList.remove('hidden');
}

function renderBadge() {
  document.getElementById('badge-name').textContent = state.badge?.name || 'AI Engineer';
  document.getElementById('badge-github').textContent = state.badge?.github || 'ai-engineer';
  document.getElementById('badge-project').textContent = state.badge?.project || 'Worlds Fair Companion';
  document.getElementById('badge-source-id').textContent = state.badge?.source_id || 'badge-001';
  
  const qrText = JSON.stringify(state.badge);
  new QRCode(document.getElementById('qr-canvas'), {
    text: qrText,
    width: 128,
    height: 128,
    colorDark: '#c9d1d9',
    colorLight: '#0d1117',
    correctLevel: QRCode.CorrectLevel.H
  });
}

async function startCamera() {
  const video = document.getElementById('camera');
  const startScanDiv = document.getElementById('qr-scanning');
  
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    video.srcObject = stream;
    video.style.display = 'block';
    startScanDiv.classList.remove('hidden');
    document.getElementById('qr-generation').classList.add('hidden');
    document.getElementById('start-scan').textContent = 'Stop Camera';
    document.getElementById('start-scan').dataset.stopped = 'false';
  } catch (err) {
    alert('Camera access denied or not available');
    console.error(err);
  }
}

function renderExpoMap() {
  if (!state.booths.length) return;
  
  const hallABooths = state.booths.filter(b => b.hall === 'Hall A');
  const hallBBooths = state.booths.filter(b => b.hall === 'Hall B');
  
  let svgContent = `
    <svg viewBox="0 0 800 400" class="expo-svg">
      <rect x="0" y="0" width="400" height="400" fill="#0d1117" stroke="#30363d" stroke-width="2"/>
      <rect x="400" y="0" width="400" height="400" fill="#0d1117" stroke="#30363d" stroke-width="2"/>
      <text x="200" y="20" text-anchor="middle" fill="#58a6ff" font-size="16" font-weight="bold">HALL A</text>
      <text x="600" y="20" text-anchor="middle" fill="#58a6ff" font-size="16" font-weight="bold">HALL B</text>
      <g stroke="#21262d" stroke-width="1">
        ${[...Array(9)].map(i => `<line x1="${i * 50}" y1="0" x2="${i * 50}" y2="400"/>`).join('')}
        ${[...Array(9)].map(i => `<line x1="0" y1="${i * 50}" x2="800" y2="${i * 50}"/>`).join('')}
      </g>
      <circle cx="400" cy="380" r="8" fill="#3fb950" stroke="#238636" stroke-width="2"/>
      <text x="400" y="400" text-anchor="middle" fill="#3fb950" font-size="10">ENTRANCE</text>
    `;

  const renderHall = (booths, offsetX) => booths.map(b => {
    const x = b.grid_x * 50 + offsetX;
    const y = b.grid_y * 50;
    const isPinned = state.pinnedBooths.includes(b.id);
    const color = isPinned ? '#ff7b72' : '#58a6ff';
    
    svgContent += `
      <rect x="${x}" y="${y}" width="40" height="30" fill="#1f2428" stroke="${color}" stroke-width="${isPinned ? 2 : 1}" class="booth" data-id="${b.id}"/>
      <text x="${x + 20}" y="${y + 20}" text-anchor="middle" fill="${color}" font-size="9">${escapeHtml(b.booth_number || `Booth ${b.id}`)}</text>
      <text x="${x + 20}" y="${y + 38}" text-anchor="middle" fill="#c9d1d9" font-size="8">${escapeHtml(b.company_name.slice(0, 12))}</text>
    `;
  });

  renderHall(hallABooths, 0);
  renderHall(hallBBooths, 400);
  
  svgContent += '</svg>';
  expoMap.innerHTML = svgContent;
  
  expoMap.querySelectorAll('.booth').forEach(rect => {
    rect.addEventListener('click', (e) => {
      const boothId = parseInt(e.target.dataset.id);
      showBoothDetail(boothId);
    });
  });
}

function showBoothDetail(boothId) {
  let detailEl = document.getElementById('booth-detail');
  if (!detailEl) {
    detailEl = document.createElement('div');
    detailEl.id = 'booth-detail';
    detailEl.className = 'hidden';
    document.body.appendChild(detailEl);
  }
  
  const booth = state.booths.find(b => b.id === boothId);
  if (!booth) return;
  
  const isPinned = state.pinnedBooths.includes(boothId);
  
  detailEl.innerHTML = `
    <div class="booth-detail-content">
      <button class="close-btn" id="close-booth-detail">&times;</button>
      <h3>${escapeHtml(booth.company_name)}</h3>
      <p>${escapeHtml(booth.description)}</p>
      <div class="booth-tags">${booth.tags.split(',').map(t => `<span class="tag">${escapeHtml(t.trim())}</span>`).join('')}</div>
      <div class="booth-meta">
        <span>${booth.hall}</span>
        <span>Grid: ${booth.grid_x}, ${booth.grid_y}</span>
      </div>
      <button class="btn-primary pin-btn" data-id="${boothId}">
        ${isPinned ? 'Unpin' : 'Pin'} for Route
      </button>
    </div>
  `;
  detailEl.classList.remove('hidden');
  
  document.getElementById('close-booth-detail').addEventListener('click', () => {
    detailEl.classList.add('hidden');
  });
  
  detailEl.querySelector('.pin-btn').addEventListener('click', () => {
    togglePinBooth(boothId);
    detailEl.classList.add('hidden');
    renderExpoMap();
  });
}

function togglePinBooth(boothId) {
  const index = state.pinnedBooths.indexOf(boothId);
  if (index === -1) {
    state.pinnedBooths.push(boothId);
  } else {
    state.pinnedBooths.splice(index, 1);
  }
  fetch(`/api/booths/${boothId}/pin`, { method: 'POST' });
}

async function calculateRoute() {
  if (state.pinnedBooths.length < 2) {
    alert('Please pin at least 2 booths to calculate a route');
    return;
  }
  
  try {
    const res = await fetch('/api/routes/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ booth_ids: state.pinnedBooths })
    });
    const route = await res.json();
    
    const svg = expoMap.querySelector('svg');
    let pathPoints = '';
    let prevX = 400, prevY = 380;
    
    route.route.forEach(id => {
      const booth = state.booths.find(b => b.id === id);
      if (booth) {
        const offsetX = booth.hall === 'Hall A' ? 0 : 400;
        const x = booth.grid_x * 50 + offsetX + 20;
        const y = booth.grid_y * 50 + 15;
        pathPoints += `${prevX},${prevY} ${x},${y} `;
        prevX = x;
        prevY = y;
      }
    });
    
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', `M${pathPoints.trim()}`);
    path.setAttribute('stroke', '#3fb950');
    path.setAttribute('stroke-width', '3');
    path.setAttribute('fill', 'none');
    path.setAttribute('marker-end', 'url(#arrowhead)');
    
    if (!svg.querySelector('defs')) {
      const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
      const marker = document.createElementNS('http://www.w3.org/2000/svg', 'marker');
      marker.setAttribute('id', 'arrowhead');
      marker.setAttribute('markerWidth', '10');
      marker.setAttribute('markerHeight', '7');
      marker.setAttribute('refX', '9');
      marker.setAttribute('refY', '3.5');
      marker.setAttribute('orient', 'auto');
      const polygon = document.createElementNS('http://www.w3.org/2000/svg', 'polygon');
      polygon.setAttribute('points', '0 0, 10 3.5, 0 7');
      polygon.setAttribute('fill', '#3fb950');
      marker.appendChild(polygon);
      defs.appendChild(marker);
      svg.appendChild(defs);
    }
    
    svg.appendChild(path);
    
    const distance = route.distance.toFixed(1);
    alert(`Route calculated: ${route.route.length} booths, ~${distance}m walking distance`);
  } catch (err) {
    console.error('Route calculation failed:', err);
    alert('Failed to calculate route');
  }
}

function filterExpoBooths() {
  const query = expoSearch.value.toLowerCase();
  const booths = state.booths.filter(b => 
    b.company_name.toLowerCase().includes(query) ||
    b.tags.toLowerCase().includes(query) ||
    b.description.toLowerCase().includes(query)
  );
  
  state.booths = booths;
  renderExpoMap();
}

async function renderContacts() {
  try {
    const res = await fetch('/api/contacts');
    state.contacts = await res.json();
    
    contactsList.innerHTML = state.contacts.map(contact => `
      <div class="contact-card">
        <div class="contact-info">
          <div class="contact-name">${escapeHtml(contact.name)}</div>
          <div class="contact-meta">
            <a href="https://github.com/${escapeHtml(contact.github)}" target="_blank" class="contact-github">@${escapeHtml(contact.github)}</a>
            <span class="contact-project">${escapeHtml(contact.project)}</span>
          </div>
        </div>
        <button class="delete-btn" data-id="${contact.id}">&times;</button>
      </div>
    `).join('');
  } catch (err) {
    console.error('Failed to load contacts:', err);
  }
}

async function deleteContact(contactId) {
  try {
    await fetch(`/api/contacts/${contactId}`, { method: 'DELETE' });
    renderContacts();
  } catch (err) {
    console.error('Failed to delete contact:', err);
  }
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
