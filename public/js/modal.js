(function (global) {
    'use strict';

    var overlay = null;
    var currentResolve = null;

    var createOverlay = function () {
        if (overlay) return;
        overlay = document.createElement('div');
        overlay.className = 'modal-overlay modal-confirm-overlay';
        overlay.addEventListener('click', function (e) {
            if (e.target === overlay) close(null);
        });
        document.body.appendChild(overlay);
    };

    var close = function (result) {
        if (overlay) overlay.classList.remove('show');
        if (currentResolve) {
            var r = currentResolve;
            currentResolve = null;
            r(result);
        }
    };

    var createDialog = function (message, title, opts) {
        createOverlay();
        overlay.innerHTML = '';

        var dialog = document.createElement('div');
        dialog.className = 'modal-dialog-confirm';

        if (title) {
            var header = document.createElement('div');
            header.className = 'modal-header confirm-header';
            var titleEl = document.createElement('div');
            titleEl.className = 'modal-title confirm-title';
            titleEl.textContent = title;
            header.appendChild(titleEl);
            dialog.appendChild(header);
        }

        var body = document.createElement('div');
        body.className = 'modal-body confirm-body';

        var msgEl = document.createElement('div');
        msgEl.className = 'confirm-message';
        msgEl.innerHTML = message;
        body.appendChild(msgEl);

        var inputEl = null;
        if (opts.prompt) {
            inputEl = document.createElement('input');
            inputEl.type = 'text';
            inputEl.className = 'confirm-input';
            if (opts.defaultVal) inputEl.value = opts.defaultVal;
            body.appendChild(inputEl);
            setTimeout(function () { inputEl.focus(); }, 50);
        }

        dialog.appendChild(body);

        var btnRow = document.createElement('div');
        btnRow.className = 'confirm-buttons';

        if (opts.showCancel) {
            var cancelBtn = document.createElement('button');
            cancelBtn.className = 'confirm-btn confirm-btn-cancel';
            cancelBtn.textContent = global.i18n ? global.i18n.tr('Cancel') : 'Cancel';
            cancelBtn.addEventListener('click', function () { close(null); });
            btnRow.appendChild(cancelBtn);
        }

        var okBtn = document.createElement('button');
        okBtn.className = 'confirm-btn confirm-btn-ok';
        okBtn.textContent = global.i18n ? global.i18n.tr('OK') : 'OK';
        okBtn.addEventListener('click', function () {
            if (opts.prompt && inputEl) {
                close(inputEl.value);
            } else {
                close(true);
            }
        });
        btnRow.appendChild(okBtn);

        dialog.appendChild(btnRow);
        overlay.appendChild(dialog);
        overlay.classList.add('show');

        if (inputEl) {
            inputEl.addEventListener('keydown', function (e) {
                if (e.key === 'Enter') okBtn.click();
                if (e.key === 'Escape') cancelBtn.click();
            });
        }
        document.addEventListener('keydown', function escHandler(e) {
            if (e.key === 'Escape') {
                document.removeEventListener('keydown', escHandler);
                close(null);
            }
        });
    };

    var modal = {
        alert: function (message, title) {
            return new Promise(function (resolve) {
                currentResolve = resolve;
                createDialog(message, title, { showCancel: false, prompt: false });
            });
        },
        confirm: function (message, title) {
            return new Promise(function (resolve) {
                currentResolve = resolve;
                createDialog(message, title, { showCancel: true, prompt: false });
            });
        },
        prompt: function (message, defaultVal, title) {
            return new Promise(function (resolve) {
                currentResolve = resolve;
                createDialog(message, title, { showCancel: true, prompt: true, defaultVal: defaultVal || '' });
            });
        }
    };

    global.modal = modal;
})(typeof window !== 'undefined' ? window : globalThis || this);
