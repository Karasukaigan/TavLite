const fetchWithToast = async (url, options = {}, successMsg, errorMsg) => {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || response.statusText);
        }
        const data = await response.json().catch(() => ({}));
        if (successMsg) toast.show(i18n.tr(successMsg), 'success');
        return data;
    } catch (error) {
        const msg = errorMsg ? i18n.tr(errorMsg) : i18n.tr("Operation failed");
        toast.show(`${msg}: ${i18n.tr(error.message)}`, 'error');
        throw error;
    }
};

const getConfig = async () =>
    fetchWithToast(`/api/config?t=${Date.now()}`, {}, null, "Failed to get current settings");

const updateJoystickCheckboxState = async (mode) => {
    const c = document.getElementById('joystickControl');
    if (mode === 'serial') {
        c.disabled = false;
        try { c.checked = (await (await fetch('/api/devices/joystick')).json()).running; }
        catch { c.checked = false; }
    } else {
        c.disabled = true;
        c.checked = false;
        try { await fetch('/api/devices/joystick/stop', { method: 'POST' }); } catch { }
    }
};

const toggleModeFields = (mode) => {
    const udpGroup = document.getElementById('udpUrl').closest('.form-group');
    const serialGroup = document.getElementById('serialDevice').closest('.form-group');
    const intifaceGroup = document.getElementById('intiface-group');
    const intifaceDeviceGroup = document.getElementById('intiface-device-group');
    const handyGroup = document.getElementById('handy-group');
    const joystickGroup = document.getElementById('joystick-group');
    const motionRangeGroup = document.getElementById('motion-range-group');
    const testParamsGroup = document.getElementById('test-params-group');
    udpGroup.style.display = mode === 'udp' ? 'flex' : 'none';
    serialGroup.style.display = mode === 'serial' ? 'flex' : 'none';
    intifaceGroup.style.display = mode === 'intiface' ? 'flex' : 'none';
    handyGroup.style.display = mode === 'handy' ? 'flex' : 'none';
    joystickGroup.style.display = mode === 'serial' ? 'flex' : 'none';
    if (mode !== 'intiface') {
        intifaceDeviceGroup.style.display = 'none';
    } else {
        intifaceDeviceGroup.style.display = intifaceDeviceGroup.dataset.connected === 'true' ? 'flex' : 'none';
    }
    const isDisabled = mode === 'disabled';
    motionRangeGroup.style.display = isDisabled ? 'none' : 'flex';
    testParamsGroup.style.display = isDisabled ? 'none' : 'flex';
};

const toggleAdvancedMode = (enabled) => {
    const els = document.querySelectorAll('.advanced');
    if (enabled) {
        els.forEach(el => el.style.display = '');
    } else {
        els.forEach(el => el.style.display = 'none');
        document.getElementById('temperature').value = '1.0';
        document.getElementById('thinkingEffort').value = '';
    }
};

const generateCardName = () => {
    const d = new Date();
    return `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}${String(d.getHours()).padStart(2, '0')}${String(d.getMinutes()).padStart(2, '0')}${String(d.getSeconds()).padStart(2, '0')}${String(d.getMilliseconds()).padStart(3, '0')}`;
};

const isValidStructure = (obj) => {
    if (typeof obj !== 'object' || !obj || !Object.keys(obj).length) return false;
    return Object.values(obj).every(item =>
        item && typeof item === 'object' &&
        typeof item.system_prompt === 'string' &&
        (item.context === undefined || (Array.isArray(item.context) && item.context.length &&
            item.context.every(ctx =>
                ctx && typeof ctx === 'object' &&
                (ctx.role === 'assistant' || ctx.role === 'user') &&
                typeof ctx.content === 'string' && ctx.content.trim()
            )
        )) &&
        (item.messages === undefined || (Array.isArray(item.messages) &&
            item.messages.every(m => typeof m === 'string' && m.trim())
        )) &&
        (item.concept_art === undefined || typeof item.concept_art === 'string') &&
        (item.tags === undefined || (Array.isArray(item.tags) &&
            item.tags.every(t => typeof t === 'string')
        ))
    );
};

document.addEventListener('DOMContentLoaded', async () => {
    await i18n.init(i18n.getBrowserLanguage());
    toast.init();
    if (typeof initTooltips === 'function') initTooltips();
    const savedLang = localStorage.getItem('language') || 'browser';
    const currentLang = savedLang === 'browser' ? i18n.getBrowserLanguage() : savedLang;
    const osrBtn = document.querySelector('.tab-button[data-tab="osr"]');
    if (osrBtn) osrBtn.style.display = (currentLang === 'zh') ? 'none' : '';
});

