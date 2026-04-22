(function() {
    'use strict';

    const Expo = {
        apiBase: '/api/expo',
        booths: [],
        filteredBooths: [],
        selectedCategory: 'all',

        init: function() {
            this.loadBooths();
            this.setupFilters();
        },

        loadBooths: async function() {
            try {
                const response = await fetch(this.apiBase);
                if (!response.ok) throw new Error('Failed to load exhibitor list');
                this.booths = await response.json();
                this.filteredBooths = [...this.booths];
                this.renderBooths();
            } catch (error) {
                console.error('Error loading exhibitors:', error);
                this.showErrorMessage('Unable to load exhibitor list. Please try again.');
            }
        },

        setupFilters: function() {
            const categoryFilters = document.querySelectorAll('.expo-category');
            categoryFilters.forEach(filter => {
                filter.addEventListener('click', () => {
                    categoryFilters.forEach(f => f.classList.remove('active'));
                    filter.classList.add('active');
                    const category = filter.dataset.category;
                    this.filterByCategory(category);
                });
            });

            const searchInput = document.getElementById('expo-search');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    this.filterBySearch(e.target.value);
                });
            }
        },

        filterByCategory: function(category) {
            this.selectedCategory = category;
            if (category === 'all') {
                this.filteredBooths = [...this.booths];
            } else {
                this.filteredBooths = this.booths.filter(b => b.category === category);
            }
            this.renderBooths();
        },

        filterBySearch: function(query) {
            if (!query) {
                this.filteredBooths = this.booths.filter(b => 
                    this.selectedCategory === 'all' || b.category === this.selectedCategory
                );
            } else {
                const lowerQuery = query.toLowerCase();
                this.filteredBooths = this.booths.filter(b => 
                    (this.selectedCategory === 'all' || b.category === this.selectedCategory) &&
                    (b.companyName.toLowerCase().includes(lowerQuery) ||
                     b.description.toLowerCase().includes(lowerQuery))
                );
            }
            this.renderBooths();
        },

        renderBooths: function() {
            const container = document.querySelector('.expo-list');
            if (!container) return;

            if (this.filteredBooths.length === 0) {
                container.innerHTML = '<p class="no-booths">No exhibitors found for this filter.</p>';
                return;
            }

            container.innerHTML = this.filteredBooths.map(booth => this.createBoothCard(booth)).join('');
        },

        createBoothCard: function(booth) {
            return `
                <div class="booth-card" data-id="${booth.id}">
                    <div class="booth-header">
                        <span class="booth-number">Booth #${booth.number}</span>
                        <span class="booth-category">${booth.category}</span>
                    </div>
                    <h3 class="booth-company">${booth.companyName}</h3>
                    <p class="booth-description">${booth.description}</p>
                    <div class="booth-features">
                        ${booth.features.map(f => `<span class="feature-tag">${f}</span>`).join('')}
                    </div>
                    <div class="booth-actions">
                        <button class="btn btn-primary btn-sm" onclick="Expo.showDetails(${booth.id})">View Details</button>
                        <button class="btn btn-outline btn-sm" onclick="Expo.addFavorite(${booth.id})">♥</button>
                    </div>
                </div>
            `;
        },

        showDetails: function(id) {
            const booth = this.booths.find(b => b.id === id);
            if (booth) {
                const details = `
                    <h2>${booth.companyName}</h2>
                    <p><strong>Booth:</strong> #${booth.number}</p>
                    <p><strong>Category:</strong> ${booth.category}</p>
                    <p><strong>Website:</strong> <a href="${booth.website}" target="_blank">${booth.website}</a></p>
                    <p><strong>Contact:</strong> ${booth.contactEmail}</p>
                    <p><strong>Description:</strong> ${booth.description}</p>
                    <p><strong>Features:</strong> ${booth.features.join(', ')}</p>
                `;
                this.showModal('Exhibitor Details', details);
            }
        },

        addFavorite: function(id) {
            const booth = this.booths.find(b => b.id === id);
            if (booth) {
                let favorites = JSON.parse(localStorage.getItem('expoFavorites') || '[]');
                if (!favorites.includes(id)) {
                    favorites.push(id);
                    localStorage.setItem('expoFavorites', JSON.stringify(favorites));
                    alert(`${booth.companyName} added to favorites`);
                }
            }
        },

        getFavorites: function() {
            const favorites = JSON.parse(localStorage.getItem('expoFavorites') || '[]');
            return this.booths.filter(b => favorites.includes(b.id));
        },

        showModal: function(title, content) {
            const modal = document.getElementById('booth-modal');
            if (modal) {
                document.querySelector('.modal-content h2').textContent = title;
                document.querySelector('.modal-content .modal-body').innerHTML = content;
                modal.classList.add('active');
            }
        },

        closeModal: function() {
            const modal = document.getElementById('booth-modal');
            if (modal) {
                modal.classList.remove('active');
            }
        },

        showErrorMessage: function(message) {
            const container = document.querySelector('.expo-list');
            if (container) {
                container.innerHTML = `<p class="error-message">${message}</p>`;
            }
        }
    };

    window.Expo = Expo;
})();
