document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.createElement('div');
    overlay.className = 'command-palette-overlay';
    overlay.innerHTML = `
        <input type="text" class="command-palette-input" id="cp-input" placeholder="Search talks, speakers... (Cmd+K)">
        <div class="command-palette-results" id="cp-results"></div>
        <div style="margin-top:1rem;color:var(--fg-dim);font-size:0.85rem">
            <span id="cursor">&nbsp;</span>
        </div>
    `;
    document.body.appendChild(overlay);
    
    const input = overlay.querySelector('#cp-input');
    const results = overlay.querySelector('#cp-results');
    
    let timer = null;
    let activeIndex = -1;
    
    function toggleOverlay(show) {
        if (show) {
            overlay.classList.add('active');
            input.focus();
            activeIndex = -1;
            results.innerHTML = '';
            input.value = '';
            fetchResults('');
        } else {
            overlay.classList.remove('active');
            results.innerHTML = '';
        }
    }
    
    function fetchResults(query) {
        if (!query) {
            results.innerHTML = '';
            return;
        }
        
        results.innerHTML = '<div class="loading-state"><span class="spinner"></span> Searching...</div>';
        
        Promise.all([
            fetch(`/api/talks?q=${encodeURIComponent(query)}`).then(r => r.json()),
            fetch(`/api/speakers?q=${encodeURIComponent(query)}`).then(r => r.json())
        ]).then(([talks, speakers]) => {
            let html = '';
            
            if (talks.length > 0) {
                html += '<h3 style="margin:1rem 0 0.5rem 0;color:var(--accent)">Talks</h3>';
                html += talks.slice(0, 10).map((t, i) => `
                    <div class="command-palette-result" data-type="talk" data-id="${t.id}" ${i === 0 ? 'style="border-left:3px solid var(--accent)"' : ''}>
                        <div style="font-weight:600">${t.title}</div>
                        <div class="command-palette-meta">${t.speaker_name} • ${t.start_time.slice(5, 16)} • ${t.room}</div>
                    </div>
                `).join('');
            }
            
            if (speakers.length > 0) {
                html += '<h3 style="margin:1rem 0 0.5rem 0;color:var(--accent)">Speakers</h3>';
                html += speakers.slice(0, 5).map((s, i) => `
                    <div class="command-palette-result" data-type="speaker" data-id="${s.id}" ${talks.length + i === 0 ? 'style="border-left:3px solid var(--accent)"' : ''}>
                        <div style="font-weight:600">${s.name}</div>
                        <div class="command-palette-meta">${s.company || ''}</div>
                    </div>
                `).join('');
            }
            
            if (!html) {
                html = '<div class="empty-state" style="text-align:center">No results found</div>';
            }
            
            results.innerHTML = html;
            activeIndex = -1;
        }).catch(() => {
            results.innerHTML = '<div class="empty-state" style="text-align:center">Search failed</div>';
        });
    }
    
    input.addEventListener('input', () => {
        clearTimeout(timer);
        timer = setTimeout(() => fetchResults(input.value), 200);
    });
    
    input.addEventListener('keydown', (e) => {
        const items = results.querySelectorAll('.command-palette-result');
        if (items.length === 0) return;
        
        if (e.key === 'ArrowDown') {
            e.preventDefault();
            activeIndex = (activeIndex + 1) % items.length;
            updateActive(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            activeIndex = activeIndex <= 0 ? items.length - 1 : activeIndex - 1;
            updateActive(items);
        } else if (e.key === 'Enter' && activeIndex >= 0) {
            e.preventDefault();
            const item = items[activeIndex];
            const type = item.dataset.type;
            const id = item.dataset.id;
            if (type === 'talk') {
                window.location.hash = 'schedule';
                setTimeout(() => {
                    const talk = document.querySelector('[data-type="talk"][data-id="' + id + '"]');
                    if (talk) talk.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }, 100);
                toggleOverlay(false);
            }
        } else if (e.key === 'Escape') {
            toggleOverlay(false);
        }
    });
    
    function updateActive(items) {
        items.forEach((item, i) => {
            if (i === activeIndex) {
                item.style.borderLeft = '3px solid var(--accent)';
                item.style.background = '#1f2233';
            } else {
                item.style.borderLeft = '1px solid var(--border)';
                item.style.background = 'transparent';
            }
        });
    }
    
    document.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            toggleOverlay(!overlay.classList.contains('active'));
        }
    });
});
