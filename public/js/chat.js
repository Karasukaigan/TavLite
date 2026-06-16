const updateLLMStatus = async () => {
    const statusDiv = document.getElementById('llm-status');
    if (!statusDiv) return;
    try {
        const res = await fetch('/api/llm/test?t=' + Date.now(), { method: 'GET' });
        const data = await res.json();
        if (data.success) {
            statusDiv.textContent = i18n.tr('Connected');
            statusDiv.className = 'llm-status connected';
        } else {
            statusDiv.textContent = i18n.tr('Disconnected');
            statusDiv.className = 'llm-status disconnected';
        }
    } catch (error) {
        console.error(error);
        statusDiv.textContent = i18n.tr('Disconnected');
        statusDiv.className = 'llm-status disconnected';
    }
};

document.addEventListener('DOMContentLoaded', async () => {
    if (!await authCheck('/chat' + window.location.search)) return;
    const savedTheme = localStorage.getItem('chat-theme');
    if (savedTheme) document.documentElement.dataset.theme = savedTheme;
    await i18n.init(i18n.getBrowserLanguage());

    setTimeout(() => {
        updateLLMStatus();
    }, 2000);
    setInterval(updateLLMStatus, 600000);
});

var systemRoles = {};
var controlModes = {};
var cards = {};
var currentCardName = null;
var t2iPrompts = {};
var userInfo = { username: '', profile: '' };
var osrMode = 'disabled';
var comfyuiType = '';

var systemPrompt = "";
var chatContext = [];
var selectedMessageIdx = 0;
var cardMessages = [];
var initialMessageContent = '';

var chatStarted = false;
let autoScroll = true;

const isNearBottom = () => {
    return chatBubbles.scrollHeight - chatBubbles.scrollTop - chatBubbles.clientHeight <= 50;
};

const systemPromptInfoContent = document.getElementById('prompt-info-content');
const systemPromptInfoText = document.getElementById('prompt-info-text');
const toggleIcon = document.querySelector('.toggle-icon');

const roleSelect = document.getElementById('role-select');
const initMsgSelect = document.getElementById('initial-msg-select');
const modeSelect = document.getElementById('mode-select');
const t2iSelect = document.getElementById('t2i-select');

const chatBubbles = document.getElementById('chat-bubbles');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const stopButton = document.getElementById('stop-button');

const inputHistory = [];
let historyIndex = 0;

chatBubbles.addEventListener('scroll', () => {
    autoScroll = isNearBottom();
});

const updateWelcomeButtonVisibility = () => {
    const btn = document.getElementById('welcome-toggle-btn');
    if (!btn) return;
    const cardHtml = cards[currentCardName]?.html;
    btn.style.display = cardHtml ? '' : 'none';
};

const clearContext = () => {
    if (abortController) return;
    chatContext = [];
    chatBubbles.innerHTML = '';
    refreshBubbleIndices();
};

const updateSystemPrompt = async () => {
    if (!chatStarted) clearContext();
    systemPrompt = '';
    const roleKey = roleSelect.value.trim();
    const t2iKey = t2iSelect.value.trim();
    let modeKey = modeSelect.value.trim();
    if (osrMode === 'disabled') {
        modeSelect.style.display = 'none';
        modeKey = '';
    } else {
        modeSelect.style.display = '';
    }
    
    if (roleKey && Object.hasOwn(systemRoles, roleKey) && systemRoles[roleKey]) systemPrompt += i18n.tr(String(systemRoles[roleKey])) + '\n\n';
    const hasImages = currentCardName && cards[currentCardName] && cards[currentCardName].images && Object.keys(cards[currentCardName].images).length > 0;
    if (t2iKey || modeKey || hasImages) {
        systemPrompt += `# ${i18n.tr("Always-do items")}\n\n${i18n.tr("Every time you generate a response, you must do the following:")}`;
        if (t2iKey && Object.hasOwn(t2iPrompts, t2iKey) && t2iPrompts[t2iKey]) systemPrompt += `\n\n- ${i18n.tr("Write text-to-image prompts")}:\n` + i18n.tr(String(t2iPrompts[t2iKey]));
        if (modeKey && Object.hasOwn(controlModes, modeKey) && controlModes[modeKey]) systemPrompt += `\n\n- ${i18n.tr("Output control commands")}:\n` + i18n.tr(String(controlModes[modeKey]));
        if (hasImages) {
            systemPrompt += `\n\n- ${i18n.tr("Pick appropriate images to insert into responses")}:\n${i18n.tr("Check if there are suitable images in the image library. If so, insert them via `<img src=\"<data>\" alt=\"<description>\" width=\"400\">`. The default width is 400, unless otherwise specified in the description. Only insert images when absolutely necessary.")}`;
        }
        systemPrompt += `\n\n`;
    }
    
    const cardKey = currentCardName;
    if (cardKey && Object.hasOwn(cards, cardKey)) {
        systemPrompt += `# ${i18n.tr("Game Settings")}\n\n`;
        if (cards[cardKey] && Object.hasOwn(cards[cardKey], 'system_prompt') && cards[cardKey]['system_prompt']) systemPrompt += i18n.tr(String(cards[cardKey]['system_prompt'])) + '\n\n';
        if (cards[cardKey] && cards[cardKey].images && Object.keys(cards[cardKey].images).length > 0) {
            systemPrompt += `# ${i18n.tr("Image Library")}\n\n${i18n.tr('May include background images, character sprites, event CGs, emoticons, etc. `data` is the image src, `description` describes the content and usage.')}\n\n${JSON.stringify(cards[cardKey].images, null, 2)}\n\n`;
        }
        initialMessageContent = '';
        if (selectedMessageIdx === 0 && Object.hasOwn(cards[cardKey], 'context') && Array.isArray(cards[cardKey].context) && cards[cardKey].context[0]) {
            initialMessageContent = cards[cardKey].context[0].content || '';
        } else if (selectedMessageIdx > 0 && Array.isArray(cardMessages) && selectedMessageIdx - 1 < cardMessages.length) {
            initialMessageContent = cardMessages[selectedMessageIdx - 1];
        }
        if (!chatStarted) {
            chatContext = [];
            await renderChatContext(chatContext);
        }
    }
    
    if (userInfo.username || userInfo.profile) {
        systemPrompt += `# ${i18n.tr("Player Character Settings")}\n\n`;
        if (userInfo.username) systemPrompt += `${i18n.tr("Name")}：${userInfo.username}\n\n`;
        if (userInfo.profile) systemPrompt += `${userInfo.profile}\n\n`;
    }

    if (userInfo.username) systemPrompt = systemPrompt.replace(/\{\{user\}\}/gi, userInfo.username);
    const placeholderHint = "# Placeholders\n\nPlaceholders should be replaced with appropriate text during output.\n\n- {{user}}: Represents the player.\n- {{char}}: Represents the character.";
    if (/\{(char|user)\}/i.test(systemPrompt)) systemPrompt += i18n.tr(placeholderHint);

    if (initialMessageContent && chatContext.length <= 4) {
        systemPrompt += `\n\n# ${i18n.tr('First Dialogue (Initial Scenario)')}\n\n${initialMessageContent}`;
    }

    systemPrompt = systemPrompt.trim();
    systemPromptInfoText.textContent = systemPrompt;
}

