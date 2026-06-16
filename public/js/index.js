document.addEventListener('DOMContentLoaded', async () => {
    if (!await authCheck('/')) return;
    await i18n.init(i18n.getBrowserLanguage());

    const headerEl = document.querySelector('.home-header h2');
    if (headerEl) {
        const tier = headerEl.textContent.trim();
        if (tier === 'Free') {
            new StickyNotice({
                message: 'Enjoying TavLite? Upgrade to <a href="https://beyondblackwall.com/product/2">TavLite Pro</a> for a better experience, access to new features, and to support our development. Your support means a lot to us!',
                buttonText: 'I understand',
                key: 'home-free-notice',
                frequency: 'n_days',
                days: 1
            }).show();
        } else if (tier === 'Pro') {
            new StickyNotice({
                message: 'TavLite Pro is intended for use by the original purchaser only. Please do not redistribute or share it with others. Thank you for supporting us!',
                buttonText: 'I agree',
                key: 'home-pro-notice',
                frequency: 'once'
            }).show();
        }
    }
});

const PAGE_SIZE = 20;
let allCards = {};
let filteredNames = [];
let currentPage = 1;
let loadImageTimer = null;

const renderPagination = (totalPages) => {
    const pagination = document.getElementById('pagination');
    pagination.innerHTML = '';

    if (totalPages <= 1) return;

    const goToPage = (page) => {
        if (page < 1 || page > totalPages) return;
        currentPage = page;
        renderCards();
    };

    const firstBtn = document.createElement('button');
    firstBtn.className = 'page-btn';
    firstBtn.innerHTML = '<svg><use xlink:href="/img/icons.svg?v=200#icon-left-double"></use></svg>';
    firstBtn.disabled = currentPage === 1;
    firstBtn.addEventListener('click', () => goToPage(1));
    pagination.appendChild(firstBtn);

    const prevBtn = document.createElement('button');
    prevBtn.className = 'page-btn';
    prevBtn.innerHTML = '<svg><use xlink:href="/img/icons.svg?v=200#icon-left"></use></svg>';
    prevBtn.disabled = currentPage === 1;
    prevBtn.addEventListener('click', () => goToPage(currentPage - 1));
    pagination.appendChild(prevBtn);

    let startPage, endPage;
    if (totalPages <= 5) {
        startPage = 1;
        endPage = totalPages;
    } else {
        const half = Math.floor(5 / 2);
        startPage = currentPage - half;
        endPage = currentPage + half;
        if (startPage < 1) { startPage = 1; endPage = 5; }
        if (endPage > totalPages) { endPage = totalPages; startPage = totalPages - 4; }
    }

    for (let i = startPage; i <= endPage; i++) {
        const pageBtn = document.createElement('button');
        pageBtn.className = 'page-btn';
        pageBtn.textContent = i;
        if (i === currentPage) pageBtn.classList.add('active');
        pageBtn.addEventListener('click', () => goToPage(i));
        pagination.appendChild(pageBtn);
    }

    const nextBtn = document.createElement('button');
    nextBtn.className = 'page-btn';
    nextBtn.innerHTML = '<svg><use xlink:href="/img/icons.svg?v=200#icon-right"></use></svg>';
    nextBtn.disabled = currentPage === totalPages;
    nextBtn.addEventListener('click', () => goToPage(currentPage + 1));
    pagination.appendChild(nextBtn);

    const lastBtn = document.createElement('button');
    lastBtn.className = 'page-btn';
    lastBtn.innerHTML = '<svg><use xlink:href="/img/icons.svg?v=200#icon-right-double"></use></svg>';
    lastBtn.disabled = currentPage === totalPages;
    lastBtn.addEventListener('click', () => goToPage(totalPages));
    pagination.appendChild(lastBtn);
};



