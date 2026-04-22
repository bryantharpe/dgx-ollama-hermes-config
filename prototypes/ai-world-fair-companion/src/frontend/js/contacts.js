(function() {
    'use strict';

    const Contacts = {
        apiBase: '/api/contacts',
        contacts: [],
        filteredContacts: [],
        selectedCategory: 'all',

        init: function() {
            this.loadContacts();
            this.setupFilters();
            this.setupScan();
        },

        loadContacts: async function() {
            try {
                const response = await fetch(this.apiBase);
                if (!response.ok) throw new Error('Failed to load contacts');
                this.contacts = await response.json();
                this.filteredContacts = [...this.contacts];
                this.renderContacts();
            } catch (error) {
                console.error('Error loading contacts:', error);
                this.showErrorMessage('Unable to load contacts. Please try again.');
            }
        },

        setupFilters: function() {
            const categoryFilters = document.querySelectorAll('.contact-category');
            categoryFilters.forEach(filter => {
                filter.addEventListener('click', () => {
                    categoryFilters.forEach(f => f.classList.remove('active'));
                    filter.classList.add('active');
                    const category = filter.dataset.category;
                    this.filterByCategory(category);
                });
            });

            const searchInput = document.getElementById('contacts-search');
            if (searchInput) {
                searchInput.addEventListener('input', (e) => {
                    this.filterBySearch(e.target.value);
                });
            }

            const addContactBtn = document.getElementById('add-contact');
            if (addContactBtn) {
                addContactBtn.addEventListener('click', () => this.showAddContactForm());
            }
        },

        filterByCategory: function(category) {
            this.selectedCategory = category;
            if (category === 'all') {
                this.filteredContacts = [...this.contacts];
            } else {
                this.filteredContacts = this.contacts.filter(c => c.category === category);
            }
            this.renderContacts();
        },

        filterBySearch: function(query) {
            if (!query) {
                this.filteredContacts = this.contacts.filter(c => 
                    this.selectedCategory === 'all' || c.category === this.selectedCategory
                );
            } else {
                const lowerQuery = query.toLowerCase();
                this.filteredContacts = this.contacts.filter(c => 
                    (this.selectedCategory === 'all' || c.category === this.selectedCategory) &&
                    (c.name.toLowerCase().includes(lowerQuery) ||
                     c.company.toLowerCase().includes(lowerQuery) ||
                     c.email.toLowerCase().includes(lowerQuery))
                );
            }
            this.renderContacts();
        },

        renderContacts: function() {
            const container = document.querySelector('.contacts-list');
            if (!container) return;

            if (this.filteredContacts.length === 0) {
                container.innerHTML = '<p class="no-contacts">No contacts found for this filter.</p>';
                return;
            }

            container.innerHTML = this.filteredContacts.map(contact => this.createContactCard(contact)).join('');
        },

        createContactCard: function(contact) {
            return `
                <div class="contact-card" data-id="${contact.id}">
                    <div class="contact-header">
                        <h3 class="contact-name">${contact.name}</h3>
                        <span class="contact-category">${contact.category}</span>
                    </div>
                    <p class="contact-company">${contact.company}</p>
                    <p class="contact-email">${contact.email}</p>
                    <div class="contact-phones">
                        ${contact.phones.map(p => `<span class="phone-tag">${p}</span>`).join('')}
                    </div>
                    <div class="contact-actions">
                        <button class="btn btn-primary btn-sm" onclick="Contacts.viewContact(${contact.id})">View</button>
                        <button class="btn btn-outline btn-sm" onclick="Contacts.addFavorite(${contact.id})">♥</button>
                    </div>
                </div>
            `;
        },

        viewContact: function(id) {
            const contact = this.contacts.find(c => c.id === id);
            if (contact) {
                const details = `
                    <h2>${contact.name}</h2>
                    <p><strong>Company:</strong> ${contact.company}</p>
                    <p><strong>Role:</strong> ${contact.role}</p>
                    <p><strong>Email:</strong> ${contact.email}</p>
                    <p><strong>Phone:</strong> ${contact.phones.join(', ')}</p>
                    <p><strong>Notes:</strong> ${contact.notes || 'N/A'}</p>
                `;
                this.showModal('Contact Details', details);
            }
        },

        addFavorite: function(id) {
            const contact = this.contacts.find(c => c.id === id);
            if (contact) {
                let favorites = JSON.parse(localStorage.getItem('favoriteContacts') || '[]');
                if (!favorites.includes(id)) {
                    favorites.push(id);
                    localStorage.setItem('favoriteContacts', JSON.stringify(favorites));
                    alert(`${contact.name} added to favorites`);
                }
            }
        },

        getFavorites: function() {
            const favorites = JSON.parse(localStorage.getItem('favoriteContacts') || '[]');
            return this.contacts.filter(c => favorites.includes(c.id));
        },

        showAddContactForm: function() {
            const form = document.getElementById('add-contact-form');
            if (form) {
                form.classList.add('active');
            }
        },

        hideAddContactForm: function() {
            const form = document.getElementById('add-contact-form');
            if (form) {
                form.classList.remove('active');
            }
        },

        setupScan: function() {
            const scanBtn = document.getElementById('scan-contact');
            if (scanBtn) {
                scanBtn.addEventListener('click', () => this.scanContact());
            }
        },

        scanContact: async function() {
            if ('BarcodeDetector' in window) {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({
                        video: { facingMode: 'environment' }
                    });
                    const videoElement = document.createElement('video');
                    videoElement.srcObject = stream;
                    videoElement.play();

                    const barcodeDetector = new BarcodeDetector({
                        formats: ['qr_code', 'code_128', 'ean_13']
                    });

                    const scanResult = await barcodeDetector.detect(videoElement);
                    if (scanResult && scanResult.length > 0) {
                        this.processScannedData(scanResult[0].rawValue);
                    }

                    stream.getTracks().forEach(track => track.stop());
                } catch (error) {
                    console.error('Scan error:', error);
                    alert('Unable to access camera. Please grant permission.');
                }
            } else {
                alert('Barcode scanning not supported on this device.');
            }
        },

        processScannedData: function(data) {
            try {
                const parsed = JSON.parse(data);
                this.addContact(parsed);
            } catch (error) {
                const contact = {
                    name: data,
                    company: 'Scanned',
                    category: 'networking',
                    email: '',
                    phones: [],
                    notes: `Scanned: ${data}`
                };
                this.addContact(contact);
            }
        },

        addContact: function(contactData) {
            this.contacts.unshift(contactData);
            this.filteredContacts = [...this.contacts];
            this.renderContacts();
            alert(`Contact "${contactData.name}" added successfully!`);
            this.hideAddContactForm();
        },

        showModal: function(title, content) {
            const modal = document.getElementById('contact-modal');
            if (modal) {
                document.querySelector('.modal-content h2').textContent = title;
                document.querySelector('.modal-content .modal-body').innerHTML = content;
                modal.classList.add('active');
            }
        },

        closeModal: function() {
            const modal = document.getElementById('contact-modal');
            if (modal) {
                modal.classList.remove('active');
            }
        },

        showErrorMessage: function(message) {
            const container = document.querySelector('.contacts-list');
            if (container) {
                container.innerHTML = `<p class="error-message">${message}</p>`;
            }
        }
    };

    window.Contacts = Contacts;
})();