function activateTab(tabId) {
    const btn = document.querySelector(`.tab-button[data-tab="${tabId}"]`);
    const content = document.getElementById(`${tabId}-tab`);
    if (!btn || !content) return;
    document.querySelectorAll('.tab-button,.tab-content').forEach(e => e.classList.remove('active'));
    btn.classList.add('active');
    content.classList.add('active');
}

document.querySelectorAll('.tab-button').forEach(b => b.addEventListener('click', function () {
    const t = this.getAttribute('data-tab');
    activateTab(t);
    location.hash = t;
}));

document.getElementById('view-api').addEventListener('click', function (e) {
    e.preventDefault();
    document.querySelectorAll('.tab-button,.tab-content').forEach(el => el.classList.remove('active'));
    document.getElementById('api-tab').classList.add('active');
    location.hash = 'api';
});

document.getElementById('modeSelect').addEventListener('change', function () {
    toggleModeFields(this.value);
    updateJoystickCheckboxState(this.value);
    if (this.value === 'intiface') {
        loadIntifaceConfig();
    }
});

async function loadSettings() {
    try {
        const settings = await getConfig();
        if (settings.udp_url) document.getElementById('udpUrl').value = settings.udp_url;
        if (settings.mode) {
            document.getElementById('modeSelect').value = settings.mode;
            toggleModeFields(settings.mode);
            await updateJoystickCheckboxState(settings.mode);
        }
        if (settings.motion_range) {
            document.getElementById('motionRange').value = String(settings.motion_range);
        }
        if (settings.handy_connection_key) {
            document.getElementById('handyConnectionKey').value = settings.handy_connection_key;
        }
        if (settings.handy_api_version) {
            document.getElementById('handyApiVersion').value = settings.handy_api_version;
        }
        if (settings.handy_min_depth !== undefined) {
            document.getElementById('handyMinDepth').value = settings.handy_min_depth;
        }
        if (settings.handy_max_depth !== undefined) {
            document.getElementById('handyMaxDepth').value = settings.handy_max_depth;
        }
        setHandyStatus(settings.handy_connected);
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

async function loadIntifaceConfig() {
    try {
        const res = await fetch('/api/config/intiface?t=' + Date.now());
        const config = await res.json();
        document.getElementById('intifaceWsUrl').value = config.ws_url || '';
        const btn = document.getElementById('intifaceConnectBtn');
        const deviceGroup = document.getElementById('intiface-device-group');
        if (config.connected) {
            setBtnConnected(btn, true);
            setIntifaceStatus(true);
            deviceGroup.dataset.connected = 'true';
            populateIntifaceDevices(config.devices, config.device_index, config.feature_index);
            if (document.getElementById('modeSelect').value === 'intiface') {
                deviceGroup.style.display = 'flex';
            }
        } else {
            setBtnConnected(btn, false);
            setIntifaceStatus(false);
            deviceGroup.dataset.connected = 'false';
            deviceGroup.style.display = 'none';
        }
    } catch (e) {
        console.error('Failed to load intiface config:', e);
    }
}

function populateIntifaceDevices(devices, savedDeviceIndex, savedFeatureIndex) {
    const select = document.getElementById('intifaceDevice');
    select.innerHTML = '';
    if (!devices || devices.length === 0) {
        const opt = document.createElement('option');
        opt.value = '';
        opt.textContent = i18n.tr('No devices available');
        select.appendChild(opt);
        return;
    }
    const blank = document.createElement('option');
    blank.value = '';
    blank.textContent = '--';
    select.appendChild(blank);
    select.value = '';

    devices.forEach(d => {
        const opt = document.createElement('option');
        opt.value = JSON.stringify({ device_index: d.device_index, feature_index: d.feature_index, step_count: d.step_count, device_name: d.device_name });
        opt.textContent = `${d.device_name} - ${d.feature_name || 'Position'} (idx:${d.device_index}, feat:${d.feature_index})`;
        select.appendChild(opt);
        if (d.device_index === savedDeviceIndex && d.feature_index === savedFeatureIndex) {
            select.value = opt.value;
        }
    });
}

async function loadSerialDevices() {
    try {
        const response = await fetch('/api/devices/serial');
        const data = await response.json();
        const select = document.getElementById('serialDevice');
        data.serial_ports.forEach(port => {
            const option = document.createElement('option');
            option.value = port.device;
            option.textContent = `${port.device} - ${port.description}`;
            select.appendChild(option);
        });
        const settings = await getConfig();
        if (settings.serial_device) select.value = settings.serial_device;
    } catch (error) {
        toast.show(`${i18n.tr("Failed to retrieve serial port device list")}: ${i18n.tr(error.message)}`, 'error');
    }
}

async function loadLlmConfig() {
    try {
        const response = await fetch('/api/config/llm?t=' + Date.now());
        const config = await response.json();

        if (config.base_url) document.getElementById('baseUrl').value = config.base_url;
        if (config.api_key) document.getElementById('apiKey').value = config.api_key;
        if (config.model) document.getElementById('model').value = config.model;
        if (config.temperature !== undefined) {
            document.getElementById('temperature').value = config.temperature;
        }
        if (config.reasoning_effort !== undefined) {
            document.getElementById('thinkingEffort').value = config.reasoning_effort;
        }
    } catch (error) {
        console.error('Failed to load LLM config:', error);
    }
}

async function loadComfyUiConfig() {
    try {
        const response = await fetch('/api/config/comfyui?t=' + Date.now());
        const config = await response.json();
        if (config.url) document.getElementById('comfyUrl').value = config.url;
        const aspectValue = (config.aspect_ratio || 'portrait').toLowerCase();
        document.getElementById('aspectRatioSelect').value = aspectValue;
        const typeValue = (config.type || '').toLowerCase();
        document.getElementById('comfyTypeSelect').value = ['sdxl', 'zit', 'anima'].includes(typeValue) ? typeValue : 'disabled';
        if (config.diffusion) document.getElementById('comfyDiffusion').value = config.diffusion;
        if (config.clip) document.getElementById('comfyClip').value = config.clip;
        if (config.vae) document.getElementById('comfyVae').value = config.vae;
    } catch (error) {
        console.error('Failed to load ComfyUI config:', error);
    }
}

document.getElementById('joystickControl').addEventListener('change', async function () {
    try {
        if (this.checked) {
            await fetchWithToast('/api/devices/joystick/start', { method: 'POST' },
                'Joystick control started', 'Failed to start joystick control');
        } else {
            await fetchWithToast('/api/devices/joystick/stop', { method: 'POST' },
                'Joystick control stopped', '');
        }
    } catch (error) {
        this.checked = !this.checked;
    }
});

document.getElementById('settingsForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    const mode = document.getElementById('modeSelect').value;
    const udpUrl = document.getElementById('udpUrl').value.trim();
    const serialDevice = document.getElementById('serialDevice').value;
    const intifaceWsUrl = document.getElementById('intifaceWsUrl').value.trim();
    const motionRange = document.getElementById('motionRange').value;
    const handyConnectionKey = document.getElementById('handyConnectionKey')?.value?.trim();
    const handyApiVersion = document.getElementById('handyApiVersion')?.value;
    const params = new URLSearchParams();
    params.append('m', mode);
    if (udpUrl) params.append('u', udpUrl);
    if (serialDevice) params.append('s', serialDevice);
    if (intifaceWsUrl) params.append('iw', intifaceWsUrl);
    params.append('mr', motionRange);
    if (handyConnectionKey) params.append('hck', handyConnectionKey);
    if (handyApiVersion) params.append('hav', handyApiVersion);
    const handyMinDepth = document.getElementById('handyMinDepth')?.value;
    const handyMaxDepth = document.getElementById('handyMaxDepth')?.value;
    if (handyMinDepth !== undefined && handyMinDepth !== '') params.append('hmd', handyMinDepth);
    if (handyMaxDepth !== undefined && handyMaxDepth !== '') params.append('hxd', handyMaxDepth);
    try {
        await fetchWithToast(
            `/api/config?${params.toString()}`, { method: 'POST' },
            'Settings saved successfully', 'Failed to save settings');
        await updateJoystickCheckboxState(mode);
    } catch (error) { }
});

function setBtnBusy(btn, busy) {
    const spinner = btn.querySelector('.btn-spinner');
    const text = btn.querySelector('.btn-text');
    if (busy) {
        spinner.style.display = 'inline-block';
        text.style.display = 'none';
        btn.disabled = true;
    } else {
        spinner.style.display = 'none';
        text.style.display = '';
        btn.disabled = false;
    }
}

function setBtnConnected(btn, connected) {
    btn.querySelector('.btn-text').textContent = i18n.tr(connected ? 'Disconnect' : 'Connect');
    btn.classList.toggle('connected', connected);
}

function setIntifaceStatus(connected) {
    const el = document.getElementById('intiface-status');
    if (!el) return;
    el.className = 'status-dot ' + (connected ? 'status-connected' : 'status-disconnected');
    el.title = connected ? 'Connected' : 'Disconnected';
}

function setHandyStatus(connected) {
    const el = document.getElementById('handy-status');
    if (!el) return;
    el.className = 'status-dot ' + (connected ? 'status-connected' : 'status-disconnected');
    el.title = connected ? 'Connected' : 'Disconnected';
}

document.getElementById('intifaceDevice').addEventListener('change', async function () {
    if (!this.value) return;
    try {
        const parsed = JSON.parse(this.value);
        await fetch('/api/config/intiface/select', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_index: parsed.device_index,
                feature_index: parsed.feature_index,
                step_count: parsed.step_count,
                device_name: parsed.device_name,
            })
        });
    } catch (e) {}
});