const renderCards = () => {
    const grid = document.getElementById('card-grid');
    grid.innerHTML = '';
    if (loadImageTimer) clearTimeout(loadImageTimer);

    const start = (currentPage - 1) * PAGE_SIZE;
    const pageNames = filteredNames.slice(start, start + PAGE_SIZE);

    if (pageNames.length === 0) {
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'home-empty';
        const span = document.createElement('span');
        span.textContent = i18n.tr('No character cards found');
        emptyDiv.appendChild(span);
        grid.appendChild(emptyDiv);
        document.getElementById('pagination').innerHTML = '';
        return;
    }

    const fragment = document.createDocumentFragment();
    pageNames.forEach(name => {
        const cardEl = document.createElement('div');
        cardEl.className = 'home-card';
        cardEl.addEventListener('click', () => {
            window.open('/chat?card=' + encodeURIComponent(name), '_blank');
        });

        const art = allCards[name]?.concept_art;
        if (art && typeof art === 'string') {
            const img = document.createElement('img');
            img.className = 'home-card-image';
            img.dataset.src = art;
            img.loading = 'lazy';
            cardEl.appendChild(img);
        } else {
            const placeholder = document.createElement('div');
            placeholder.className = 'home-card-placeholder';
            cardEl.appendChild(placeholder);
        }

        const infoBtn = document.createElement('button');
        infoBtn.className = 'home-card-info-btn';
        infoBtn.innerHTML = '<svg><use xlink:href="/img/icons.svg?v=200#icon-info"></use></svg>';
        infoBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            openCardInfoModal(name);
        });
        cardEl.appendChild(infoBtn);

        const title = document.createElement('div');
        title.className = 'home-card-title';
        title.textContent = name;
        title.title = name;
        cardEl.appendChild(title);

        fragment.appendChild(cardEl);
    });
    grid.appendChild(fragment);

    loadImageTimer = setTimeout(() => {
        grid.querySelectorAll('.home-card-image').forEach(img => {
            if (img.dataset.src) { img.src = img.dataset.src; delete img.dataset.src; }
        });
        loadImageTimer = null;
    }, 300);

    const totalPages = Math.ceil(filteredNames.length / PAGE_SIZE);
    renderPagination(totalPages);
};

document.addEventListener('DOMContentLoaded', async () => {
    allCards = await fetchJson('/api/cards?with_art=true&t=' + Date.now());
    filteredNames = Object.entries(allCards)
        .sort((a, b) => (b[1]?.updated_at || 0) - (a[1]?.updated_at || 0))
        .map(([name]) => name);
    setTimeout(() => { renderCards(); }, 500);

    let searchTimer;
    document.getElementById('search-input').addEventListener('input', function () {
        clearTimeout(searchTimer);
        const query = this.value.trim();
        searchTimer = setTimeout(async () => {
            currentPage = 1;
            let url = '/api/cards?with_art=true&t=' + Date.now();
            if (query) url += '&q=' + encodeURIComponent(query);
            allCards = await fetchJson(url);
            filteredNames = Object.entries(allCards)
                .sort((a, b) => (b[1]?.updated_at || 0) - (a[1]?.updated_at || 0))
                .map(([name]) => name);
            renderCards();
        }, 300);
    });
});

document.getElementById('settings-button').addEventListener('click', () => {
    window.location.href = '/settings';
});

const openCardInfoModal = async (name) => {
    const modal = document.getElementById('card-info-modal');
    document.getElementById('info-modal-title').textContent = name;
    const body = document.getElementById('info-modal-body');
    body.innerHTML = `<p style="color:#888;">${i18n.tr("Loading")}...</p>`;
    modal.style.display = 'flex';

    try {
        const res = await fetch('/api/cards/' + encodeURIComponent(name) + '?t=' + Date.now());
        if (!res.ok) throw new Error('Failed to load card');
        const data = await res.json();
        const card = data && data[name];

        let html = '';
        if (card && card.tags && card.tags.length) {
            html += '<div class="tags-container" id="info-tags-container">';
            card.tags.forEach(tag => {
                html += '<span class="tag-item">' + tag.replace(/</g, '&lt;') + '</span>';
            });
            html += '</div>';
        }

        const prompt = card && card.system_prompt;
        if (prompt) {
            html += marked.parse(prompt);
        } else if (!html) {
            html = '<p style="color:#888; user-select: text;">(No system prompt)</p>';
        }
        body.innerHTML = html;
    } catch (e) {
        body.innerHTML = '<p style="color:#c00;">Error: ' + e.message + '</p>';
    }
};

const closeCardInfoModal = () => {
    document.getElementById('card-info-modal').style.display = 'none';
};

document.getElementById('info-modal-close').addEventListener('click', closeCardInfoModal);

document.getElementById('card-info-modal').addEventListener('click', (e) => {
    if (e.target === e.currentTarget) closeCardInfoModal();
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && document.getElementById('card-info-modal').style.display === 'flex') {
        closeCardInfoModal();
    }
});

document.getElementById('info-modal-start-chat').addEventListener('click', () => {
    const name = document.getElementById('info-modal-title').textContent;
    if (name) window.open('/chat?card=' + encodeURIComponent(name), '_blank');
});
