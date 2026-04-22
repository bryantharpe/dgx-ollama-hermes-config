(function() {
    'use strict';

    const Palette = {
        colors: {
            primary: '#6366f1',
            secondary: '#8b5cf6',
            accent: '#ec4899',
            background: '#0f172a',
            surface: '#1e293b',
            text: '#f8fafc',
            textSecondary: '#94a3b8',
            success: '#10b981',
            warning: '#f59e0b',
            error: '#ef4444',
            info: '#3b82f6'
        },

        setTheme: function(theme) {
            const root = document.documentElement;
            const colors = this.colors;

            if (theme === 'dark') {
                root.style.setProperty('--color-primary', colors.primary);
                root.style.setProperty('--color-secondary', colors.secondary);
                root.style.setProperty('--color-accent', colors.accent);
                root.style.setProperty('--color-background', colors.background);
                root.style.setProperty('--color-surface', colors.surface);
                root.style.setProperty('--color-text', colors.text);
                root.style.setProperty('--color-text-secondary', colors.textSecondary);
            } else if (theme === 'light') {
                root.style.setProperty('--color-primary', colors.primary);
                root.style.setProperty('--color-secondary', colors.secondary);
                root.style.setProperty('--color-accent', colors.accent);
                root.style.setProperty('--color-background', '#ffffff');
                root.style.setProperty('--color-surface', '#f1f5f9');
                root.style.setProperty('--color-text', '#0f172a');
                root.style.setProperty('--color-text-secondary', '#64748b');
            }
        },

        getColor: function(name) {
            return this.colors[name] || '#000000';
        },

        applyColorTheme: function() {
            const theme = localStorage.getItem('theme') || 'dark';
            this.setTheme(theme);
        },

        toggleTheme: function() {
            const currentTheme = localStorage.getItem('theme') || 'dark';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            localStorage.setItem('theme', newTheme);
            this.setTheme(newTheme);
        }
    };

    window.Palette = Palette;
})();
