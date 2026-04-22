(function() {
    'use strict';

    const Schedule = {
        apiBase: '/api/schedule',
        events: [],
        filteredEvents: [],
        selectedDay: 0,

        init: function() {
            this.loadEvents();
            this.setupFilters();
        },

        loadEvents: async function() {
            try {
                const response = await fetch(this.apiBase);
                if (!response.ok) throw new Error('Failed to load schedule');
                this.events = await response.json();
                this.filteredEvents = [...this.events];
                this.renderEvents();
            } catch (error) {
                console.error('Error loading schedule:', error);
                this.showErrorMessage('Unable to load schedule. Please try again.');
            }
        },

        setupFilters: function() {
            const dayFilters = document.querySelectorAll('.day-filter');
            dayFilters.forEach(filter => {
                filter.addEventListener('click', () => {
                    dayFilters.forEach(f => f.classList.remove('active'));
                    filter.classList.add('active');
                    const day = parseInt(filter.dataset.day);
                    this.filterByDay(day);
                });
            });

            const trackFilters = document.querySelectorAll('.track-filter');
            trackFilters.forEach(filter => {
                filter.addEventListener('click', () => {
                    trackFilters.forEach(f => f.classList.remove('active'));
                    filter.classList.add('active');
                    const track = filter.dataset.track;
                    this.filterByTrack(track);
                });
            });

            const searchInput = document.getElementById('schedule-search');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    this.filterBySearch(e.target.value);
                });
            }
        },

        filterByDay: function(day) {
            this.selectedDay = day;
            this.filteredEvents = this.events.filter(e => e.day === day);
            this.renderEvents();
        },

        filterByTrack: function(track) {
            if (!track || track === 'all') {
                this.filteredEvents = this.events.filter(e => e.day === this.selectedDay);
            } else {
                this.filteredEvents = this.events.filter(e => 
                    e.day === this.selectedDay && e.track === track
                );
            }
            this.renderEvents();
        },

        filterBySearch: function(query) {
            if (!query) {
                this.filteredEvents = this.events.filter(e => e.day === this.selectedDay);
            } else {
                const lowerQuery = query.toLowerCase();
                this.filteredEvents = this.events.filter(e => 
                    e.title.toLowerCase().includes(lowerQuery) ||
                    e.speaker.toLowerCase().includes(lowerQuery) ||
                    e.description.toLowerCase().includes(lowerQuery)
                );
            }
            this.renderEvents();
        },

        renderEvents: function() {
            const container = document.querySelector('.schedule-list');
            if (!container) return;

            if (this.filteredEvents.length === 0) {
                container.innerHTML = '<p class="no-events">No events found for this filter.</p>';
                return;
            }

            container.innerHTML = this.filteredEvents.map(event => this.createEventCard(event)).join('');
        },

        createEventCard: function(event) {
            return `
                <div class="event-card" data-id="${event.id}">
                    <div class="event-header">
                        <span class="event-time">${event.startTime} - ${event.endTime}</span>
                        <span class="event-track">${event.track}</span>
                    </div>
                    <h3 class="event-title">${event.title}</h3>
                    <p class="event-speaker">by ${event.speaker}</p>
                    <p class="event-description">${event.description}</p>
                    <div class="event-location">
                        <span>📍 ${event.location}</span>
                    </div>
                </div>
            `;
        },

        showErrorMessage: function(message) {
            const container = document.querySelector('.schedule-list');
            if (container) {
                container.innerHTML = `<p class="error-message">${message}</p>`;
            }
        }
    };

    window.Schedule = Schedule;
})();
