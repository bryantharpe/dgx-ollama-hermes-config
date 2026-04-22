let currentBooths = [];
let currentPins = new Set();
let routePath = [];

async function renderExpo(container) {
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
    
    try {
        const [booths, pins] = await Promise.all([
            fetch('/api/booths').then(r => r.json()),
            fetch('/api/expo/pins').then(r => r.json())
        ]);
        
        currentBooths = booths;
        currentPins = new Set(pins.map(b => b.id));
        
        renderExpoMap();
        
        container.querySelector('#booth-filter').addEventListener('input', (e) => {
            renderExpoBoothList(e.target.value);
        });
        renderExpoBoothList('');
        
        container.querySelector('#calculate-route').addEventListener('click', async () => {
            try {
                const route = await fetch('/api/expo/route').then(r => r.json());
                renderExpoRoute(route);
            } catch (err) {
                console.error('Route error:', err);
            }
        });
        
        container.querySelector('#clear-route').addEventListener('click', () => {
            document.getElementById('expo-path').setAttribute('points', '');
            routePath = [];
        });
    } catch (err) {
        container.innerHTML = '<div class="empty-state">Error loading expo data</div>';
        console.error(err);
    }
}

function renderExpoMap(filter = '') {
    const container = document.getElementById('expo-map');
    if (!container) return;
    
    let html = '';
    html += '<div class="zone-label" style="top:50px;left:50px">Hall A</div>';
    html += '<div class="zone-label" style="top:50px;left:400px">Hall B</div>';
    html += '<div class="zone-label" style="top:50px;left:700px">Hall C</div>';
    
    const filtered = currentBooths.filter(b => 
        b.name.toLowerCase().includes(filter.toLowerCase()) ||
        (b.topics && b.topics.toLowerCase().includes(filter.toLowerCase()))
    );
    
    html += filtered.map(b => `
        <div class="expo-marker ${currentPins.has(b.id) ? 'pinned' : ''}" 
             style="top:${b.grid_y * 15 + 80}px; left:${b.grid_x * 25 + 50}px"
             data-id="${b.id}">
            ${b.id}
        </div>
    `).join('');
    
    container.innerHTML = html;
    
    container.querySelectorAll('.expo-marker').forEach(marker => {
        marker.addEventListener('click', (e) => {
            const id = parseInt(marker.dataset.id);
            const booth = currentBooths.find(b => b.id === id);
            if (booth) showExpoInfo(e.clientX, e.clientY, booth);
        });
        
        marker.addEventListener('mouseover', (e) => {
            const id = parseInt(marker.dataset.id);
            const booth = currentBooths.find(b => b.id === id);
            if (booth) showExpoInfo(e.clientX, e.clientY, booth);
        });
        
        marker.addEventListener('mouseout', hideExpoInfo);
    });
}

function renderExpoBoothList(filter = '') {
    const container = document.getElementById('booth-list');
    if (!container) return;
    
    const filtered = currentBooths.filter(b => 
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
            <button onclick="toggleBoothPin(${b.id})">
                ${currentPins.has(b.id) ? 'Unpin' : 'Pin'}
            </button>
        </div>
    `).join('');
}

function renderExpoRoute(route) {
    if (!route || !route.booths || route.booths.length === 0) return;
    
    const polyline = document.getElementById('expo-path');
    if (!polyline) return;
    
    routePath = route.booths;
    const points = routePath.map(b => 
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

async function toggleBoothPin(boothId) {
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
        
        currentPins = isPinned ? new Set([...currentPins].filter(id => id !== boothId)) : new Set([...currentPins, boothId]);
        renderExpoMap();
        renderExpoBoothList();
    } catch (err) {
        alert(`Error: ${err.message}`);
    }
}
