// Main application entry point
document.addEventListener('DOMContentLoaded', async () => {
    // Check health
    try {
        const res = await fetch('/api/health');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        console.log('Health check passed');
    } catch (err) {
        console.error('Health check failed:', err);
    }

    // Initialize app
    window.app = {
        bookmarks: new Set(),
        contacts: [],
        state: {
            currentView: 'search',
            talks: [],
            speakers: [],
            booths: [],
        },
        api: {
            async getTalks(params = {}) {
                const query = new URLSearchParams(params).toString();
                const res = await fetch(`/api/talks?${query}`);
                return await res.json();
            },
            async searchTalks(query) {
                const res = await fetch(`/api/talks/search?q=${encodeURIComponent(query)}`);
                return await res.json();
            },
            async getSpeakers() {
                const res = await fetch('/api/speakers');
                return await res.json();
            },
            async getSpeaker(id) {
                const res = await fetch(`/api/speakers/${id}`);
                return await res.json();
            },
            async getBooths(category = null) {
                let url = '/api/booths';
                if (category) url += `?category=${encodeURIComponent(category)}`;
                const res = await fetch(url);
                return await res.json();
            },
            async getBadge() {
                const res = await fetch('/api/badge');
                return await res.json();
            },
            async scanContact(rawJson) {
                const res = await fetch('/api/contacts/scan', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ raw_json: rawJson }),
                });
                return await res.json();
            },
            async getContacts() {
                const res = await fetch('/api/contacts');
                return await res.json();
            },
            async deleteContact(id) {
                const res = await fetch(`/api/contacts/${id}`, { method: 'DELETE' });
                return await res.json();
            },
            async getBookmarks() {
                const res = await fetch('/api/bookmarks');
                return await res.json();
            },
            async createBookmark(entityId, type) {
                const res = await fetch('/api/bookmarks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ entity_id: entityId, type: type }),
                });
                return await res.json();
            },
        },
    };

    // Load initial data
    await Promise.all([
        window.app.api.getTalks().then(data => window.app.state.talks = data),
        window.app.api.getSpeakers().then(data => window.app.state.speakers = data),
        window.app.api.getBooths().then(data => window.app.state.booths = data),
        window.app.api.getBookmarks().then(data => {
            window.app.bookmarks = new Set(data.map(b => b.entity_id));
        }),
    ]);

    // Initialize palette
    window.palette.init();

    // Initialize routing
    window.route.init();
});