document.getElementById('test-play-btn').addEventListener('click', async function () {
    const text = document.getElementById('test-params').value.trim();
    if (!text) { toast.show(i18n.tr('Please enter test parameters'), 'error'); return; }
    let params;
    try { params = JSON.parse(text); } catch (e) { toast.show(i18n.tr('Invalid JSON'), 'error'); return; }
    this.disabled = true;
    try {
        const res = await fetch('/api/script/custom', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || 'Test failed');
        toast.show(i18n.tr('Test playback started'), 'success');
    } catch (e) {
        toast.show(`${i18n.tr("Operation failed")}: ${e.message}`, 'error');
    } finally {
        this.disabled = false;
    }
});

document.getElementById('intifaceConnectBtn').addEventListener('click', async function () {
    const wsUrl = document.getElementById('intifaceWsUrl').value.trim() || 'ws://127.0.0.1:12345';
    const deviceGroup = document.getElementById('intiface-device-group');

    if (this.classList.contains('connected')) {
        try {
            await fetch('/api/config/intiface/disconnect', { method: 'POST' });
        } catch (e) {}
        setBtnConnected(this, false);
        setIntifaceStatus(false);
        deviceGroup.dataset.connected = 'false';
        deviceGroup.style.display = 'none';
        return;
    }

    setBtnBusy(this, true);
    try {
        const res = await fetch('/api/config/intiface/connect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ws_url: wsUrl })
        });
        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            const detail = errData.detail;
            const msg = Array.isArray(detail) ? detail.map(d => d.msg || d).join('; ') : (detail || 'Connection failed');
            throw new Error(msg);
        }
        const data = await res.json();
        setBtnConnected(this, true);
        setIntifaceStatus(true);
        deviceGroup.dataset.connected = 'true';
        if (document.getElementById('modeSelect').value === 'intiface') {
            deviceGroup.style.display = 'flex';
        }
        populateIntifaceDevices(data.devices || []);
    } catch (error) {
        toast.show(`${i18n.tr("Connection failed")}: ${error.message}`, 'error');
        setBtnConnected(this, false);
    } finally {
        setBtnBusy(this, false);
    }
});

