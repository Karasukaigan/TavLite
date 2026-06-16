(function (global) {
    'use strict';

    let tooltipEl = null;
    let locked = false;

    const hideTooltip = () => {
        if (tooltipEl) {
            tooltipEl.remove();
            tooltipEl = null;
        }
        locked = false;
    };

    const showTooltip = (trigger) => {
        hideTooltip();

        const text = global.i18n.tr(trigger.getAttribute('data-tooltip'));
        if (!text) return;

        tooltipEl = document.createElement('div');
        tooltipEl.className = 'tooltip-box';
        tooltipEl.innerHTML = text;
        document.body.appendChild(tooltipEl);

        const rect = trigger.getBoundingClientRect();
        const tooltipRect = tooltipEl.getBoundingClientRect();
        let top = rect.bottom + 6;
        let left = rect.left + rect.width / 2 - tooltipRect.width / 2;
        if (left < 4) left = 4;
        if (left + tooltipRect.width > window.innerWidth - 4) {
            left = window.innerWidth - tooltipRect.width - 4;
        }
        tooltipEl.style.top = top + 'px';
        tooltipEl.style.left = left + 'px';
    };

    const initTooltips = () => {
        document.querySelectorAll('[data-tooltip]').forEach(el => {
            el.addEventListener('mouseenter', () => {
                if (!locked) showTooltip(el);
            });
            el.addEventListener('mouseleave', () => {
                if (!locked) hideTooltip();
            });
            el.addEventListener('click', (e) => {
                e.stopPropagation();
                if (tooltipEl && locked) {
                    hideTooltip();
                } else {
                    showTooltip(el);
                    locked = true;
                }
            });
        });

        document.addEventListener('click', () => {
            if (locked) hideTooltip();
        }, true);
    };

    global.initTooltips = initTooltips;
    global.hideTooltip = hideTooltip;

    if (typeof module !== 'undefined' && module.exports) {
        module.exports = { initTooltips, hideTooltip };
    }
})(typeof window !== 'undefined' ? window : globalThis || this);