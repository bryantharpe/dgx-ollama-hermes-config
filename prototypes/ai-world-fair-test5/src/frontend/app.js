document.addEventListener('DOMContentLoaded', async () => {
    const status = document.getElementById('status');
    try {
        const res = await fetch('/api/health');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        status.textContent = `health: ${data.status}`;
        status.className = 'ok';
    } catch (err) {
        status.textContent = `health check failed: ${err.message}`;
        status.className = 'err';
    }

    window.addEventListener('hashchange', navigate);
    navigate();
});

const api = {
    get: async (path) => {
        const res = await fetch(`/api${path}`);
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },
    post: async (path, body) => {
        const res = await fetch(`/api${path}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    },
    del: async (path) => {
        const res = await fetch(`/api${path}`, { method: 'DELETE' });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
    }
};

function navigate() {
    const hash = window.location.hash.replace('#', '') || 'schedule';
    render(hash);
}

function render(page) {
    const app = document.getElementById('app');
    app.innerHTML = '';
    
    const nav = document.createElement('nav');
    nav.innerHTML = `
        <button onclick="navigateTo('schedule')" class="${page === 'schedule' ? 'active' : ''}">Schedule</button>
        <button onclick="navigateTo('expo')" class="${page === 'expo' ? 'active' : ''}">Expo Map</button>
        <button onclick="navigateTo('badge')" class="${page === 'badge' ? 'active' : ''}">Badge</button>
        <button onclick="navigateTo('contacts')" class="${page === 'contacts' ? 'active' : ''}">Contacts</button>
        <button onclick="navigateTo('about')" class="${page === 'about' ? 'active' : ''}">About</button>
    `;
    app.appendChild(nav);
    
    let content = document.createElement('main');
    content.id = 'main-content';
    app.appendChild(content);
    
    switch(page) {
        case 'schedule': renderSchedule(content); break;
        case 'expo': renderExpo(content); break;
        case 'badge': renderBadge(content); break;
        case 'contacts': renderContacts(content); break;
        case 'about': renderAbout(content); break;
        default: content.innerHTML = '<p>Unknown page</p>';
    }
}

window.navigateTo = (page) => {
    window.location.hash = page;
};

// ── schedule view ──
async function renderSchedule(container) {
    container.innerHTML = `
        <h2>Schedule</h2>
        <div class="filter-bar">
            <input type="text" id="schedule-filter" class="filter-input" placeholder="Filter talks...">
        </div>
        <div id="schedule-list" style="min-height: 200px;"></div>
    `;
    
    const events = await api.get('/talks');
    const pins = await api.get('/schedule');
    const pinnedIds = new Set(pins.map(t => t.id));
    
    container.querySelector('#schedule-filter').addEventListener('input', (e) => {
        renderScheduleList(events, pinnedIds, e.target.value);
    });
    
    renderScheduleList(events, pinnedIds);
}

function renderScheduleList(events, pinnedIds, filter = '') {
    const container = document.getElementById('schedule-list');
    if (!container) return;
    
    const filtered = events.filter(e => 
        e.title.toLowerCase().includes(filter.toLowerCase()) ||
        e.speaker_name.toLowerCase().includes(filter.toLowerCase()) ||
        e.topics.toLowerCase().includes(filter.toLowerCase())
    );
    
    if (filtered.length === 0) {
        container.innerHTML = '<div class="empty-state">No talks found</div>';
        return;
    }
    
    container.innerHTML = filtered.map(t => {
        const pinned = pinnedIds.has(t.id);
        const tags = t.topics.split(',').map(tag => `<span class="tag tag-topic">${tag}</span>`).join('');
        
        return `
            <div class="card schedule-item" data-talk-id="${t.id}">
                <div class="schedule-time">
                    <div>${t.start_time.slice(11, 16)}</div>
                    <div style="font-size:0.8rem">${t.room}</div>
                </div>
                <div class="schedule-content">
                    <h3 style="margin:0 0 0.5rem 0">${t.title}</h3>
                    <div class="schedule-meta">
                        <span>${t.speaker_name}</span>
                        <span>• ${t.level}</span>
                        <span>• ${t.track || 'General'}</span>
                    </div>
                    <div>${tags}</div>
                </div>
                <button onclick="togglePin(${t.id})">
                    ${pinned ? 'Unpin' : 'Pin'}
                </button>
            </div>
        `;
    }).join('');
}

async function togglePin(talkId) {
    try {
        const pins = await api.get('/schedule');
        const isPinned = pins.some(t => t.id === talkId);
        
        if (isPinned) {
            await api.del(`/schedule/unpin/${talkId}`);
        } else {
            await api.post('/schedule/pin', { talk_id: talkId });
        }
        renderSchedule(document.getElementById('main-content'));
    } catch (err) {
        alert(`Error: ${err.message}`);
    }
}

// ── badge view ──
async function renderBadge(container) {
    try {
        const badgeData = await api.get('/badge');
        
        container.innerHTML = `
            <h2>Your Badge</h2>
            <div id="badge-card"></div>
            <div class="badge-controls" style="margin-top:1rem">
                <button id="edit-badge">Edit Badge</button>
            </div>
        `;
        
        const card = container.querySelector('#badge-card');
        card.innerHTML = `
            <div class="badge-card">
                <h2 style="color:var(--accent)">${badgeData.name}</h2>
                <p style="margin:0 0 2rem 0">${badgeData.hacking_on}</p>
                <div class="badge-qr" id="qr-container"></div>
                <p style="color:var(--fg-dim);font-size:0.9rem">github.com/${badgeData.github || 'guest'}</p>
            </div>
        `;
        
        const qrOptions = {
            size: 180,
            colorDark: "#0d1117",
            colorLight: "#73daca",
            correctLevel: 0
        };
        new QRCode(container.querySelector('#qr-container'), Object.assign(qrOptions, { text: JSON.stringify(badgeData) }));
        
        container.querySelector('#edit-badge').addEventListener('click', () => {
            const name = prompt('Name:', badgeData.name || '');
            const github = prompt('GitHub:', badgeData.github || '');
            const hacking = prompt('Hacking on:', badgeData.hacking_on || '');
            
            if (name) {
                api.post('/badge', { name, github, hacking_on: hacking })
                    .then(() => renderBadge(container));
            }
        });
    } catch (err) {
        container.innerHTML = '<div class="empty-state">Error loading badge</div>';
    }
}

// ── expo map view ──
async function renderExpo(container) {
    try {
        const [booths, pins] = await Promise.all([
            api.get('/booths'),
            api.get('/expo/pins')
        ]);
        
        const currentPins = new Set(pins.map(b => b.id));
        
        container.innerHTML = `
            <h2>Expo Map</h2>
            <div id="expo-map-container" class="expo-map-container">
                <div id="expo-map" class="expo-map"></div>
                <div id="expo-info" class="expo-info"></div>
                <svg id="expo-route-overlay" class="expo-route-overlay">
                    <polyline id="expo-path" class="expo-route-line"></polyline>
                </svg>
            </div>
            <div class="expo-controls">
                <button id="calculate-route">Calculate Route</button>
                <button id="clear-route">Clear Route</button>
            </div>
            <div style="margin-top:1rem">
                <input type="text" id="booth-filter" class="filter-input" placeholder="Filter booths...">
            </div>
            <div id="booth-list"></div>
        `;
        
        renderExpoMap(booths, currentPins);
        
        container.querySelector('#booth-filter').addEventListener('input', (e) => {
            renderExpoBoothList(booths, currentPins, e.target.value);
        });
        renderExpoBoothList(booths, currentPins);
        
        container.querySelector('#calculate-route').addEventListener('click', async () => {
            const route = await api.get('/expo/route');
            if (route && route.booths && route.booths.length > 0) {
                renderExpoRoute(route);
            }
        });
        
        container.querySelector('#clear-route').addEventListener('click', () => {
            document.getElementById('expo-path').setAttribute('points', '');
        });
    } catch (err) {
        container.innerHTML = '<div class="empty-state">Error loading expo data</div>';
    }
}

function renderExpoMap(booths, pinnedIds, filter = '') {
    const container = document.getElementById('expo-map');
    if (!container) return;
    
    let html = '';
    html += '<div class="zone-label" style="top:50px;left:50px">Hall A</div>';
    html += '<div class="zone-label" style="top:50px;left:400px">Hall B</div>';
    html += '<div class="zone-label" style="top:50px;left:700px">Hall C</div>';
    
    const filtered = booths.filter(b => 
        b.name.toLowerCase().includes(filter.toLowerCase()) ||
        (b.topics && b.topics.toLowerCase().includes(filter.toLowerCase()))
    );
    
    html += filtered.map(b => `
        <div class="expo-marker ${pinnedIds.has(b.id) ? 'pinned' : ''}" 
             style="top:${b.grid_y * 15 + 80}px; left:${b.grid_x * 25 + 50}px"
             data-id="${b.id}"
             data-name="${b.name}"
             data-desc="${(b.description || '').replace(/"/g, '&quot;')}"
             data-zone="${b.zone}">
            ${b.id}
        </div>
    `).join('');
    
    container.innerHTML = html;
    
    container.querySelectorAll('.expo-marker').forEach(marker => {
        marker.addEventListener('click', (e) => {
            const id = parseInt(marker.dataset.id);
            const booth = booths.find(b => b.id === id);
            if (booth) showExpoInfo(e.clientX, e.clientY, booth);
            setTimeout(() => toggleBoothPin(id, booths, pinnedIds), 0);
        });
        
        marker.addEventListener('mouseover', (e) => {
            const id = parseInt(marker.dataset.id);
            const booth = booths.find(b => b.id === id);
            if (booth) showExpoInfo(e.clientX, e.clientY, booth);
        });
        
        marker.addEventListener('mouseout', hideExpoInfo);
    });
}

function renderExpoBoothList(booths, pinnedIds, filter = '') {
    const container = document.getElementById('booth-list');
    if (!container) return;
    
    const filtered = booths.filter(b => 
        b.name.toLowerCase().includes(filter.toLowerCase()) ||
        (b.topics && b.topics.toLowerCase().includes(filter.toLowerCase()))
    );
    
    if (filtered.length === 0) {
        container.innerHTML = '<div class="empty-state">No booths found</div>';
        return;
    }
    
    container.innerHTML = filtered.map(b => `
        <div class="card" style="display:flex;justify-content:space-between;align-items:center">
            <div>
                <strong>Booth #${b.id} - ${b.name}</strong>
                <div class="contact-hacking">${b.description}</div>
                <div class="tag">${b.zone}</div>
                ${b.topics ? b.topics.split(',').map(t => `<span class="tag tag-topic">${t}</span>`).join('') : ''}
            </div>
            <button onclick="toggleBoothPin(${b.id}, booths, currentPins)" data-booth-id="${b.id}">
                ${pinnedIds.has(b.id) ? 'Unpin' : 'Pin'}
            </button>
        </div>
    `).join('');
}

function renderExpoRoute(route) {
    if (!route || !route.booths || route.booths.length === 0) return;
    
    const polyline = document.getElementById('expo-path');
    if (!polyline) return;
    
    const points = route.booths.map(b => 
        `${b.grid_x * 25 + 62},${b.grid_y * 15 + 92}`
    ).join(' ');
    
    polyline.setAttribute('points', points);
}

function showExpoInfo(x, y, booth) {
    const info = document.getElementById('expo-info');
    if (!info) return;
    
    info.innerHTML = `
        <strong>${booth.name}</strong>
        <div>${booth.description}</div>
        <div class="tag">${booth.zone}</div>
    `;
    
    const rect = info.getBoundingClientRect();
    let top = y - rect.height - 10;
    let left = x - rect.width / 2;
    
    if (top < 10) top = y + 20;
    if (left < 10) left = 10;
    if (left + rect.width > window.innerWidth - 10) left = window.innerWidth - rect.width - 10;
    
    info.style.top = `${top}px`;
    info.style.left = `${left}px`;
    info.classList.add('visible');
}

function hideExpoInfo() {
    const info = document.getElementById('expo-info');
    if (info) info.classList.remove('visible');
}

async function toggleBoothPin(boothId, allBooths, currentPins) {
    try {
        const isPinned = currentPins.has(boothId);
        const method = isPinned ? 'DELETE' : 'POST';
        const url = isPinned 
            ? `/api/expo/unpin/${boothId}` 
            : '/api/expo/pin';
        
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ booth_id: boothId })
        });
        
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        
        if (isPinned) {
            currentPins.delete(boothId);
        } else {
            currentPins.add(boothId);
        }
        renderExpoMap(allBooths, currentPins);
        renderExpoBoothList(allBooths, currentPins);
    } catch (err) {
        alert(`Error: ${err.message}`);
    }
}

// ── contacts view ──
async function renderContacts(container) {
    try {
        const contacts = await api.get('/contacts');
        
        container.innerHTML = `
            <h2>Contacts</h2>
            <input type="text" id="contact-filter" class="filter-input" placeholder="Search contacts...">
            <div id="contact-list" class="contact-list"></div>
        `;
        
        container.querySelector('#contact-filter').addEventListener('input', (e) => {
            renderContactList(contacts, e.target.value);
        });
        
        renderContactList(contacts);
    } catch (err) {
        container.innerHTML = '<div class="empty-state">Error loading contacts</div>';
    }
}

function renderContactList(contacts, filter = '') {
    const container = document.getElementById('contact-list');
    if (!container) return;
    
    const filtered = contacts.filter(c =>
        c.name.toLowerCase().includes(filter.toLowerCase()) ||
        (c.github && c.github.toLowerCase().includes(filter.toLowerCase())) ||
        (c.hacking_on && c.hacking_on.toLowerCase().includes(filter.toLowerCase()))
    );
    
    if (filtered.length === 0) {
        container.innerHTML = '<div class="empty-state">No contacts yet. Scan badges at the expo!</div>';
        return;
    }
    
    container.innerHTML = filtered.map(c => `
        <div class="contact-item">
            <div>
                <strong>${c.name}</strong>
                <span class="contact-github">github.com/${c.github || 'guest'}</span>
                <div class="contact-hacking">${c.hacking_on}</div>
            </div>
        </div>
    `).join('');
}

// ── about view ──
function renderAbout(container) {
    container.innerHTML = `
        <h2>About</h2>
        <div class="card">
            <p>This is an unofficial community prototype for the AI Engineer World's Fair.</p>
            <p>All data is stored locally in your browser and SQLite database.</p>
            <p>No external network calls are made after initial load.</p>
        </div>
        <div class="card">
            <h3>Features</h3>
            <ul>
                <li>Schedule management with pin/unpin</li>
                <li>Expo map with route planning</li>
                <li>Digital badge and QR networking</li>
                <li>Command palette (Cmd+K)</li>
            </ul>
        </div>
        <footer>
            <p>AI Engineer World's Fair Companion &copy; 2026</p>
        </footer>
    `;
}
