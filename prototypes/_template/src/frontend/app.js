document.addEventListener('DOMContentLoaded', async () => {
    const status = document.getElementById('status');
    try {
        const res = await fetch('/api/health');
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();
        status.textContent = `health: ${data.status}`;
        status.className = 'ok';
    } catch (err) {
        status.textContent = `health check failed: ${err.message}`;
        status.className = 'err';
    }
});
