// i18n.js
(function (global) {
    'use strict';

    const i18n = {
        translations: {},

        /**
         * Get user's browser current language
         */
        getBrowserLanguage() {
            const lang = navigator.language || navigator.userLanguage;
            return lang.split('-')[0];
        },

        /**
         * Assign element content to tr attribute value
         */
        setTr() {
            document.querySelectorAll('[tr]').forEach(el => {
                let textContent = el.textContent?.trim() || '';
                if (textContent) el.setAttribute('tr', textContent);
            });
            document.querySelectorAll('[tr-title]').forEach(el => {
                if (el.hasAttribute('title')) el.setAttribute('tr-title', el.getAttribute('title'));
            });
            document.querySelectorAll('[tr-input]').forEach(el => {
                if (el.hasAttribute('placeholder')) el.setAttribute('tr-input', el.getAttribute('placeholder'));
            });
        },

        /**
         * Set element content to tr attribute value
         */
        applyTr() {
            document.querySelectorAll('[tr]').forEach(el => {
                const trValue = el.getAttribute('tr')?.trim();
                if (trValue) el.textContent = trValue;
            });
            document.querySelectorAll('[tr-title]').forEach(el => {
                const trValue = el.getAttribute('tr-title')?.trim();
                if (trValue) el.setAttribute('title', trValue);
            });
            document.querySelectorAll('[tr-input]').forEach(el => {
                const trValue = el.getAttribute('tr-input')?.trim();
                if (trValue) el.setAttribute('placeholder', trValue);
            });
        },

        /**
         * Load translation file
         */
        load(url) {
            if (!url || typeof url !== 'string') return Promise.reject(new Error('Invalid URL provided to i18n.load()'));
            return fetch(url)
                .then(response => {
                    if (!response.ok) throw new Error(`Failed to load translations: ${response.status} ${response.statusText}`);
                    return response.json();
                })
                .then(data => {
                    if (typeof data !== 'object' || data === null) throw new Error('Translation data must be a valid JSON object');
                    this.translations = data;
                })
                .catch(error => {
                    console.error('i18n.load() error:', error);
                    throw error;
                });
        },

        /**
         * Apply translations
         */
        apply() {
            if (!this.translations || Object.keys(this.translations).length === 0) return;
            document.querySelectorAll('[tr]').forEach(el => {
                const originalText = el.getAttribute('tr')?.trim() || '';
                if (!originalText) return;
                const translated = this.tr(originalText);
                if (translated !== originalText) el.textContent = translated;
            });
            document.querySelectorAll('[tr-title]').forEach(el => {
                const originalText = el.getAttribute('tr-title')?.trim() || '';
                if (!originalText) return;
                const translated = this.tr(originalText);
                if (translated !== originalText) el.setAttribute('title', translated);
            });
            document.querySelectorAll('[tr-input]').forEach(el => {
                const originalText = el.getAttribute('tr-input')?.trim() || '';
                if (!originalText) return;
                const translated = this.tr(originalText);
                if (translated !== originalText) el.setAttribute('placeholder', translated);
            });
        },

        /**
         * Translate single text
         */
        tr(key) {
            if (typeof key !== 'string') return String(key || '');
            return this.translations[key?.trim()] || key;
        },

        /**
         * Initialize i18n
         */
        async init(lang = "en") {
            const saved = localStorage.getItem('language');
            if (saved && saved !== 'browser') {
                lang = saved;
            }
            if (lang !== "en") {
                try {
                    this.setTr();
                    await this.load(`/json/i18n/${lang}.json?t=${Date.now()}`);
                    this.apply();
                } catch (e) {
                    console.error(e);
                }
            }
        }
    };

    global.i18n = i18n;

    if (typeof module !== 'undefined' && module.exports) module.exports = i18n;
    if (typeof define === 'function' && define.amd) define(() => i18n);
})(typeof window !== 'undefined' ? window : globalThis || this);