(function (global) {
    'use strict';

    var StickyNotice = function (options) {
        this._opt = {
            message: '',
            buttonText: 'OK',
            key: '',
            frequency: 'always',
            days: 7,
            onAction: null,
            ...options
        };
        this._el = null;
    };

    StickyNotice.prototype._injectStyles = function () {
        if (document.getElementById('sn-styles')) return;
        var s = document.createElement('style');
        s.id = 'sn-styles';
        s.textContent = `
.sticky-notice{position:fixed;bottom:0;left:0;width:100%;z-index:9998;background:#fff;border-top:1px solid #ddd;box-shadow:0 -2px 12px rgba(0,0,0,.1);display:flex;align-items:center;justify-content:center;padding:14px 20px;gap:16px;box-sizing:border-box;transform:translateY(100%);transition:transform .3s ease;font-size:14px;flex-wrap:wrap}
.sticky-notice.show{transform:translateY(0)}
.sticky-notice-message{flex:1;min-width:200px;color:#333;line-height:1.4}
.sticky-notice-btn{flex-shrink:0;padding:8px 20px;font-size:14px;background:#000;color:#fff;border:none;border-radius:8px;cursor:pointer;white-space:nowrap;display:inline-flex;align-items:center;justify-content:center}
.sticky-notice-btn:hover{background:#282828}
[data-theme=dark] .sticky-notice{background:#1e1e1e;border-top-color:#333}
[data-theme=dark] .sticky-notice-message{color:#ccc}
[data-theme=dark] .sticky-notice-btn{background:#333;color:#fff}
[data-theme=dark] .sticky-notice-btn:hover{background:#444}
`;
        document.head.appendChild(s);
    };

    StickyNotice.prototype._shouldShow = function () {
        if (!this._opt.key) return true;
        var key = 'sn_' + this._opt.key;
        var stored = localStorage.getItem(key);
        if (!stored) return true;
        if (this._opt.frequency === 'once') return false;
        if (this._opt.frequency === 'n_days') {
            var ts = parseInt(stored, 10);
            if (isNaN(ts)) return true;
            var now = Date.now();
            var days = Math.max(1, parseInt(this._opt.days, 10) || 7);
            return (now - ts) > days * 24 * 60 * 60 * 1000;
        }
        return true;
    };

    StickyNotice.prototype._markShown = function () {
        if (!this._opt.key) return;
        var key = 'sn_' + this._opt.key;
        if (this._opt.frequency === 'once') {
            localStorage.setItem(key, '1');
        } else if (this._opt.frequency === 'n_days') {
            localStorage.setItem(key, String(Date.now()));
        }
    };

    StickyNotice.prototype.show = function () {
        if (this._el) return;
        if (!this._shouldShow()) return;
        this._injectStyles();
        var self = this;
        this._el = document.createElement('div');
        this._el.className = 'sticky-notice';
        var msg = document.createElement('div');
        msg.className = 'sticky-notice-message';
        msg.innerHTML = global.i18n ? global.i18n.tr(this._opt.message) : this._opt.message;
        this._el.appendChild(msg);
        var btn = document.createElement('button');
        btn.className = 'sticky-notice-btn';
        btn.textContent = global.i18n ? global.i18n.tr(this._opt.buttonText) : this._opt.buttonText;
        btn.addEventListener('click', function () {
            self._markShown();
            if (self._opt.onAction) self._opt.onAction();
            self.hide();
        });
        this._el.appendChild(btn);
        document.body.appendChild(this._el);
        requestAnimationFrame(function () {
            self._el.classList.add('show');
        });
    };

    StickyNotice.prototype.hide = function () {
        if (!this._el) return;
        var self = this;
        this._el.classList.remove('show');
        this._el.addEventListener('transitionend', function () {
            if (self._el && self._el.parentNode) {
                self._el.parentNode.removeChild(self._el);
            }
            self._el = null;
        }, { once: true });
    };

    global.StickyNotice = StickyNotice;
})(typeof window !== 'undefined' ? window : globalThis || this);