roleSelect.addEventListener('change', updateSystemPrompt);
modeSelect.addEventListener('change', updateSystemPrompt);
t2iSelect.addEventListener('change', updateSystemPrompt);

document.getElementById('prompt-info-toggle').addEventListener('click', () => {
    if (systemPromptInfoContent.style.display === 'block') {
        systemPromptInfoContent.style.display = 'none';
        toggleIcon.classList.remove('rotated');
    } else {
        systemPromptInfoContent.style.display = 'block';
        toggleIcon.classList.add('rotated');
        updateSystemPrompt();
    }
});

const populateSelect = async (dict, selectElement, selectFirst = true, clear = false) => {
    if (clear) selectElement.innerHTML = '<option value=""></option>';
    const fragment = document.createDocumentFragment();
    const keys = Object.keys(dict);
    keys.forEach((key, index) => {
        const option = document.createElement('option');
        option.value = key;
        option.textContent = key;
        if (index === 0 && selectFirst) option.selected = true;
        fragment.appendChild(option);
    });
    selectElement.appendChild(fragment);
};

function populateInitialMsgSelect() {
    const cardKey = currentCardName;
    cardMessages = (cardKey && cards[cardKey] && cards[cardKey].messages) ? cards[cardKey].messages : [];
    initMsgSelect.innerHTML = '';
    const defaultContent = (cardKey && cards[cardKey] && cards[cardKey].context && cards[cardKey].context[0]) ? cards[cardKey].context[0].content : '';
    const emptyOpt = document.createElement('option');
    emptyOpt.value = '-1';
    emptyOpt.textContent = '';
    initMsgSelect.appendChild(emptyOpt);
    let displayNum = 0;
    if (defaultContent) {
        displayNum++;
        const opt = document.createElement('option');
        opt.value = 0;
        opt.textContent = String(displayNum);
        opt.title = defaultContent.length > 30 ? defaultContent.slice(0, 30) + '...' : defaultContent;
        initMsgSelect.appendChild(opt);
    }
    cardMessages.forEach((msg, i) => {
        displayNum++;
        const opt = document.createElement('option');
        opt.value = i + 1;
        opt.textContent = String(displayNum);
        const displayText = msg.length > 30 ? msg.slice(0, 30) + '...' : msg;
        opt.title = displayText;
        initMsgSelect.appendChild(opt);
    });
    if (displayNum > 0) {
        initMsgSelect.style.display = '';
        initMsgSelect.value = '0';
        selectedMessageIdx = 0;
    } else {
        initMsgSelect.style.display = 'none';
    }
}

initMsgSelect.addEventListener('change', function () {
    if (chatStarted) {
        this.value = String(selectedMessageIdx);
        return;
    }
    selectedMessageIdx = parseInt(this.value);
    if (selectedMessageIdx === -1) {
        clearContext();
    } else {
        updateSystemPrompt();
    }
});