document.getElementById('handyTestBtn').addEventListener('click', async function () {
    const connectionKey = document.getElementById('handyConnectionKey').value.trim();
    const apiVersion = document.getElementById('handyApiVersion').value;
    if (!connectionKey) {
        toast.show(i18n.tr('Connection key is required'), 'error');
        return;
    }
    this.disabled = true;
    try {
        const res = await fetch('/api/config/handy/test', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ connection_key: connectionKey, api_version: apiVersion })
        });
        const data = await res.json();
        setHandyStatus(data.connected);
        if (data.connected) {
            toast.show(i18n.tr('Handy connected'), 'success');
        } else {
            toast.show(i18n.tr('Handy not connected'), 'error');
        }
    } catch (e) {
        toast.show(`${i18n.tr("Connection failed")}: ${e.message}`, 'error');
        setHandyStatus(false);
    } finally {
        this.disabled = false;
    }
});

document.getElementById('clear-t2i-cache')?.addEventListener('click', async function (e) {
    e.preventDefault();
    await fetchWithToast('/api/t2i/cache', {
        method: 'DELETE'
    }, 'Image cache cleared successfully', 'Failed to clear cache');
});

document.getElementById('clear-chat-cache')?.addEventListener('click', async function (e) {
    e.preventDefault();
    await fetchWithToast('/api/chat/cache', {
        method: 'DELETE'
    }, 'Chat cache cleared successfully', 'Failed to clear cache');
});

document.getElementById('llmConfigForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    const baseUrl = document.getElementById('baseUrl').value.trim();
    const apiKey = document.getElementById('apiKey').value.trim();
    const model = document.getElementById('model').value.trim();
    const temperature = parseFloat(document.getElementById('temperature').value);
    const reasoningEffort = document.getElementById('thinkingEffort').value;
    const requestBody = {};
    if (baseUrl) requestBody.base_url = baseUrl;
    if (apiKey) requestBody.api_key = apiKey;
    if (model) requestBody.model = model;
    requestBody.temperature = temperature;
    requestBody.reasoning_effort = reasoningEffort;
    await fetchWithToast('/api/config/llm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
    }, 'Settings saved successfully', 'Failed to save settings');
});

