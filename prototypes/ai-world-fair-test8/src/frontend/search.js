// Search utilities
window.search = {
    filterTalks(talks, filters) {
        return talks.filter(talk => {
            if (filters.q && !this.matchesSearch(talk, filters.q)) return false;
            if (filters.tag && !this.hasTag(talk, filters.tag)) return false;
            if (filters.speaker && talk.speaker_id !== filters.speaker) return false;
            if (filters.track && talk.track !== filters.track) return false;
            if (filters.date && new Date(talk.start_time).toDateString() !== new Date(filters.date).toDateString()) return false;
            return true;
        });
    },

    matchesSearch(item, term) {
        const searchStr = [item.title, item.abstract, item.tags, item.room, item.track].join(' ').toLowerCase();
        return searchStr.includes(term.toLowerCase());
    },

    hasTag(talk, tag) {
        const tags = JSON.parse(talk.tags || '[]');
        return tags.some(t => t.toLowerCase().includes(tag.toLowerCase()));
    },

    groupByDay(talks) {
        const days = {};
        talks.forEach(talk => {
            const date = talk.start_time.split('T')[0];
            if (!days[date]) days[date] = [];
            days[date].push(talk);
        });
        return days;
    },

    groupByTrack(talks) {
        const tracks = {};
        talks.forEach(talk => {
            const track = talk.track || 'Other';
            if (!tracks[track]) tracks[track] = [];
            tracks[track].push(talk);
        });
        return tracks;
    },

    getTags(talks) {
        const allTags = new Set();
        talks.forEach(talk => {
            JSON.parse(talk.tags || '[]').forEach(tag => allTags.add(tag));
        });
        return Array.from(allTags).sort();
    },

    detectConflicts(talks) {
        // Check for overlapping talks
        const conflicts = new Set();
        for (let i = 0; i < talks.length; i++) {
            for (let j = i + 1; j < talks.length; j++) {
                const t1 = talks[i];
                const t2 = talks[j];
                if (this.overlaps(t1, t2)) {
                    conflicts.add(t1.talk_id);
                    conflicts.add(t2.talk_id);
                }
            }
        }
        return conflicts;
    },

    overlaps(t1, t2) {
        const s1 = new Date(t1.start_time);
        const e1 = new Date(t1.end_time);
        const s2 = new Date(t2.start_time);
        const e2 = new Date(t2.end_time);
        return s1 < e2 && s2 < e1;
    },
};