document.addEventListener('DOMContentLoaded', async function () {
    setTimeout(async () => {
        t = Date.now();
        systemRoles = await fetchJson('json/prompts/system_roles.json?t=' + t);
        cards = await fetchJson('/api/cards?t=' + t);
        controlModes = await fetchJson('json/prompts/control_modes.json?t=' + t);
        t2iPrompts = await fetchJson('json/prompts/t2i.json?t=' + t);
        await populateSelect(systemRoles, roleSelect);
        await populateSelect(controlModes, modeSelect);
        await populateSelect(t2iPrompts, t2iSelect);
        const urlParams = new URLSearchParams(window.location.search);
        const cardParam = urlParams.get('card');
        if (cardParam && Object.hasOwn(cards, cardParam)) {
            currentCardName = cardParam;
            const cardData = await fetchJson('/api/cards/' + encodeURIComponent(cardParam) + '?t=' + Date.now());
            if (cardData && Object.hasOwn(cardData, cardParam)) {
                cards[cardParam] = cardData[cardParam];
            }
        }
        const userRes = await fetch('/api/config/user?t=' + Date.now());
        const userData = await userRes.json().catch(() => ({}));
        userInfo = { username: userData.username || '', profile: userData.profile || '' };
        const osrConfig = await fetchJson('/api/config?t=' + Date.now());
        osrMode = osrConfig.mode || 'disabled';
        const comfyuiConfig = await fetchJson('/api/config/comfyui?t=' + Date.now());
        comfyuiType = (comfyuiConfig.type && comfyuiConfig.type !== 'disabled') ? comfyuiConfig.type : '';
        if (!comfyuiType) {
            t2iSelect.style.display = 'none';
            t2iSelect.value = '';
        } else {
            t2iSelect.style.display = '';
            var t2iKeys = Object.keys(t2iPrompts);
            if (comfyuiType === 'zit' && t2iKeys.includes('Natural')) {
                t2iSelect.value = 'Natural';
            } else if ((comfyuiType === 'sdxl' || comfyuiType === 'anima') && t2iKeys.includes('Danbooru')) {
                t2iSelect.value = 'Danbooru';
            }
        }
        populateInitialMsgSelect();
        updateSystemPrompt();
        if (currentCardName) {
            try {
                const cacheRes = await fetch('/api/chat/cache/' + encodeURIComponent(currentCardName) + '?t=' + Date.now());
                if (cacheRes.ok) {
                    const cache = await cacheRes.json();
                    if (cache.chat_started && Array.isArray(cache.context) && cache.context.length > 0) {
                        if (cache.role && Object.hasOwn(systemRoles, cache.role)) roleSelect.value = cache.role;
                        if (cache.mode && Object.hasOwn(controlModes, cache.mode)) modeSelect.value = cache.mode;
                        if (comfyuiType && cache.t2i && Object.hasOwn(t2iPrompts, cache.t2i)) t2iSelect.value = cache.t2i;
                        if (cache.selected_message_idx !== undefined) selectedMessageIdx = cache.selected_message_idx;
                        chatContext = cache.context;
                        chatStarted = cache.chat_started;
                        updateSystemPrompt();
                        if (initialMessageContent && chatContext.length > 0 && chatContext[0].role === 'assistant' && chatContext[0].content === initialMessageContent) {
                            chatContext.shift();
                        }
                        renderChatContext(chatContext);
                    }
                }
            } catch (e) {
                console.warn('Failed to load chat cache:', e);
            }

            updateWelcomeButtonVisibility();
            // Show welcome page if card has html content and no chat cache
            const cardHtml = cards[currentCardName]?.html;
            if (cardHtml && !chatStarted) {
                const welcomeContainer = document.getElementById('welcome-container');
                const welcomeFrame = document.getElementById('welcome-frame');
                const chatContainer = document.querySelector('.chat-container');
                if (welcomeContainer && welcomeFrame && chatContainer) {
                    welcomeFrame.srcdoc = cardHtml;
                    welcomeContainer.style.display = 'flex';
                    chatContainer.style.display = 'none';
                }
            }
        }

        const sb = new StickySidebar({ icon: 'shapes' });
        sb.addButton({ icon: 'skip-up', title: 'Jump to Top', onClick: () => { chatBubbles.scrollTop = 0; } });
        sb.addButton({ icon: 'skip-down', title: 'Jump to Bottom', onClick: () => { chatBubbles.scrollTop = chatBubbles.scrollHeight; } });
        sb.addButton({ icon: 'lightbulb', title: 'Toggle Theme', onClick: () => {
            const isDark = document.documentElement.dataset.theme === 'dark';
            switchTheme(!isDark);
        }});
        sb.addButton({ icon: 'code', title: 'Toggle System Prompt', onClick: () => {
            const section = document.querySelector('.prompt-info-section');
            const hidden = section.style.display === 'none';
            section.style.display = hidden ? '' : 'none';
            if (hidden) updateSystemPrompt();
        }});

        if (osrMode !== 'disabled') {
            const grid = document.querySelector('.sidebar-grid');
            if (grid) {
                const customConfigs = [
                    { label: 'S', params: { max_pos: 80, min_pos: 0, freq: 0.2, decline_ratio: 0.5, loop_count: 9999 } },
                    { label: 'M', params: { max_pos: 90, min_pos: 0, freq: 0.6, decline_ratio: 0.4, loop_count: 9999 } },
                    { label: 'F', params: { max_pos: 100, min_pos: 0, freq: 2, decline_ratio: 0.5, loop_count: 9999 } },
                    { label: 'T', params: { max_pos: 100, min_pos: 45, freq: 1, decline_ratio: 0.65, loop_count: 9999 } },
                    { label: 'B', params: { max_pos: 55, min_pos: 0, freq: 0.8, decline_ratio: 0.45, loop_count: 9999 } },
                ];
                customConfigs.forEach(({ label, params }) => {
                    const btn = document.createElement('button');
                    btn.className = 'sidebar-btn script-label';
                    btn.textContent = label;
                    btn.title = JSON.stringify(params);
                    btn.addEventListener('click', () => {
                        fetch('/api/script/custom', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify(params)
                        }).catch(console.error);
                        isDeviceMoving = true;
                    });
                    grid.appendChild(btn);
                });

                const stopBtn = document.createElement('button');
                stopBtn.className = 'sidebar-btn';
                stopBtn.innerHTML = '<svg><use xlink:href="/img/icons.svg?v=200#icon-stop"></use></svg>';
                stopBtn.title = 'Stop';
                stopBtn.addEventListener('click', () => {
                    fetch('/api/script/stop', { method: 'GET' }).catch(console.error);
                    isDeviceMoving = false;
                    toast.show(i18n.tr('Movement has stopped'), 'success');
                });
                grid.appendChild(stopBtn);
            }
        }
    }, 500);
});

const renderChatContext = async (contextArray) => {
    chatBubbles.innerHTML = '';
    if (initialMessageContent) {
        const initBubble = document.createElement('div');
        initBubble.className = 'bubble assistant initial-msg';
        initBubble.innerHTML = marked.parse(processContext(initialMessageContent));
        chatBubbles.appendChild(initBubble);
    }
    for (let i = 0; i < contextArray.length; i++) {
        const msg = contextArray[i];
        if (typeof msg === 'object' && ['user', 'assistant'].includes(msg.role) && typeof msg.content === 'string') {
            const bubble = document.createElement('div');
            bubble.className = `bubble ${msg.role}`;
            bubble.dataset.contextIndex = i;

            if (msg.role === 'assistant') {
                const originalContent = msg.content;
                const scriptDict = extractDict(originalContent);
                bubble.innerHTML = marked.parse(processContext(originalContent));

                if (Object.keys(scriptDict).length > 0) {
                    bubble.appendChild(createScriptButton(scriptDict));
                }

                addEditIcon(bubble);
                addT2IButtonIfNeeded(bubble, originalContent, i);
                if (msg.usage) {
                    addUsageInfo(bubble, msg.usage);
                }
            } else {
                bubble.innerHTML = msg.content;
            }

            if (msg.t2i && typeof msg.t2i === 'string') {
                bubble.appendChild(createT2IContainer(msg.t2i, i));
            }

            chatBubbles.appendChild(bubble);
        }
    }
    chatBubbles.scrollTop = chatBubbles.scrollHeight;
};

