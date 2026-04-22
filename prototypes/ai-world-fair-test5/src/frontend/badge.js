function renderBadge(container, data) {
    const badgeData = data || { name: "AI Engineer", github: "", hacking_on: "Exploring the conference" };
    
    container.innerHTML = `
        <h2>Your Badge</h2>
        <div id="badge-card"></div>
        <div class="badge-controls" style="margin-top:1rem">
            <button id="edit-badge">Edit Badge</button>
        </div>
    `;
    
    const card = container.querySelector('#badge-card');
    card.innerHTML = `
        <div class="badge-card">
            <h2 style="color:var(--accent)">${badgeData.name}</h2>
            <p style="margin:0 0 2rem 0">${badgeData.hacking_on}</p>
            <div class="badge-qr" id="qr-container"></div>
            <p style="color:var(--fg-dim);font-size:0.9rem">github.com/${badgeData.github || 'guest'}</p>
        </div>
    `;
    
    const qrOptions = {
        size: 180,
        colorDark: "#0d1117",
        colorLight: "#73daca",
        correctLevel: 0
    };
    new QRCode(container.querySelector('#qr-container'), Object.assign(qrOptions, { text: JSON.stringify(badgeData) }));
    
    container.querySelector('#edit-badge').addEventListener('click', () => {
        const name = prompt('Name:', badgeData.name || '');
        const github = prompt('GitHub:', badgeData.github || '');
        const hacking = prompt('Hacking on:', badgeData.hacking_on || '');
        
        if (name) {
            return { name, github, hacking_on: hacking };
        }
        return null;
    });
    
    return card;
}