document.getElementById('comfyuiConfigForm')?.addEventListener('submit', async function (e) {
    e.preventDefault();
    const url = document.getElementById('comfyUrl').value.trim();
    const aspectRatio = document.getElementById('aspectRatioSelect').value || 'portrait';
    const diffusion = document.getElementById('comfyDiffusion').value.trim();
    const clip = document.getElementById('comfyClip').value.trim();
    const vae = document.getElementById('comfyVae').value.trim();
    const type = document.getElementById('comfyTypeSelect').value || '';
    const requestBody = { url, type, diffusion, clip, vae, aspect_ratio: aspectRatio };
    await fetchWithToast('/api/config/comfyui', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody)
    }, 'Settings saved successfully', 'Failed to save ComfyUI settings');
});

function toggleModelFields() {
    const type = document.getElementById('comfyTypeSelect').value;
    const isDisabled = type === 'disabled';
    const isSdxl = type === 'sdxl';
    const modelGroups = document.querySelectorAll('.model-group, .clip-vae-group');
    modelGroups.forEach(group => {
        if (isDisabled) {
            group.style.display = 'none';
        } else if (isSdxl && group.classList.contains('clip-vae-group')) {
            group.style.display = 'none';
        } else {
            group.style.display = 'flex';
        }
    });
    const urlGroup = document.querySelector('.comfyui-url-group');
    const ratioGroup = document.querySelector('.aspect-ratio-group');
    if (urlGroup) urlGroup.style.display = isDisabled ? 'none' : 'flex';
    if (ratioGroup) ratioGroup.style.display = isDisabled ? 'none' : 'flex';
}

document.getElementById('comfyTypeSelect').addEventListener('change', function () {
    toggleModelFields();
    updateT2IToolsAvailability();
});

async function loadUserConfig() {
    try {
        const res = await fetch('/api/config/user?t=' + Date.now());
        const config = await res.json().catch(() => ({}));
        document.getElementById('username').value = config.username || '';
        const profileVal = config.profile || '';
        document.getElementById('userProfile').value = profileVal;
        countTokens(profileVal).then(c => { document.getElementById('profile-token-count').textContent = `${c} tokens`; });
    } catch (e) {
        console.error('Failed to load user config:', e);
    }
}

async function loadSystemConfig() {
    try {
        const savedLang = localStorage.getItem('language') || 'browser';
        const langSelect = document.getElementById('languageSelect');
        if (langSelect) langSelect.value = savedLang;

        const advancedMode = localStorage.getItem('advancedMode') === 'true';
        document.getElementById('advancedModeSelect').value = advancedMode ? 'true' : 'false';
        toggleAdvancedMode(advancedMode);

        const res = await fetch('/api/config/user?t=' + Date.now());
        const config = await res.json().catch(() => ({}));
        document.getElementById('startupPageSelect').value = config.startup_page || 'llm';
    } catch (e) {
        console.error('Failed to load system config:', e);
    }
}

document.getElementById('advancedModeSelect').addEventListener('change', function () {
    toggleAdvancedMode(this.value === 'true');
});

document.getElementById('userConfigForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    const username = document.getElementById('username').value.trim();
    const profile = document.getElementById('userProfile').value.trim();
    await fetchWithToast('/api/config/user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, profile })
    }, 'Settings saved successfully', 'Failed to save settings');
});

document.getElementById('systemConfigForm').addEventListener('submit', async function (e) {
    e.preventDefault();
    const startupPage = document.getElementById('startupPageSelect').value;
    const advancedMode = document.getElementById('advancedModeSelect').value === 'true';
    const newLang = document.getElementById('languageSelect').value;
    const oldLang = localStorage.getItem('language') || 'browser';
    await fetchWithToast('/api/config/user', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ startup_page: startupPage })
    }, 'Settings saved successfully', 'Failed to save settings');
    localStorage.setItem('advancedMode', advancedMode ? 'true' : 'false');
    if (newLang !== oldLang) {
        localStorage.setItem('language', newLang);
        location.reload();
    }
});