const refreshBubbleIndices = () => {
    const bubbles = chatBubbles.querySelectorAll('.bubble:not(.initial-msg)');
    bubbles.forEach((bubble, index) => {
        bubble.dataset.contextIndex = index;
    });
};

document.getElementById('settings-button').addEventListener('click', () => {
    window.location.href = '/settings';
});

document.getElementById('home-button').addEventListener('click', () => {
    window.location.href = '/';
});

document.getElementById('welcome-close-btn').addEventListener('click', () => {
    const welcomeContainer = document.getElementById('welcome-container');
    const chatContainer = document.querySelector('.chat-container');
    if (welcomeContainer && chatContainer) {
        welcomeContainer.style.display = 'none';
        chatContainer.style.display = 'flex';
    }
});

document.getElementById('welcome-toggle-btn').addEventListener('click', () => {
    const welcomeContainer = document.getElementById('welcome-container');
    const chatContainer = document.querySelector('.chat-container');
    if (!welcomeContainer || !chatContainer) return;
    if (welcomeContainer.style.display === 'none' || welcomeContainer.style.display === '') {
        const cardHtml = cards[currentCardName]?.html;
        if (cardHtml) {
            const frame = document.getElementById('welcome-frame');
            if (frame) frame.srcdoc = cardHtml;
            welcomeContainer.style.display = 'flex';
            chatContainer.style.display = 'none';
        }
    } else {
        welcomeContainer.style.display = 'none';
        chatContainer.style.display = 'flex';
    }
});

document.getElementById('clear-button').addEventListener('click', async () => {
    if (abortController) return;
    const confirmed = await modal.confirm(i18n.tr('Are you sure you want to clear the context?'));
    if (!confirmed) return;
    clearContext();
    chatStarted = false;
    if (currentCardName) {
        fetch('/api/chat/cache/' + encodeURIComponent(currentCardName), { method: 'DELETE' }).catch(() => {});
    }
    renderChatContext(chatContext);
});

document.getElementById('undo-button').addEventListener('click', async () => {
    if (abortController) return;
    const confirmed = await modal.confirm(i18n.tr('Are you sure you want to undo the last message?'));
    if (!confirmed) return;
    const bubbles = chatBubbles.querySelectorAll('.bubble');
    if (bubbles.length >= 2 && chatContext.length >= 2) {
        chatBubbles.removeChild(bubbles[bubbles.length - 1]);
        chatBubbles.removeChild(bubbles[bubbles.length - 2]);
        chatContext.splice(-2);
        if (chatContext.length <= 1) chatStarted = false;
        refreshBubbleIndices();
    }
});

async function saveChatCache(showToast = true) {
    if (!currentCardName) {
        if (showToast) toast.show(i18n.tr('No card selected'), 'warn');
        return;
    }
    try {
        const res = await fetch('/api/chat/cache', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                card_name: currentCardName,
                context: chatContext,
                chat_started: chatStarted,
                selected_message_idx: selectedMessageIdx,
                system_prompt: systemPrompt,
                role: roleSelect.value,
                mode: modeSelect.value,
                t2i: t2iSelect.value
            })
        });
        if (res.ok) {
            if (showToast) toast.show(i18n.tr('Cache saved'), 'success');
        } else {
            const err = await res.json().catch(() => ({}));
            if (showToast) toast.show(`${i18n.tr("Failed to save cache")}: ` + (err.detail || ''), 'error');
        }
    } catch (e) {
        console.error('Failed to save cache:', e);
        if (showToast) toast.show(i18n.tr("Failed to save cache"), 'error');
    }
}

document.getElementById('save-button').addEventListener('click', () => saveChatCache());

document.getElementById('export-button').addEventListener('click', () => {
    const roleSelectedKey = roleSelect.value;
    const cardSelectedKey = currentCardName;
    const modeSelectedKey = modeSelect.value;

    const exportData = {
        cards: cardSelectedKey ? { [cardSelectedKey]: cards[cardSelectedKey] } : {},
        context: chatContext.map(msg => {
            if (msg && typeof msg === 'object') {
                const { t2i, ...rest } = msg;
                return rest;
            }
            return msg;
        })
    };
    const dataStr = JSON.stringify(exportData, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${Date.now()}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
});

document.getElementById('import-button').addEventListener('click', () => {
    document.getElementById('import-file-input').click();
});
const updateDict = (original, updates) => ({ ...original, ...updates });
document.getElementById('import-file-input').addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    try {
        const text = await file.text();
        const imported = JSON.parse(text);
        if (!imported || (typeof imported !== 'object')) throw new Error('Invalid import format: root must be an object');

        if (imported.cards && Object.keys(imported.cards).length > 0) {
            cards = updateDict(cards, imported.cards);
            currentCardName = Object.keys(imported.cards)[0];
            updateWelcomeButtonVisibility();
        }
        updateSystemPrompt();

        const externalContext = Array.isArray(imported.context) ? imported.context : [];
        chatContext = [...externalContext];
        if (initialMessageContent && chatContext.length > 0 && chatContext[0].role === 'assistant' && chatContext[0].content === initialMessageContent) {
            chatContext.shift();
        }
        await renderChatContext(chatContext);

        chatStarted = chatContext.length > 0;
        populateInitialMsgSelect();
    } catch (err) {
        console.error('Import failed:', err);
    } finally {
        e.target.value = '';
    }
});

let abortController = null;
let isDeviceMoving = false;

