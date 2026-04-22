const http = require('http');
const fs = require('fs');
const path = require('path');

const PORT = 8000;
const DIST_DIR = path.join(__dirname, '..', 'dist');

const mimeTypes = {
    '.html': 'text/html',
    '.js': 'application/javascript',
    '.css': 'text/css',
    '.json': 'application/json',
    '.svg': 'image/svg+xml',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.gif': 'image/gif',
    '.ico': 'image/x-icon'
};

const server = http.createServer((req, res) => {
    console.log(`${req.method} ${req.url}`);

    if (req.method === 'OPTIONS') {
        res.writeHead(200, {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type'
        });
        res.end();
        return;
    }

    let filePath = path.join(DIST_DIR, req.url === '/' ? 'index.html' : req.url);
    const extname = path.extname(filePath).toLowerCase();
    const contentType = mimeTypes[extname] || 'application/octet-stream';

    fs.readFile(filePath, (err, content) => {
        if (err) {
            if (err.code === 'ENOENT') {
                res.writeHead(404);
                res.end('404 Not Found');
            } else {
                res.writeHead(500);
                res.end('500 Internal Server Error');
            }
            return;
        }

        res.writeHead(200, {
            'Content-Type': contentType,
            'Access-Control-Allow-Origin': '*'
        });
        res.end(content);
    });
});

const apiRoutes = {
    '/api/health': {
        GET: (req, res) => {
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({ status: 'ok', timestamp: new Date().toISOString() }));
        }
    },
    '/api/schedule': {
        GET: (req, res) => {
            const schedule = [
                { id: 1, day: 1, startTime: '09:00', endTime: '10:00', title: 'Opening Keynote', speaker: 'Dr. Sarah Chen', track: 'Main Hall', location: 'Hall A', description: 'Welcome to the AI World Fair' },
                { id: 2, day: 1, startTime: '10:30', endTime: '11:30', title: 'AI in Healthcare', speaker: 'Dr. James Wilson', track: 'Track 1', location: 'Room 101', description: 'Transforming patient care through artificial intelligence' },
                { id: 3, day: 1, startTime: '11:00', endTime: '12:00', title: 'Robotics Demo', speaker: 'TechCorp Team', track: 'Track 2', location: 'Demo Zone', description: 'Live demonstration of latest robotics technologies' },
                { id: 4, day: 2, startTime: '09:00', endTime: '10:30', title: 'Future of LLMs', speaker: 'Dr. Maria Garcia', track: 'Track 1', location: 'Room 101', description: 'Exploring the next generation of large language models' }
            ];
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(schedule));
        }
    },
    '/api/expo': {
        GET: (req, res) => {
            const booths = [
                { id: 1, number: 'B01', category: 'Healthcare', companyName: 'MediAI', description: 'AI-powered diagnostic tools', website: 'https://medai.ai', contactEmail: 'info@medai.ai', features: ['Demo', 'Networking', 'Job Openings'] },
                { id: 2, number: 'B02', category: 'Education', companyName: 'Learnbot', description: 'Intelligent tutoring systems', website: 'https://learnbot.io', contactEmail: 'contact@learnbot.io', features: ['Demo', 'Resources'] },
                { id: 3, number: 'B03', category: 'Finance', companyName: 'FinTech AI', description: 'AI-driven financial analysis', website: 'https:// fintech.ai', contactEmail: 'help@fintech.ai', features: ['Demo', 'Consultation', 'Job Openings'] }
            ];
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(booths));
        }
    },
    '/api/badge': {
        GET: (req, res) => {
            const badge = {
                id: 'badge-12345',
                name: 'John Doe',
                company: 'TechCorp Inc.',
                role: 'AI Engineer',
                email: 'john.doe@techcorp.com',
                badgeType: 'Regular',
                scannedCount: 0
            };
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(badge));
        }
    },
    '/api/contacts': {
        GET: (req, res) => {
            const contacts = [
                { id: 1, name: 'Alice Johnson', company: 'TechCorp Inc.', category: 'Technology', email: 'alice@techcorp.com', phones: ['+1-555-1234', '+1-555-5678'], role: 'Senior Engineer', notes: 'Interested in AI partnerships' },
                { id: 2, name: 'Bob Smith', company: 'HealthAI', category: 'Healthcare', email: 'bob@healthai.com', phones: ['+1-555-9876'], role: 'Director', notes: 'Looking for new vendors' }
            ];
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify(contacts));
        }
    }
};

server.on('request', (req, res) => {
    console.log(`${req.method} ${req.url}`);

    if (req.url.startsWith('/api/')) {
        const route = req.url.split('?')[0];
        const apiRoute = apiRoutes[route];
        
        if (apiRoute && apiRoute[req.method]) {
            return apiRoute[req.method](req, res);
        }
    }

    let filePath = path.join(DIST_DIR, req.url === '/' ? 'index.html' : req.url);
    const extname = path.extname(filePath).toLowerCase();
    const contentType = mimeTypes[extname] || 'application/octet-stream';

    fs.readFile(filePath, (err, content) => {
        if (err) {
            if (err.code === 'ENOENT') {
                res.writeHead(404);
                res.end('404 Not Found');
            } else {
                res.writeHead(500);
                res.end('500 Internal Server Error');
            }
            return;
        }

        res.writeHead(200, {
            'Content-Type': contentType,
            'Access-Control-Allow-Origin': '*'
        });
        res.end(content);
    });
});

server.listen(PORT, () => {
    console.log(`Server running on port ${PORT}`);
    console.log(`API endpoints available at http://localhost:${PORT}/api/`);
});
