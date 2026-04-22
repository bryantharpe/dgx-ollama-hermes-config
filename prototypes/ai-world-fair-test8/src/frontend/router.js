// Route handling
window.route = {
    currentHash: '',

    init() {
        window.addEventListener('hashchange', () => this.handleHash());
        this.handleHash();
    },

    handleHash() {
        const hash = window.location.hash.slice(1) || '/';
        this.currentHash = hash;
        this.updateNav();
        this.renderView(hash);
    },

    navigate(path) {
        window.location.hash = path;
    },

    updateNav() {
        document.querySelectorAll('.sidebar-nav a').forEach(link => {
            const target = link.getAttribute('href').slice(1);
            const current = this.currentHash.split('/')[1] || '';
            const isActive = target === current || (target === '/' && current === '');
            link.classList.toggle('active', isActive);
        });
    },

    renderView(hash) {
        const container = document.getElementById('view-container');
        const path = hash.split('/').slice(1);

        if (path[0] === '' || path[0] === '/') {
            container.innerHTML = this.renderSearchView();
        } else if (path[0] === 'talk' && path[1]) {
            container.innerHTML = this.renderTalkDetail(path[1]);
        } else if (path[0] === 'speaker' && path[1]) {
            container.innerHTML = this.renderSpeakerDetail(path[1]);
        } else if (path[0] === 'schedule') {
            container.innerHTML = this.renderScheduleView();
        } else if (path[0] === 'expo') {
            container.innerHTML = this.renderExpoView();
        } else if (path[0] === 'badge') {
            container.innerHTML = this.renderBadgeView();
        } else if (path[0] === 'contacts') {
            container.innerHTML = this.renderContactsView();
        } else {
            container.innerHTML = `
                <h2>404</h2>
                <p>Page not found</p>
                <a href="#/" style="color: #58a6ff;">Back to home</a>
            `;
        }
    },

    renderSearchView() {
        const talks = window.app.state.talks;
        const tags = window.search.getTags(talks);
        return `
            <div style="padding: 1rem;">
                <div style="margin-bottom: 1.5rem;">
                    <h2 style="color: #58a6ff; margin: 0 0 0.5rem 0;">Search Talks</h2>
                    <p style="color: #8b949e;">Press <kbd style="color:#58a6ff;">Cmd+K</kbd> for instant search</p>
                </div>

                <div style="display: flex; gap: 1rem; margin-bottom: 1.5rem; flex-wrap: wrap;">
                    <div style="flex: 1; min-width: 200px;">
                        <label style="display: block; color: #8b949e; margin-bottom: 0.5rem; font-size: 0.85rem;">Track</label>
                        <select id="track-filter" class="filter-select">
                            <option value="">All Tracks</option>
                            <option value="Talk">Talk</option>
                            <option value="Workshop">Workshop</option>
                            <option value="Panel">Panel</option>
                        </select>
                    </div>
                    <div style="flex: 1; min-width: 200px;">
                        <label style="display: block; color: #8b949e; margin-bottom: 0.5rem; font-size: 0.85rem;">Tags</label>
                        <div id="tag-filters" style="display: flex; gap: 0.5rem; flex-wrap: wrap;"></div>
                    </div>
                </div>

                <div id="talk-list">
                    ${talks.map(t => this.renderTalkCard(t)).join('')}
                </div>
            </div>
        `;
    },

    renderTalkCard(talk) {
        const isBookmarked = window.app.bookmarks.has(talk.talk_id);
        return `
            <div class="talk-card" data-id="${talk.talk_id}">
                <div class="talk-card-header">
                    <div>
                        <h3 class="talk-card-title">${talk.title}</h3>
                        <div class="talk-card-meta">
                            <span class="talk-card-time">${talk.start_time.split('T')[1].slice(0,5)} - ${talk.end_time.split('T')[1].slice(0,5)}</span>
                            <span>•</span>
                            <span class="talk-card-room">${talk.room}</span>
                        </div>
                        <div style="display: flex; gap: 0.5rem; margin-top: 0.5rem;">
                            ${JSON.parse(talk.tags || '[]').map(tag => `<span class="talk-card-tag">${tag}</span>`).join('')}
                        </div>
                    </div>
                    <button class="talk-bookmark-btn" data-id="${talk.talk_id}" data-type="talk" style="
                        background: none; border: none; color: ${isBookmarked ? '#58a6ff' : '#8b949e'};
                        font-size: 1.5rem; cursor: pointer;
                    ">★</button>
                </div>
                <p style="color: #8b949e; margin: 0.5rem 0;">${talk.abstract}</p>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="level-badge ${talk.level || 'beginner'}">${talk.level || 'Beginner'}</span>
                    <button class="talk-detail-btn" data-id="${talk.talk_id}" style="
                        background: #58a6ff; border: none; color: #0d1117; padding: 0.5rem 1rem;
                        border-radius: 6px; cursor: pointer; font-weight: 600; font-family: inherit;
                    ">View Details</button>
                </div>
            </div>
        `;
    },

    renderTalkDetail(id) {
        const talk = window.app.state.talks.find(t => t.talk_id === id);
        if (!talk) return `<h2>404</h2><p>Talk not found</p>`;

        const isBookmarked = window.app.bookmarks.has(id);
        return `
            <div class="talk-card">
                <button onclick="window.route.navigate('#/')" style="
                    background: none; border: none; color: #8b949e; cursor: pointer;
                    margin-bottom: 1rem; font-family: inherit;
                ">← Back</button>

                <h2 style="color: #c9d1d9; margin-bottom: 1rem;">${talk.title}</h2>

                <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 2rem;">
                    <div>
                        <div class="talk-card-meta" style="margin-bottom: 1rem;">
                            <span class="talk-card-time">${talk.start_time.split('T')[1].slice(0,5)} - ${talk.end_time.split('T')[1].slice(0,5)}</span>
                            <span>•</span>
                            <span class="talk-card-room">${talk.room}</span>
                            <span>•</span>
                            <span>${talk.track}</span>
                            <span>•</span>
                            <span class="level-badge ${talk.level || 'beginner'}">${talk.level || 'Beginner'}</span>
                        </div>
                        <p style="color: #8b949e; line-height: 1.6;">${talk.abstract}</p>
                        <div style="display: flex; gap: 0.5rem; margin-top: 1rem;">
                            ${JSON.parse(talk.tags || '[]').map(tag => `<span class="talk-card-tag">${tag}</span>`).join('')}
                        </div>
                    </div>

                    <div>
                        <h3 style="color: #58a6ff; margin-top: 0;">Speaker</h3>
                        <div style="background: #161b22; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                            <p style="margin: 0; font-weight: 600;">Alice Chen</p>
                            <p style="margin: 0.25rem 0 0 0; color: #8b949e; font-size: 0.9rem;">Main Speaker</p>
                        </div>

                        <button class="talk-bookmark-btn" data-id="${talk.talk_id}" data-type="talk" style="
                            width: 100%; padding: 0.75rem; background: ${isBookmarked ? '#58a6ff' : '#21262d'};
                            border: none; border-radius: 6px; color: ${isBookmarked ? '#0d1117' : '#c9d1d9'};
                            cursor: pointer; font-weight: 600; font-family: inherit;
                        ">${isBookmarked ? 'Bookmarked' : 'Bookmark Talk'}</button>
                    </div>
                </div>
            </div>
        `;
    },

    renderSpeakerDetail(id) {
        return `<h2>Speaker ${id}</h2><p>Details coming soon</p><button onclick="window.route.navigate('#/')">Back</button>`;
    },

    renderScheduleView() {
        const talks = window.app.state.talks;
        const days = window.search.groupByDay(talks);
        const tracks = ['Talk', 'Workshop', 'Panel'];

        return `
            <div style="padding: 1rem;">
                <h2 style="color: #58a6ff; margin-bottom: 1rem;">Schedule</h2>

                <div class="schedule-day-header">
                    ${Object.keys(days).map(date => `
                        <button class="schedule-day-btn" data-date="${date}">
                            ${date}
                        </button>
                    `).join('')}
                </div>

                <div class="schedule-track-filter">
                    <span class="filter-label">Filter by:</span>
                    ${tracks.map(track => `
                        <button class="schedule-track-btn" data-track="${track}">${track}</button>
                    `).join('')}
                </div>

                <div class="search-filters" style="margin-top: 1rem;">
                    <span class="filter-label">Tags:</span>
                    ${window.search.getTags(talks).map(tag => `
                        <button class="filter-chip" data-tag="${tag}">${tag}</button>
                    `).join('')}
                </div>

                <div class="schedule-timeline">
                    <div class="schedule-time-col">
                        ${this.getTimeSlots().map(t => `<div class="schedule-time-slot">${t}</div>`).join('')}
                    </div>
                    <div class="schedule-talks-col">
                        ${Object.values(days).flat().map(talk => this.renderScheduleTalk(talk)).join('')}
                    </div>
                </div>
            </div>
        `;
    },

    renderScheduleTalk(talk) {
        const isConflict = window.search.detectConflicts([talk]).has(talk.talk_id);
        const isBookmarked = window.app.bookmarks.has(talk.talk_id);
        return `
            <div class="schedule-talk ${isBookmarked ? 'schedule-talk-bookmarked' : ''} ${isConflict ? 'schedule-talk-conFLICT' : ''}">
                <div class="schedule-talk-title">${talk.title}</div>
                <div class="schedule-talk-meta">${talk.room}</div>
                <div class="schedule-track-btn tag">${talk.track}</div>
            </div>
        `;
    },

    renderExpoView() {
        const booths = window.app.state.booths;
        return `
            <div class="expo-map-container" style="padding: 1rem;">
                <div style="margin-bottom: 1rem;">
                    <h2 style="color: #58a6ff; margin: 0 0 0.5rem 0;">Expo Floor Map</h2>
                    <p style="color: #8b949e;">Pick booths to visit and optimize your route</p>
                </div>

                <div class="expo-map-controls">
                    <button id="optimize-route-btn" class="expo-map-btn primary" onclick="alert('Route optimization coming soon')">Optimize Route</button>
                </div>

                <div class="expo-map-category-filter">
                    <span class="filter-label" style="color: #c9d1d9;">Category:</span>
                    ${['All', ...new Set(booths.map(b => b.category))].map(cat => `
                        <button class="expo-map-category-btn" data-category="${cat}">${cat}</button>
                    `).join('')}
                </div>

                <div style="margin-top: 1rem;">
                    <svg class="expo-map-svg" viewBox="0 0 1000 600">
                        <rect width="1000" height="600" fill="#0d1117" />
                        <g id="booths"></g>
                        <g id="route-overlay"></g>
                    </svg>
                    <div style="margin-top: 0.5rem; color: #8b949e; display: flex; gap: 1rem;">
                        <span>■ = Available</span>
                        <span style="color: #3fb950;">■ = Pinned</span>
                    </div>
                </div>
            </div>
        `;
    },

    renderBadgeView() {
        return `
            <div style="padding: 1rem;">
                <h2 style="color: #58a6ff;">My Digital Badge</h2>
                <p style="color: #8b949e;">Show this QR code to exchange contacts</p>

                <div class="badge-card">
                    <div class="badge-card-header">
                        <h2>AIPractitioner</h2>
                    </div>
                    <pre class="badge-card-data">
<span class="key">name:</span> AIPractitioner
<span class="key">github:</span> aiworldfair
<span class="key">topic:</span> LLMs and RAG
<span class="key">role:</span> AI Engineer
                    </pre>
                    <div class="badge-card-qr" id="badge-qr"></div>
                </div>
            </div>
        `;
    },

    renderContactsView() {
        return `
            <div style="padding: 1rem;">
                <h2 style="color: #58a6ff;">My Contacts</h2>
                <p style="color: #8b949e;">Contacts you've scanned via QR</p>
                <div id="contacts-list">
                    <p style="color: #8b949e;">No contacts yet. Scan someone's badge QR!</p>
                </div>
            </div>
        `;
    },

    getTimeSlots() {
        const times = [];
        for (let h = 9; h <= 18; h++) {
            const time = `${h.toString().padStart(2, '0')}:00`;
            times.push(time);
        }
        return times;
    },
};