async function sendMessage(content = null, isRetry = false) {
    if (abortController) return;
    const messageContent = (content !== null && typeof content === 'string') ? content : messageInput.value.trim();
    if (!messageContent) return;
    chatStarted = true;
    document.body.focus();

    abortController = new AbortController();

    if (!isRetry) {
        const userBubble = document.createElement('div');
        userBubble.className = 'bubble user';
        userBubble.textContent = messageContent;
        userBubble.dataset.contextIndex = chatContext.length;
        chatBubbles.appendChild(userBubble);
        messageInput.value = '';
        inputHistory.push(messageContent);
        historyIndex = inputHistory.length;
        chatContext.push({ role: "user", content: messageContent });
    }

    try {
        if (abortController.signal.aborted) {
            abortController = null;
            return;
        }

        const response = await fetch('/api/llm/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_message: messageContent,
                context_messages: removeT2i(chatContext.slice(0, -1)) || [],
                system_prompt: systemPrompt || ""
            }),
            signal: abortController.signal,
        });

        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let assistantBubble = document.createElement('div');
        assistantBubble.className = 'bubble assistant';
        chatBubbles.appendChild(assistantBubble);

        let buffer = '';
        let markdownContent = '';
        let usageRaw = '';
        assistantBubble.classList.add('thinking');
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop();
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.token) {
                            if (data.token.includes('<usage>')) {
                                usageRaw += data.token;
                            } else {
                                markdownContent += data.token;
                                if (data.token.includes("__THINKING_FINISHED__")) {
                                    assistantBubble.innerHTML = '';
                                    markdownContent = '';
                                    assistantBubble.classList.remove('thinking');
                                    const afterThinking = data.token.split("__THINKING_FINISHED__")[1];
                                    if (afterThinking) {
                                        assistantBubble.innerHTML += marked.parse(afterThinking);
                                        markdownContent += afterThinking;
                                    }
                                } else {
                                    assistantBubble.innerHTML = marked.parse(markdownContent);
                                }
                                if (autoScroll) chatBubbles.scrollTop = chatBubbles.scrollHeight;
                                if (autoScroll) assistantBubble.scrollTop = assistantBubble.scrollHeight;
                            }
                        }
                    } catch (e) {
                        console.warn('Failed to parse SSE data:', line);
                    }
                }
            }
        }

        if (buffer.startsWith('data: ')) {
            try {
                const data = JSON.parse(buffer.slice(6));
                if (data.token) {
                    if (data.token.includes('<usage>')) {
                        usageRaw += data.token;
                    } else {
                        markdownContent += data.token;
                        assistantBubble.innerHTML = marked.parse(markdownContent);
                        if (autoScroll) chatBubbles.scrollTop = chatBubbles.scrollHeight;
                    }
                }
            } catch (e) {
                console.warn('Failed to parse remaining SSE data:', buffer);
            }
        }

        if (!usageRaw) {
            const usageMatch = markdownContent.match(/<usage>([\s\S]*?)<\/usage>/);
            if (usageMatch) {
                usageRaw = usageMatch[0];
                markdownContent = markdownContent.replace(/<usage>[\s\S]*?<\/usage>/, '');
            }
        }

        const scriptDict = extractDict(markdownContent);
        assistantBubble.innerHTML = marked.parse(processContext(markdownContent));
        if (Object.keys(scriptDict).length > 0) {
            const isSent = await sendCustom(scriptDict);
            if (isSent) {
                assistantBubble.appendChild(createScriptButton(scriptDict));
            }
        }

        assistantBubble.classList.remove('thinking');
        if (autoScroll) chatBubbles.scrollTop = chatBubbles.scrollHeight;

        try {
            if (markdownContent.includes("STOP_TOY")) await fetch('/api/script/stop', { method: 'GET' });
            if (markdownContent.includes("DARK_THEME")) switchTheme(true);
            if (markdownContent.includes("LIGHT_THEME")) switchTheme(false);
        } catch (e) {
            console.error(e);
        }

        let usageData = null;
        if (usageRaw) {
            const usageMatch = usageRaw.match(/<usage>([\s\S]*?)<\/usage>/);
            if (usageMatch) {
                try { usageData = JSON.parse(usageMatch[1]); } catch (e) {}
            }
        }

        addEditIcon(assistantBubble);
        chatContext.push({ role: "assistant", content: markdownContent, ...(usageData ? { usage: usageData } : {}) });
        const assistantIndex = chatContext.length - 1;
        assistantBubble.dataset.contextIndex = assistantIndex;
        addT2IButtonIfNeeded(assistantBubble, markdownContent, assistantIndex);
        if (usageData) {
            addUsageInfo(assistantBubble, usageData);
        }
        saveChatCache(false);
    } catch (error) {
        if (error.name === 'AbortError') {
            console.info('Conversation aborted by user');
        } else {
            console.error('Failed to send message:', error);
        }
    } finally {
        abortController = null;
    }
}

const extractDict = (str) => {
    try {
        let start = str.indexOf('{');
        if (start === -1) return {};
        let depth = 0;
        for (let i = start; i < str.length; i++) {
            if (str[i] === '{') depth++;
            else if (str[i] === '}') {
                depth--;
                if (depth === 0) {
                    return JSON.parse(str.slice(start, i + 1));
                }
            }
        }
        return {};
    } catch (error) {
        return {};
    }
};

const isValidFormat = o => o && typeof o == 'object' && Object.keys(o).length == 5 && ['max', 'min', 'freq', 'decline_ratio', 'loop_count'].every(k => k in o && typeof o[k] == 'number' && !isNaN(o[k]));
const isValidActions = a => Array.isArray(a) && a.length > 0 && a.every(i => i && typeof i === 'object' && 'at' in i && 'pos' in i && typeof i.at === 'number' && typeof i.pos === 'number' && isFinite(i.at) && isFinite(i.pos));

const removeDict = (str) => {
    try {
        let result = '';
        let last = 0;
        for (let i = 0; i < str.length; i++) {
            if (str[i] === '{') {
                let depth = 1;
                let start = i;
                i++;
                while (i < str.length && depth > 0) {
                    if (str[i] === '{') depth++;
                    else if (str[i] === '}') depth--;
                    i++;
                }
                result += str.slice(last, start);
                last = i;
            }
        }
        result += str.slice(last);
        return result.trim();
    } catch (error) {
        return str;
    }
};

