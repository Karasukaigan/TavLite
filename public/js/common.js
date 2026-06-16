const fetchJson = async url => { try { const r = await fetch(url); if (!r.ok) return {}; const d = await r.json(); return d && typeof d == 'object' && !Array.isArray(d) ? d : {} } catch { return {} } };

const authCheck = async (redirectPath) => {
    try {
        const res = await fetch('/api/auth/check');
        const data = await res.json();
        if (!data.authenticated && data.password_enabled) {
            window.location.href = '/login?redirect=' + encodeURIComponent(redirectPath);
            return false;
        }
    } catch (e) { }
    return true;
};

function debounce(fn, delay) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

const escapeHtml = (t) => ((div) => { div.textContent = t; return div.innerHTML; })(document.createElement('div'));

async function countTokens(text) {
    if (!text) return 0;
    try {
        const res = await fetch('/api/llm/count-tokens', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
        });
        const data = await res.json();
        return data.count || 0;
    } catch {
        return 0;
    }
}

const urlToBase64 = async (url) => {
    const response = await fetch(url);
    const blob = await response.blob();
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
};

function downloadFile(content, filename, mimeType = 'application/json') {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

const sortCardsByUpdatedAt = (cardsObj) => {
    return Object.entries(cardsObj).sort((a, b) => (b[1]?.updated_at || 0) - (a[1]?.updated_at || 0));
};

const readSSE = async (response, onData, onDone) => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    while (true) {
        const { done, value } = await reader.read();
        if (done) { if (onDone) onDone(); break; }
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                onData(line.slice(6));
            }
        }
    }
};