document.addEventListener('click', async (e) => {
    if (e.target.closest('.card-header') &&
        !e.target.closest('.card-edit,.card-delete,.card-delete-confirm,.card-export')) {
        const cardItem = e.target.closest('.card-item');
        const name = cardItem.querySelector('.card-name').textContent;
        openEditModal(name);
    }

    if (e.target.closest('.card-edit')) {
        e.stopPropagation();
        modal.alert(i18n.tr('Upgrade to <a href="https://beyondblackwall.com/product/2">TavLite Pro</a> to unlock the advanced editor.'));
    }

    if (e.target.closest('.card-delete')) {
        e.stopPropagation();
        const deleteBtn = e.target.closest('.card-delete');
        const cardItem = deleteBtn.closest('.card-item');
        const header = cardItem.querySelector('.card-header');
        const confirmBtn = header.querySelector('.card-delete-confirm');
        if (deleteBtn.dataset.timerId) clearTimeout(parseInt(deleteBtn.dataset.timerId));
        deleteBtn.style.display = 'none';
        confirmBtn.style.display = '';
        confirmBtn.focus();
        deleteBtn.dataset.timerId = '';
    }

    if (e.target.closest('.card-delete-confirm')) {
        e.stopPropagation();
        const confirmBtn = e.target.closest('.card-delete-confirm');
        if (confirmBtn.disabled) return;
        confirmBtn.disabled = true;
        const cardItem = confirmBtn.closest('.card-item');
        const header = cardItem.querySelector('.card-header');
        const deleteBtn = header.querySelector('.card-delete');
        const name = header.querySelector('.card-name').textContent;
        if (deleteBtn.dataset.timerId) {
            clearTimeout(parseInt(deleteBtn.dataset.timerId));
            deleteBtn.dataset.timerId = '';
        }
        fetchWithToast(`/api/cards/${encodeURIComponent(name)}`, {
            method: 'DELETE'
        }, '', 'Failed to delete card').then(() => {
            cardItem.remove();
            cardDataMap.delete(name);
        }).catch(() => {
            confirmBtn.disabled = false;
        });
    }

    if (e.target.closest('.card-export')) {
        e.stopPropagation();
        const cardItem = e.target.closest('.card-item');
        const header = cardItem.querySelector('.card-header');
        const name = header.querySelector('.card-name').textContent;
        let card = cardDataMap.get(name);
        if (!card || !card.system_prompt) {
            try {
                const response = await fetch('/api/cards/' + encodeURIComponent(name) + '?t=' + Date.now());
                if (response.ok) {
                    const data = await response.json();
                    card = data && data[name];
                    if (card) cardDataMap.set(name, card);
                }
            } catch (e) {}
        }
        if (card) {
            try {
                let exportData = { system_prompt: card.system_prompt || '' };
                if (card.context) exportData.context = card.context;
                if (card.messages) exportData.messages = card.messages;
                if (card.tags) exportData.tags = card.tags;
                if (card.concept_art) {
                    exportData.concept_art = card.concept_art.startsWith('/img/')
                        ? await urlToBase64(card.concept_art)
                        : card.concept_art;
                }
                if (card.images && Object.keys(card.images).length > 0) {
                    exportData.images = {};
                    for (const [key, img] of Object.entries(card.images)) {
                        try {
                            const b64 = img.data && img.data.startsWith('/img/')
                                ? await urlToBase64(img.data)
                                : img.data;
                            exportData.images[key] = { data: b64, description: img.description || '' };
                        } catch (e) {}
                    }
                    if (Object.keys(exportData.images).length === 0) delete exportData.images;
                }
                if (card.html) exportData.html = card.html;
                if (card.updated_at) exportData.updated_at = card.updated_at;
                const blob = new Blob([JSON.stringify({ [name]: exportData }, null, 2)], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `${name}_${Date.now()}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            } catch (error) {
                console.error('Failed to export card:', error);
                toast.show(i18n.tr('Failed to export card'), 'error');
            }
        }
    }

});

document.addEventListener('focusout', (e) => {
    if (e.target.closest('.card-delete-confirm')) {
        const confirmBtn = e.target.closest('.card-delete-confirm');
        const cardItem = confirmBtn.closest('.card-item');
        const header = cardItem.querySelector('.card-header');
        const deleteBtn = header.querySelector('.card-delete');
        if (deleteBtn.dataset.timerId) clearTimeout(parseInt(deleteBtn.dataset.timerId));
        const timerId = setTimeout(() => {
            deleteBtn.style.display = '';
            confirmBtn.style.display = 'none';
            deleteBtn.dataset.timerId = '';
        }, 500);
        deleteBtn.dataset.timerId = timerId.toString();
    }
});

document.addEventListener('focusin', (e) => {
    if (e.target.closest('.card-delete-confirm')) {
        const confirmBtn = e.target.closest('.card-delete-confirm');
        const cardItem = confirmBtn.closest('.card-item');
        const header = cardItem.querySelector('.card-header');
        const deleteBtn = header.querySelector('.card-delete');
        if (deleteBtn.dataset.timerId) {
            clearTimeout(parseInt(deleteBtn.dataset.timerId));
            deleteBtn.dataset.timerId = '';
        }
    }
});

const nameInput = document.getElementById('card-name-input');
const newCardButton = document.getElementById('new-card-button');
newCardButton.addEventListener('click', async () => {
    const name = nameInput.value.trim() || generateCardName();
    nameInput.value = '';
    await fetchWithToast('/api/cards', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, prompt: '', content: '' })
    }, '', 'Failed to create card');
    try {
        const response = await fetch('/api/cards?t=' + Date.now());
        const cards = await response.json();
        renderCards(cards);
        openEditModal(name);
    } catch (error) {
        console.error('Failed to reload cards:', error);
    }
});

const importCardButton = document.getElementById('import-card-button');
const importFileInput = document.createElement('input');
importFileInput.type = 'file';
importFileInput.accept = '.json,.png';
importFileInput.multiple = true;
importFileInput.style.display = 'none';
document.body.appendChild(importFileInput);

importCardButton.addEventListener('click', () => {
    importFileInput.click();
});

async function processCardFiles(files) {
    let successCount = 0, failCount = 0;
    for (const file of files) {
        try {
            const formData = new FormData();
            formData.append('file', file);
            const res = await fetch('/api/cards/import/json', { method: 'POST', body: formData });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || res.statusText);
            }
            const result = await res.json();
            successCount += result.success || 0;
            if (result.errors && result.errors.length) failCount += result.errors.length;
        } catch (error) {
            failCount++;
        }
    }
    importFileInput.value = '';
    try {
        const response = await fetch('/api/cards?t=' + Date.now());
        const cards = await response.json();
        renderCards(cards);
    } catch (error) {}
    if (successCount > 0) {
        toast.show(`${i18n.tr("Imported")} ${successCount} ${i18n.tr("card(s)")}`, 'success');
    }
}

async function processPNGFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch('/api/cards/import/png', { method: 'POST', body: formData });
    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || response.statusText);
    }
    return await response.json();
}

importFileInput.addEventListener('change', async (event) => {
    if (!event.target.files.length) return;
    const files = Array.from(event.target.files);
    const jsonFiles = files.filter(f => f.name.endsWith('.json'));
    const pngFiles = files.filter(f => f.name.endsWith('.png'));
    let pngOk = 0;
    if (jsonFiles.length) {
        await processCardFiles(jsonFiles);
    }
    for (const file of pngFiles) {
        try {
            await processPNGFile(file);
            pngOk++;
        } catch (e) {}
    }
    if (pngOk > 0) {
        toast.show(`${i18n.tr("Imported")} ${pngOk} PNG ${i18n.tr("card(s)")}`, 'success');
        try {
            const response = await fetch('/api/cards?t=' + Date.now());
            const cards = await response.json();
            renderCards(cards);
        } catch (error) {}
    }
});

const cardsTab = document.getElementById('cards-tab');
cardsTab.addEventListener('dragenter', (e) => {
    e.preventDefault();
    cardsTab.classList.add('drag-over');
});
cardsTab.addEventListener('dragover', (e) => {
    e.preventDefault();
});
cardsTab.addEventListener('dragleave', (e) => {
    if (!cardsTab.contains(e.relatedTarget)) {
        cardsTab.classList.remove('drag-over');
    }
});
cardsTab.addEventListener('drop', async (e) => {
    e.preventDefault();
    cardsTab.classList.remove('drag-over');
    const files = Array.from(e.dataTransfer.files);
    const jsonFiles = files.filter(f => f.name.endsWith('.json'));
    const pngFiles = files.filter(f => f.name.endsWith('.png'));
    let pngOk = 0;
    if (jsonFiles.length) {
        await processCardFiles(jsonFiles);
    }
    for (const file of pngFiles) {
        try {
            await processPNGFile(file);
            pngOk++;
        } catch (e) {}
    }
    if (pngOk > 0) {
        toast.show(`${i18n.tr("Imported")} ${pngOk} PNG ${i18n.tr("card(s)")}`, 'success');
    }
    if (pngOk > 0) {
        try {
            const response = await fetch('/api/cards?t=' + Date.now());
            const cards = await response.json();
            renderCards(cards);
        } catch (error) {}
    }
});

let cardDataMap = new Map();

function renderCards(cards) {
    const cardsList = document.getElementById('cards-list');
    cardsList.innerHTML = '';
    cardDataMap.clear();

    Object.entries(cards)
        .sort((a, b) => (b[1]?.updated_at || 0) - (a[1]?.updated_at || 0))
        .forEach(([name, card]) => {
        cardDataMap.set(name, card);
        const cardElem = document.createElement('div');
        cardElem.className = 'card-item';
        cardElem.innerHTML = `
<div class="card-header">
    <span class="card-name">${escapeHtml(name)}</span>
    <svg class="card-edit" data-card="${escapeHtml(name)}"><use xlink:href="/img/icons.svg?v=200#icon-edit"></use></svg>
    <svg class="card-export"><use xlink:href="/img/icons.svg?v=200#icon-export"></use></svg>
    <svg class="card-delete" tabindex="0"><use xlink:href="/img/icons.svg?v=200#icon-clear"></use></svg>
    <svg class="card-delete-confirm" tabindex="0" style="display: none;"><use xlink:href="/img/icons.svg?v=200#icon-check"></use></svg>
</div>
        `;
        cardsList.appendChild(cardElem);
    });
    applyCardFilter();
}

function applyCardFilter() {
    const searchTerm = document.getElementById('card-search-input').value.trim().toLowerCase();
    const items = document.querySelectorAll('#cards-list .card-item');
    items.forEach(item => {
        const name = item.querySelector('.card-name').textContent.toLowerCase();
        item.style.display = (!searchTerm || name.includes(searchTerm)) ? '' : 'none';
    });
}

document.getElementById('card-search-input').addEventListener('input', applyCardFilter);





const debouncedProfileTokens = debounce(async function () {
    const count = await countTokens(this.value);
    document.getElementById('profile-token-count').textContent = `${count} tokens`;
}, 300);
document.getElementById('userProfile').addEventListener('input', debouncedProfileTokens);

async function loadAndRenderCards() {
    try {
        const response = await fetch('/api/cards?t=' + Date.now());
        const cards = await response.json();
        renderCards(cards);
    } catch (error) {
        console.error('Failed to load cards:', error);
    }
}

async function initQrCode() {
    try {
        const response = await fetch('/api/host/ip');
        const data = await response.json();
        const ip = data.ip || '127.0.0.1';
        new QRCode(document.getElementById('qr-code'), {
            text: `${location.protocol}//tavlite.local:${location.port}/`,
            width: 200,
            height: 200,
            colorDark: '#000000',
            colorLight: '#ffffff',
            correctLevel: QRCode.CorrectLevel.H
        });
        document.getElementById('qr-url').textContent = `${location.protocol}//tavlite.local:${location.port}/`;
    } catch (error) {
        console.error('Failed to init QR code:', error);
    }
}

async function initApiDocs() {
    try {
        const response = await fetch('/docs/api.md');
        const markdown = await response.text();
        document.getElementById('api-doc-content').innerHTML = marked.parse(markdown);
    } catch (error) {
        console.error('Failed to load API docs:', error);
    }
}


function updateT2IToolsAvailability() {
}

document.getElementById('temperature').addEventListener('change', function () {
    if (this.value !== '') {
        let v = parseFloat(this.value);
        if (isNaN(v)) v = 1.0;
        v = Math.min(2.0, Math.max(0.0, v));
        this.value = v.toFixed(1);
    }
});

document.addEventListener('DOMContentLoaded', async () => {
    if (!await authCheck('/settings')) return;
    await Promise.allSettled([
        loadSettings(),
        loadSerialDevices(),
        loadLlmConfig(),
        loadComfyUiConfig(),
        loadUserConfig(),
        loadSystemConfig(),
        loadIntifaceConfig(),
        initQrCode(),
        initApiDocs(),
        loadAndRenderCards()
    ]);

    toggleModelFields();
    updateT2IToolsAvailability();

    new StickyNotice({
        message: 'Please fill in the LLM settings first when using for the first time.',
        buttonText: 'I understand',
        key: 'settings-first-notice',
        frequency: 'once'
    }).show();

    const hashTab = location.hash.slice(1) || 'llm';
    const hashBtn = document.querySelector(`.tab-button[data-tab="${hashTab}"]`);
    if (hashTab && hashBtn && hashBtn.style.display !== 'none') {
        activateTab(hashTab);
    } else {
        const firstVisible = Array.from(document.querySelectorAll('.tab-button')).find(b => b.style.display !== 'none');
        activateTab(firstVisible ? firstVisible.dataset.tab : 'llm');
    }
});

window.addEventListener('hashchange', () => {
    const h = location.hash.slice(1);
    const btn = document.querySelector(`.tab-button[data-tab="${h}"]`);
    if (h && btn && btn.style.display !== 'none') {
        activateTab(h);
    }
});