const generateRepeatedActions = (scriptDict) => {
    const { loop_count: loopCount = 100 } = scriptDict;

    if (Array.isArray(scriptDict.custom_actions) && scriptDict.custom_actions.length > 0) {
        if (loopCount <= 1 || scriptDict.custom_actions.length < 3) {
            return [...scriptDict.custom_actions];
        }
        const sorted = [...scriptDict.custom_actions].sort((a, b) => a.at - b.at);
        const startAt = sorted[0].at;
        const aligned = sorted.map(a => ({ at: a.at - startAt, pos: a.pos }));
        const lastAt = aligned[aligned.length - 1].at;
        const result = [...aligned];
        for (let i = 1; i < loopCount; i++) {
            const offset = i * lastAt;
            for (let j = 1; j < aligned.length; j++) {
                result.push({ at: aligned[j].at + offset, pos: aligned[j].pos });
            }
        }
        return result;
    }

    if (isValidFormat(scriptDict)) {
        let maxPos = Math.min(100, Math.max(0, scriptDict.max ?? 100));
        let minPos = Math.min(100, Math.max(0, scriptDict.min ?? 0));
        if (minPos > maxPos) { const t = minPos; minPos = maxPos; maxPos = t; }
        const freq = Math.min(2.5, Math.max(0.01, scriptDict.freq ?? 1));
        const declineRatio = Math.min(0.7, Math.max(0.3, scriptDict.decline_ratio ?? 0.5));
        if (loopCount <= 0) return [{ at: 0, pos: maxPos }];
        const cycleTimeMs = Math.round(1000 / freq);
        const declineTime = Math.round(cycleTimeMs * declineRatio);
        const riseTime = Math.round(cycleTimeMs * (1 - declineRatio));
        const actions = [{ at: 0, pos: maxPos }];
        let currentTime = 0;
        const goUp = maxPos < (maxPos + minPos) / 2;
        for (let i = 0; i < loopCount; i++) {
            if (goUp) {
                actions.push(
                    { at: currentTime + declineTime, pos: minPos },
                    { at: currentTime + cycleTimeMs, pos: maxPos }
                );
            } else {
                actions.push(
                    { at: currentTime + riseTime, pos: maxPos },
                    { at: currentTime + cycleTimeMs, pos: minPos }
                );
            }
            currentTime += cycleTimeMs;
        }
        return actions;
    }

    return [];
};

const createScriptCanvas = (scriptDict) => {
    const canvas = document.createElement('canvas');
    canvas.width = 200;
    canvas.height = 20;
    canvas.className = 'script-canvas';

    const color = '#FF4444';
    const ctx = canvas.getContext('2d');
    ctx.strokeStyle = color;
    ctx.lineWidth = 1;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    const actions = generateRepeatedActions(scriptDict);
    if (actions.length > 0) {
        ctx.beginPath();
        for (let i = 0; i < actions.length; i++) {
            const x = (actions[i].at / 5000) * 200;
            const y = 20 - (actions[i].pos / 100) * 20;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.stroke();
    }

    return canvas;
};

const createScriptButton = (scriptDict) => {
    const btn = document.createElement('button');
    btn.className = 'script-btn';
    btn.title = JSON.stringify(scriptDict);
    btn.appendChild(createScriptCanvas(scriptDict));
    btn.addEventListener('click', () => sendCustom(scriptDict));
    return btn;
};

const removeMarks = (
    str,
    marks = [
        'STOP_TOY',
        'DARK_THEME',
        'LIGHT_THEME',
        '```json',
        '```',
    ]
) => {
    let result = str;
    for (const mark of marks) {
        result = result.split(mark).join('');
    }
    return result;
};

const processContext = (context) => {
    return removeMarks(removeDict(removeComfyUITags(context)));
};

const enableEditMode = (bubble) => {
    const bubbleIndex = parseInt(bubble.dataset.contextIndex);
    if (isNaN(bubbleIndex) || bubbleIndex < 0 || bubbleIndex >= chatContext.length) return;

    const role = bubble.classList.contains('user') ? 'user' : 'assistant';
    const originalContent = chatContext[bubbleIndex].content;

    const textarea = document.createElement('textarea');
    textarea.value = originalContent;
    textarea.className = 'edit-textarea';

    bubble.innerHTML = '';
    bubble.appendChild(textarea);
    textarea.focus();

    const saveEdit = () => {
        const newContent = textarea.value.trim();
        const currentMsg = chatContext[bubbleIndex];
        const hadT2I = currentMsg.t2i;
        const hadUsage = currentMsg.usage;

        if (newContent === currentMsg.content) {
            revertBubble(bubble, role, originalContent, chatContext[bubbleIndex].t2i, chatContext[bubbleIndex].usage);
            return;
        }

        chatContext[bubbleIndex] = {
            role: role,
            content: newContent,
            ...(hadT2I ? { t2i: hadT2I } : {}),
            ...(hadUsage ? { usage: hadUsage } : {})
        };

        if (role === 'assistant') {
            const scriptDict = extractDict(newContent);
            bubble.innerHTML = marked.parse(processContext(newContent));
            if (Object.keys(scriptDict).length > 0) {
                bubble.appendChild(createScriptButton(scriptDict));
            }
            if (hadT2I) {
                bubble.appendChild(createT2IContainer(hadT2I, bubbleIndex));
            }
        } else {
            bubble.innerHTML = newContent;
            delete chatContext[bubbleIndex].t2i;
        }

        addEditIcon(bubble);
        addT2IButtonIfNeeded(bubble, newContent, bubbleIndex);
        if (chatContext[bubbleIndex] && chatContext[bubbleIndex].usage) {
            addUsageInfo(bubble, chatContext[bubbleIndex].usage);
        }
        bubble.className = `bubble ${role}`;
    };

    textarea.addEventListener('blur', saveEdit);
};

const revertBubble = (bubble, role, content, t2i = null, usage = null) => {
    if (role === 'assistant') {
        const scriptDict = extractDict(content);
        bubble.innerHTML = marked.parse(processContext(content));
        if (Object.keys(scriptDict).length > 0) {
            bubble.appendChild(createScriptButton(scriptDict));
        }
        if (t2i) {
            const idx = parseInt(bubble.dataset.contextIndex);
            bubble.appendChild(createT2IContainer(t2i, !isNaN(idx) ? idx : undefined));
        }
    } else {
        bubble.innerHTML = content;
    }
    addEditIcon(bubble);
    addT2IButtonIfNeeded(bubble, content, parseInt(bubble.dataset.contextIndex));
    if (usage) {
        addUsageInfo(bubble, usage);
    }
    bubble.className = `bubble ${role}`;
};

const addEditIcon = (bubble) => {
    const editIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    editIcon.setAttribute('class', 'edit-icon');
    const useElem = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    useElem.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', '/img/icons.svg?v=200#icon-edit');
    editIcon.appendChild(useElem);
    bubble.appendChild(editIcon);

    if (bubble.classList.contains('assistant')) {
        const existingRetry = bubble.querySelector('.retry-icon');
        if (existingRetry) existingRetry.remove();

        const retryIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        retryIcon.setAttribute('class', 'retry-icon');
        const useRetry = document.createElementNS('http://www.w3.org/2000/svg', 'use');
        useRetry.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', '/img/icons.svg?v=200#icon-refresh');
        retryIcon.appendChild(useRetry);
        retryIcon.addEventListener('click', async (e) => {
            e.stopPropagation();
            await retryAssistantFromBubble(bubble);
        });
        bubble.insertBefore(retryIcon, editIcon);
    }
};

const createT2IContainer = (imageUrl, contextIndex) => {
    const container = document.createElement('div');
    container.className = 't2i-image-container';

    const img = document.createElement('img');
    img.src = imageUrl;
    container.appendChild(img);

    const closeBtn = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    closeBtn.setAttribute('class', 't2i-close-btn');
    closeBtn.setAttribute('viewBox', '0 0 24 24');
    const useElem = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    useElem.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', '/img/icons.svg?v=200#icon-close');
    closeBtn.appendChild(useElem);
    closeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        container.remove();
        if (contextIndex !== undefined && chatContext[contextIndex]) {
            delete chatContext[contextIndex].t2i;
        }
        saveChatCache(false);
    });
    container.appendChild(closeBtn);

    return container;
};

