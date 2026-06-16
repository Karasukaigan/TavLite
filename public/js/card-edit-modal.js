let currentEditingCard = null;

function handleConceptArtFile(file, area) {
    if (/webp|gif/i.test(file.type) || /\.(webp|gif)$/i.test(file.name)) {
        if (file.size > 5 * 1024 * 1024) {
            toast.show('WebP/GIF images must be 5MB or smaller', 'error');
            return;
        }
    }
    const preview = area.querySelector('.concept-art-preview');
    const upload = area.querySelector('.concept-art-upload');
    const img = preview.querySelector('.concept-art-image');
    const reader = new FileReader();
    reader.onload = (ev) => {
        img.src = ev.target.result;
        preview.style.display = '';
        upload.style.display = 'none';
    };
    reader.readAsDataURL(file);
}

async function openEditModal(name) {
    let card = cardDataMap.get(name);
    if (!card || !card.system_prompt) {
        try {
            const response = await fetch('/api/cards/' + encodeURIComponent(name) + '?t=' + Date.now());
            if (!response.ok) return;
            const data = await response.json();
            card = data && data[name];
            if (!card) return;
            cardDataMap.set(name, card);
        } catch (e) {
            console.error('Failed to load card:', e);
            return;
        }
    }
    currentEditingCard = name;
    document.getElementById('modal-card-title').textContent = name;
    const promptEl = document.getElementById('modal-card-prompt');
    const contextEl = document.getElementById('modal-card-context');
    promptEl.value = card.system_prompt || '';
    contextEl.value = card.context?.[0]?.content || '';
    const htmlEl = document.getElementById('modal-card-html');
    if (htmlEl) htmlEl.value = card.html || '';
    countTokens(promptEl.value).then(c => { document.getElementById('prompt-token-count').textContent = `${c} tokens`; });
    countTokens(contextEl.value).then(c => { document.getElementById('context-token-count').textContent = `${c} tokens`; });
    const messagesList = document.getElementById('messages-list');
    messagesList.innerHTML = '';
    const messages = card.messages || [];
    messages.forEach((msg, i) => {
        addMessageRow(msg);
    });
    const modal = document.getElementById('card-edit-modal');
    const preview = modal.querySelector('.concept-art-preview');
    const upload = modal.querySelector('.concept-art-upload');
    const img = modal.querySelector('.concept-art-image');
    if (card.concept_art) {
        img.src = card.concept_art;
        preview.style.display = '';
        upload.style.display = 'none';
    } else {
        img.src = '';
        preview.style.display = 'none';
        upload.style.display = '';
    }
    modal.style.display = 'flex';
}

function renumberMessages() {
    const items = document.querySelectorAll('#messages-list .message-item');
    items.forEach((item, idx) => {
        const n = idx + 2;
        const label = item.querySelector('.message-label');
        const ta = item.querySelector('.message-input');
        label.textContent = `#${n}`;
        label.htmlFor = `message-${n}`;
        ta.id = `message-${n}`;
    });
}

function addMessageRow(value) {
    const modalBody = document.getElementById('modal-body');
    const messagesList = document.getElementById('messages-list');
    messagesList.style.display = 'flex';
    const row = document.createElement('div');
    row.className = 'message-item';

    const header = document.createElement('div');
    header.className = 'message-item-header';

    const label = document.createElement('label');
    label.className = 'message-label';

    const tokenCount = document.createElement('span');
    tokenCount.className = 'token-count';
    tokenCount.textContent = '0 tokens';

    const textarea = document.createElement('textarea');
    textarea.className = 'message-input';
    textarea.value = value || '';
    textarea.rows = 2;

    const removeBtn = document.createElement('button');
    removeBtn.type = 'button';
    removeBtn.className = 'message-remove';
    removeBtn.innerHTML = '<svg><use xlink:href="/img/icons.svg?v=200#icon-close"></use></svg>';
    removeBtn.addEventListener('click', () => {
        row.remove();
        if (messagesList.children.length < 1) messagesList.style.display = 'none';
        renumberMessages();
    });

    const updateTokens = debounce(async function () {
        const count = await countTokens(textarea.value);
        tokenCount.textContent = `${count} tokens`;
    }, 300);
    textarea.addEventListener('input', updateTokens);

    header.appendChild(label);
    header.appendChild(tokenCount);
    header.appendChild(removeBtn);
    row.appendChild(header);
    row.appendChild(textarea);
    messagesList.appendChild(row);
    renumberMessages();

    if (value) {
        countTokens(value).then(count => {
            tokenCount.textContent = `${count} tokens`;
        });
    }

    modalBody.scrollTop = modalBody.scrollHeight;
}

