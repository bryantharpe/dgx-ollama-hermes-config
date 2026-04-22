(function() {
    'use strict';

    const app = {
        init: function() {
            this.bindEvents();
            this.loadUI();
        },

        bindEvents: function() {
            document.addEventListener('DOMContentLoaded', () => this.onDOMContentLoaded());
            document.addEventListener('resume', () => this.onResume(), false);
        },

        onDOMContentLoaded: function() {
            this.setupNavigation();
            this.setupTabs();
            this.checkConnection();
        },

        onResume: function() {
            this.checkConnection();
        },

        setupNavigation: function() {
            const navLinks = document.querySelectorAll('.nav-link');
            navLinks.forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const targetId = link.getAttribute('href').substring(1);
                    this.showView(targetId);
                });
            });
        },

        setupTabs: function() {
            const tabLinks = document.querySelectorAll('.tab-link');
            tabLinks.forEach(link => {
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    const tabId = link.getAttribute('data-tab');
                    this.switchTab(tabId);
                });
            });
        },

        showView: function(viewId) {
            document.querySelectorAll('.view').forEach(view => {
                view.classList.remove('active');
            });
            const activeView = document.getElementById(viewId);
            if (activeView) {
                activeView.classList.add('active');
            }
            this.updateActiveNav(viewId);
        },

        updateActiveNav: function(viewId) {
            document.querySelectorAll('.nav-link').forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('href').substring(1) === viewId) {
                    link.classList.add('active');
                }
            });
        },

        switchTab: function(tabId) {
            document.querySelectorAll('.tab-content').forEach(content => {
                content.classList.remove('active');
            });
            const activeTab = document.querySelector(`.tab-content[data-tab="${tabId}"]`);
            if (activeTab) {
                activeTab.classList.add('active');
            }
            document.querySelectorAll('.tab-link').forEach(link => {
                link.classList.remove('active');
                if (link.getAttribute('data-tab') === tabId) {
                    link.classList.add('active');
                }
            });
        },

        checkConnection: function() {
            if (navigator.onLine) {
                this.showStatus('Connected', 'success');
            } else {
                this.showStatus('Offline', 'error');
            }
        },

        showStatus: function(message, type) {
            const statusEl = document.getElementById('connection-status');
            if (statusEl) {
                statusEl.textContent = message;
                statusEl.className = `status-${type}`;
            }
        },

        loadUI: function() {
            console.log('AI World Fair Companion App v1.0.0');
            console.log('Loading UI components...');
        }
    };

    window.app = app;
})();