const addT2IButtonIfNeeded = (bubble, originalContent, contextIndex) => {
    const existing = bubble.querySelector('.t2i-button');
    if (existing) existing.remove();

    const comfyPrompt = extractComfyUIPrompt(originalContent);
    if (!comfyPrompt) return;

    const t2iButton = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    t2iButton.setAttribute('class', 't2i-button');
    const useElem = document.createElementNS('http://www.w3.org/2000/svg', 'use');
    useElem.setAttributeNS('http://www.w3.org/1999/xlink', 'xlink:href', '/img/icons.svg?v=200#icon-image');
    t2iButton.appendChild(useElem);

    t2iButton.addEventListener('click', async (e) => {
        e.stopPropagation();

        const existingContainer = bubble.querySelector('.t2i-image-container');
        if (existingContainer) {
            existingContainer.remove();
        }

        const imageUrl = await sendT2I(comfyPrompt);
        if (!imageUrl) return;

        const staleContainer = bubble.querySelector('.t2i-image-container');
        if (staleContainer) staleContainer.remove();

        if (contextIndex !== undefined && chatContext[contextIndex]) {
            chatContext[contextIndex].t2i = imageUrl;
        }

        bubble.appendChild(createT2IContainer(imageUrl, contextIndex));

        saveChatCache(false);
    });

    const editIcon = bubble.querySelector('.edit-icon');
    if (editIcon) {
        bubble.insertBefore(t2iButton, editIcon);
    } else {
        bubble.appendChild(t2iButton);
    }
};

const addUsageInfo = (bubble, usage) => {
    const el = document.createElement('span');
    el.className = 'usage-info';
    const tokensSpan = document.createElement('span');
    tokensSpan.className = 'usage-tokens';
    tokensSpan.textContent = '\u2191' + (usage.prompt_tokens || '?') + ' \u2193' + (usage.completion_tokens || '?');
    el.appendChild(tokensSpan);
    if (usage.model) {
        const modelSpan = document.createElement('span');
        modelSpan.className = 'usage-model';
        modelSpan.textContent = usage.model;
        el.appendChild(modelSpan);
    }
    const retryIcon = bubble.querySelector('.retry-icon');
    if (retryIcon) {
        bubble.insertBefore(el, retryIcon);
    } else {
        bubble.appendChild(el);
    }
};

const retryAssistantFromBubble = async (bubble) => {
    if (abortController) return;
    const confirmed = await modal.confirm(i18n.tr('Are you sure you want to retry?'));
    if (!confirmed) return;
    const bubbleIndex = parseInt(bubble.dataset.contextIndex);
    if (isNaN(bubbleIndex) || bubbleIndex < 1 || !bubble.classList.contains('assistant')) return;

    const userIndex = bubbleIndex - 1;
    if (userIndex < 0 || !chatContext[userIndex]) return;

    const userMessage = chatContext[userIndex].content;
    if (typeof userMessage !== 'string') return;

    const allBubbles = chatBubbles.querySelectorAll('.bubble[data-context-index]');
    for (const b of [...allBubbles].reverse()) {
        const idx = parseInt(b.dataset.contextIndex);
        if (!isNaN(idx) && idx >= bubbleIndex) {
            b.remove();
        }
    }

    chatContext.splice(bubbleIndex);

    sendMessage(userMessage, true);
};

async function sendCustom(scriptDict) {
    if (isValidFormat(scriptDict)) {
        try {
            const response = await fetch('/api/script/custom', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    max_pos: scriptDict.max ?? 100,
                    min_pos: scriptDict.min ?? 0,
                    freq: scriptDict.freq ?? 1.0,
                    decline_ratio: scriptDict.decline_ratio ?? 0.5,
                    loop_count: scriptDict.loop_count ?? 100
                })
            });
            isDeviceMoving = true;
            return true;
        } catch (e) {
            console.error(e);
        }
    } else if (Object.hasOwn(scriptDict, 'custom_actions') && isValidActions(scriptDict.custom_actions)) {
        try {
            const response = await fetch('/api/script/custom', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    loop_count: scriptDict.loop_count ?? 100,
                    custom_actions: scriptDict.custom_actions
                })
            });
            isDeviceMoving = true;
            return true;
        } catch (e) {
            console.error(e);
        }
    }
    return false;
}