function closeEditModal() {
    document.getElementById('card-edit-modal').style.display = 'none';
    currentEditingCard = null;
}

document.addEventListener('click', (e) => {
    if (e.target.closest('.concept-art-upload')) {
        const uploadArea = e.target.closest('.concept-art-upload');
        const input = uploadArea.querySelector('.concept-art-input');
        if (input) input.click();
    }

    if (e.target.closest('.concept-art-remove')) {
        e.stopPropagation();
        const removeBtn = e.target.closest('.concept-art-remove');
        const area = removeBtn.closest('.concept-art-area');
        const preview = area.querySelector('.concept-art-preview');
        const upload = area.querySelector('.concept-art-upload');
        const img = preview.querySelector('.concept-art-image');
        if (img) img.src = '';
        preview.style.display = 'none';
        upload.style.display = '';
    }
});

document.addEventListener('change', (e) => {
    const input = e.target.closest('.concept-art-input');
    if (!input || !input.files || !input.files[0]) return;
    handleConceptArtFile(input.files[0], input.closest('.concept-art-area'));
    input.value = '';
});

document.addEventListener('dragenter', (e) => {
    const uploadArea = e.target.closest('.concept-art-upload');
    if (uploadArea) {
        e.preventDefault();
        uploadArea.classList.add('drag-over');
    }
});
document.addEventListener('dragover', (e) => {
    if (e.target.closest('.concept-art-upload')) {
        e.preventDefault();
    }
});
document.addEventListener('dragleave', (e) => {
    const uploadArea = e.target.closest('.concept-art-upload');
    if (uploadArea && !uploadArea.contains(e.relatedTarget)) {
        uploadArea.classList.remove('drag-over');
    }
});
document.addEventListener('drop', (e) => {
    const uploadArea = e.target.closest('.concept-art-upload');
    if (uploadArea) {
        e.preventDefault();
        uploadArea.classList.remove('drag-over');
        const files = e.dataTransfer.files;
        if (files.length) {
            handleConceptArtFile(files[0], uploadArea.closest('.concept-art-area'));
        }
    }
});

document.getElementById('modal-close').addEventListener('click', closeEditModal);

document.getElementById('card-edit-modal').addEventListener('click', (e) => {
});

document.getElementById('add-message-btn').addEventListener('click', () => {
    addMessageRow('');
});

const debouncedPromptTokens = debounce(async function () {
    const count = await countTokens(this.value);
    document.getElementById('prompt-token-count').textContent = `${count} tokens`;
}, 300);
document.getElementById('modal-card-prompt').addEventListener('input', debouncedPromptTokens);

const debouncedContextTokens = debounce(async function () {
    const count = await countTokens(this.value);
    document.getElementById('context-token-count').textContent = `${count} tokens`;
}, 300);
document.getElementById('modal-card-context').addEventListener('input', debouncedContextTokens);

document.getElementById('modal-card-save').addEventListener('click', async () => {
    const saveBtn = document.getElementById('modal-card-save');
    if (saveBtn.disabled) return;
    saveBtn.disabled = true;
    const name = currentEditingCard;
    if (!name) { saveBtn.disabled = false; return; }
    const prompt = document.getElementById('modal-card-prompt').value;
    const content = document.getElementById('modal-card-context').value;
    const img = document.querySelector('#card-edit-modal .concept-art-image');
    let conceptArt = '';
    if (img) {
        const src = img.getAttribute('src');
        if (src && (src.startsWith('data:') || src.startsWith('/img/'))) {
            conceptArt = src;
        }
    }
    const messageInputs = document.querySelectorAll('#messages-list .message-input');
    const messages = [];
    messageInputs.forEach(inp => {
        const v = inp.value.trim();
        if (v) messages.push(v);
    });
    const htmlContent = document.getElementById('modal-card-html')?.value || '';
    try {
        await fetchWithToast(`/api/cards/${encodeURIComponent(name)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt, content, concept_art: conceptArt, messages, html: htmlContent })
        }, 'Card saved successfully', 'Failed to save card');
        let updatedCard = { system_prompt: prompt };
        if (content) updatedCard.context = [{ role: "assistant", content }];
        if (messages.length) updatedCard.messages = messages;
        if (conceptArt) updatedCard.concept_art = conceptArt;
        if (htmlContent) updatedCard.html = htmlContent;
        cardDataMap.set(name, updatedCard);
        closeEditModal();
    } catch (e) {} finally {
        saveBtn.disabled = false;
    }
});

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && document.getElementById('card-edit-modal').style.display === 'flex') {
        closeEditModal();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === 's' && document.getElementById('card-edit-modal').style.display === 'flex') {
        e.preventDefault();
        document.getElementById('modal-card-save').click();
    }
});
