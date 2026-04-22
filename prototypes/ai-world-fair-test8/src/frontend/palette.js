// Command Palette
window.palette = {
    element: null,
    input: null,
    results: null,
    noResults: null,
    tabs: [],
    activeTab: 'talks',
    activeIndex: -1,
    lastQuery: '',
    resultsData: [],
    resultsType: 'talks',

    init() {
        this.element = document.getElementById('cmd-palette');
        this.input = document.getElementById('cmd-palette-input');
        this.results = document.getElementById('cmd-palette-results');
        this.noResults = document.querySelector('.cmd-palette-no-results');

        // Setup tabs
        this.tabs = Array.from(document.querySelectorAll('.cmd-palette-tab'));
        this.tabs.forEach(tab => {
            tab.addEventListener('click', () => this.switchTab(tab.dataset.tab));
        });

        // Setup input
        this.input.addEventListener('input', () => this.search(this.input.value));
        this.input.addEventListener('keydown', (e) => this.handleKeydown(e));
        this.input.addEventListener('blur', () => this.close());

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!this.element.contains(e.target) && e.target !== this.input) {
                this.close();
            }
        });

        // Cmd+K / Ctrl+K to open
        document.addEventListener('keydown', (e) => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                this.open();
            }
        });

        // Esc to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && !this.element.classList.contains('hidden')) {
                this.close();
                this.input.value = '';
            }
        });
    },

    open() {
        this.element.classList.remove('hidden');
        this.input.focus();
        this.search('');
    },

    close() {
        this.element.classList.add('hidden');
        this.activeIndex = -1;
        this.results.innerHTML = '';
        this.showNoResults(false);
    },

    switchTab(tab) {
        this.activeTab = tab;
        this.tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
        this.results.innerHTML = '';
        this.search(this.input.value);
    },

    async search(query) {
        if (query === this.lastQuery) return;
        this.lastQuery = query;
        this.activeIndex = -1;

        if (!query.trim()) {
            this.results.innerHTML = '';
            this.showNoResults(false);
            return;
        }

        this.resultsData = [];
        this.resultsType = this.activeTab;

        if (this.activeTab === 'talks') {
            const results = await window.app.api.searchTalks(query);
            this.resultsData = results.map(t => ({ type: 'talk', data: t }));
        } else if (this.activeTab === 'speakers') {
            const all = window.app.state.speakers;
            const term = query.toLowerCase();
            this.resultsData = all
                .filter(s => s.name.toLowerCase().includes(term) || s.bio?.toLowerCase().includes(term))
                .map(s => ({ type: 'speaker', data: s }));
        } else if (this.activeTab === 'booths') {
            const all = window.app.state.booths;
            const term = query.toLowerCase();
            this.resultsData = all
                .filter(b => b.name.toLowerCase().includes(term) || b.description?.toLowerCase().includes(term))
                .map(b => ({ type: 'booth', data: b }));
        }

        this.renderResults();
    },

    renderResults() {
        if (this.resultsData.length === 0) {
            this.showNoResults(true);
            return;
        }
        this.showNoResults(false);

        this.results.innerHTML = this.resultsData.map((item, idx) => `
            <div class="cmd-palette-result${idx === this.activeIndex ? ' active' : ''}" data-index="${idx}">
                <span class="cmd-palette-result-title">${this.getTitle(item)}</span>
                <span class="cmd-palette-result-meta">${this.getMeta(item)}</span>
            </div>
        `).join('');

        this.results.querySelectorAll('.cmd-palette-result').forEach((el, idx) => {
            el.addEventListener('click', () => this.select(idx));
        });
    },

    getTitle(item) {
        if (item.type === 'talk') return item.data.title;
        if (item.type === 'speaker') return item.data.name;
        if (item.type === 'booth') return item.data.name;
        return '';
    },

    getMeta(item) {
        if (item.type === 'talk') {
            return `${item.data.room} • ${item.data.start_time.split('T')[1].slice(0,5)} • ${item.data.speaker_id ? 'Alice Chen' : ''}`;
        }
        if (item.type === 'speaker') return item.data.company;
        if (item.type === 'booth') return item.data.category;
        return '';
    },

    showNoResults(show) {
        if (show) {
            this.noResults.classList.remove('hidden');
            this.results.style.display = 'none';
        } else {
            this.noResults.classList.add('hidden');
            this.results.style.display = 'block';
        }
    },

    handleKeydown(e) {
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.activeIndex = Math.min(this.activeIndex + 1, this.resultsData.length - 1);
            this.updateActive();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.activeIndex = Math.max(this.activeIndex - 1, -1);
            this.updateActive();
        } else if (e.key === 'Enter') {
            if (this.activeIndex >= 0) {
                this.select(this.activeIndex);
            }
        }
    },

    updateActive() {
        this.results.querySelectorAll('.cmd-palette-result').forEach((el, idx) => {
            el.classList.toggle('active', idx === this.activeIndex);
        });
    },

    select(index) {
        const item = this.resultsData[index];
        if (!item) return;

        this.close();

        if (item.type === 'talk') {
            window.route.navigate(`/talk/${item.data.talk_id}`);
        } else if (item.type === 'speaker') {
            window.route.navigate(`/speaker/${item.data.speaker_id}`);
        } else if (item.type === 'booth') {
            window.route.navigate(`/expo`);
            // Highlight the booth
            const boothEl = document.querySelector(`.expo-map-booth[data-id="${item.data.booth_id}"]`);
            if (boothEl) boothEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
    },
};