sendButton.addEventListener('click', () => sendMessage());
messageInput.addEventListener('keydown', (e) => {
    if ((e.key === 'ArrowUp' || e.key === 'ArrowDown') && (e.ctrlKey || e.altKey)) {
        e.preventDefault();
        if (inputHistory.length === 0) return;
        if (e.key === 'ArrowUp' && historyIndex > 0) {
            historyIndex--;
            messageInput.value = inputHistory[historyIndex];
        } else if (e.key === 'ArrowDown' && historyIndex < inputHistory.length) {
            historyIndex++;
            messageInput.value = historyIndex < inputHistory.length ? inputHistory[historyIndex] : '';
        } else {
            return;
        }
        const len = messageInput.value.length;
        messageInput.setSelectionRange(len, len);
        return;
    }
    if (e.key === 'Enter') {
        if (e.altKey || e.ctrlKey) {
            const start = e.target.selectionStart;
            const end = e.target.selectionEnd;
            const value = e.target.value;
            e.target.value = value.slice(0, start) + '\n' + value.slice(end);
            e.target.setSelectionRange(start + 1, start + 1);
            e.preventDefault();
            messageInput.scrollTop = messageInput.scrollHeight;
        } else {
            e.preventDefault();
            messageInput.blur();
            sendMessage();
        }
    }
});

const originalHeight = '70px';
messageInput.addEventListener('focus', () => {
    if (messageInput.value.trim() !== '') {
        messageInput.style.height = '150px';
        messageInput.style.padding = '10px 15px 70px 15px';
        chatBubbles.scrollTop = chatBubbles.scrollHeight;
    }
});
messageInput.addEventListener('blur', () => {
    messageInput.style.height = originalHeight;
    messageInput.style.padding = '10px 120px 10px 15px';
});
messageInput.addEventListener('input', () => {
    if (document.activeElement === messageInput && messageInput.value.trim() !== '') {
        messageInput.style.height = '150px';
        messageInput.style.padding = '10px 15px 70px 15px';
        chatBubbles.scrollTop = chatBubbles.scrollHeight;
    } else if (document.activeElement !== messageInput) {
        messageInput.style.height = originalHeight;
        messageInput.style.padding = '10px 120px 10px 15px';
    }
});

stopButton.addEventListener('click', async () => {
    if (isDeviceMoving) {
        try {
            await fetch('/api/script/stop', { method: 'GET' });
        } catch (error) { }
        isDeviceMoving = false;
        toast.show(i18n.tr('Movement has stopped'), 'success');
        return;
    }

    if (abortController) {
        abortController.abort();
        toast.show(i18n.tr('Messages have stopped'), 'success');
        abortController = null;
        const bubbles = chatBubbles.querySelectorAll('.bubble');
        const contextLen = chatContext.length;
        if (bubbles.length > contextLen) chatBubbles.removeChild(bubbles[bubbles.length - 1]);
        if (contextLen > 0 && chatContext[contextLen - 1].role === 'user') {
            chatContext.pop();
            if (chatBubbles.children.length > 0) chatBubbles.removeChild(chatBubbles.lastChild);
        }
        chatStarted = chatContext.length > 0;
        refreshBubbleIndices();
    }
});

const switchTheme = (isDark) => {
    document.documentElement.dataset.theme = isDark ? 'dark' : 'light';
    localStorage.setItem('chat-theme', isDark ? 'dark' : 'light');
};



document.addEventListener('DOMContentLoaded', () => {
    chatBubbles.addEventListener('click', (e) => {
        if (e.target.closest('.edit-icon')) {
            const bubble = e.target.closest('.bubble');
            if (bubble) enableEditMode(bubble);
        }
    });
    document.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 's') {
            e.preventDefault();
            saveChatCache();
        }
    });
});

const extractComfyUIPrompt = (text) => {
    const match = text.match(/<comfyui>([\s\S]*?)<\/comfyui>/i);
    return match ? match[1].trim() : '';
};

const removeComfyUITags = (text) => {
    return text.replace(/<comfyui>[\s\S]*?<\/comfyui>/gi, '');
};

const removeT2i = (obj) => {
    if (Array.isArray(obj)) {
        return obj.map(item => removeT2i(item));
    } else if (obj !== null && typeof obj === 'object') {
        const { t2i, usage, ...rest } = obj;
        const cleaned = {};
        for (const [key, value] of Object.entries(rest)) {
            cleaned[key] = removeT2i(value);
        }
        return cleaned;
    } else {
        return obj;
    }
};

var imageGenerating = false;
const sendT2I = async (prompt) => {
    if (imageGenerating) {
        console.warn('T2I is already generating an image');
        return null;
    }
    if (!prompt || typeof prompt !== 'string' || !prompt.trim()) {
        console.warn('T2I prompt is empty or invalid');
        return null;
    }
    try {
        imageGenerating = true;
        toast.show(i18n.tr('Generating image...'), 'success');
        const response = await fetch('/api/t2i', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: prompt.trim() })
        });
        if (!response.ok) {
            const errorText = await response.text();
            console.error('T2I request failed:', response.status, errorText);
            return null;
        }
        const data = await response.json();
        if (data && data.image_url) {
            return data.image_url;
        } else {
            console.error('T2I response missing image_url');
            return null;
        }
    } catch (error) {
        console.error('Error in sendT2I:', error);
        return null;
    } finally {
        imageGenerating = false;
    }
};

const getComfyUIConfig = async () => {
    try {
        const response = await fetch('/api/config/comfyui', {
            method: 'GET'
        });
        if (!response.ok) {
            console.error('Failed to fetch ComfyUI config:', response.status);
            return null;
        }
        const config = await response.json();
        return config;
    } catch (error) {
        console.error('Error in getComfyUIConfig:', error);
        return null;
    }
};
