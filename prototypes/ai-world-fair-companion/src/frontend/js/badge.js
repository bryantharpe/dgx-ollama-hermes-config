(function() {
    'use strict';

    const Badge = {
        apiBase: '/api/badge',
        badgeData: null,
        qrValue: '',

        init: function() {
            this.loadBadge();
            this.setupShare();
        },

        loadBadge: async function() {
            try {
                const response = await fetch(this.apiBase);
                if (!response.ok) throw new Error('Failed to load badge');
                this.badgeData = await response.json();
                this.renderBadge();
                this.generateQR();
            } catch (error) {
                console.error('Error loading badge:', error);
                this.showErrorMessage('Unable to load badge. Please try again.');
            }
        },

        renderBadge: function() {
            if (!this.badgeData) return;

            const nameEl = document.getElementById('badge-name');
            const companyEl = document.getElementById('badge-company');
            const roleEl = document.getElementById('badge-role');
            const emailEl = document.getElementById('badge-email');

            if (nameEl) nameEl.textContent = this.badgeData.name;
            if (companyEl) companyEl.textContent = this.badgeData.company;
            if (roleEl) roleEl.textContent = this.badgeData.role;
            if (emailEl) emailEl.textContent = this.badgeData.email;

            document.getElementById('badge-id').textContent = this.badgeData.id;
        },

        generateQR: function() {
            const qrContainer = document.getElementById('qr-code');
            if (!qrContainer) return;

            this.qrValue = JSON.stringify({
                id: this.badgeData.id,
                name: this.badgeData.name,
                email: this.badgeData.email,
                company: this.badgeData.company
            });

            this.renderQRCode(this.qrValue, qrContainer);
        },

        renderQRCode: function(text, container) {
            container.innerHTML = '';
            const canvas = document.createElement('canvas');
            const qrCode = new QRCode(canvas, {
                text: text,
                width: 200,
                height: 200,
                colorDark: '#000000',
                colorLight: '#ffffff',
                correctLevel: QRCode.CorrectLevel.M
            });
            container.appendChild(canvas);
        },

        setupShare: function() {
            const shareBtn = document.getElementById('share-badge');
            if (shareBtn) {
                shareBtn.addEventListener('click', () => this.shareBadge());
            }
        },

        shareBadge: async function() {
            const shareData = {
                title: 'AI World Fair - My Badge',
                text: `Hi! I'm ${this.badgeData.name} from ${this.badgeData.company}. Let's connect!`,
                url: window.location.href
            };

            if (navigator.share) {
                try {
                    await navigator.share(shareData);
                } catch (error) {
                    console.error('Error sharing:', error);
                }
            } else {
                this.copyToClipboard(JSON.stringify({
                    id: this.badgeData.id,
                    name: this.badgeData.name,
                    email: this.badgeData.email
                }));
                alert('Badge info copied to clipboard!');
            }
        },

        copyToClipboard: function(text) {
            navigator.clipboard.writeText(text).catch(err => {
                console.error('Failed to copy:', err);
            });
        },

        showErrorMessage: function(message) {
            const container = document.querySelector('.badge-container');
            if (container) {
                container.innerHTML = `<p class="error-message">${message}</p>`;
            }
        }
    };

    window.Badge = Badge;
})();
