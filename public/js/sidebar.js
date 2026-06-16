class StickySidebar {
  constructor(options = {}) {
    this._opt = { icon: 'shapes', side: 'right', buttons: [], ...options };
    this._state = {
      expanded: false,
      dragging: false,
      click: false,
      wasSnapped: false,
      side: this._opt.side,
      dragStartX: 0,
      dragStartY: 0,
      offsetX: 0,
      offsetY: 0,
      snapTop: 0,
      snapped: true,
      lastX: 0,
      lastY: 0
    };
    this._el = null;
    this._toggle = null;
    this._panel = null;
    this._grid = null;
    this._init();
  }

  addButton(cfg) {
    if (this._grid) {
      this._grid.appendChild(this._createButtonEl(cfg));
    }
    return this;
  }

  expand() {
    if (this._state.expanded) return;
    this._state.expanded = true;
    this._panel.classList.add('visible');
    this._el.classList.add('expanded');
    this._applySnapPosition();
    this._checkBounds();
  }

  collapse() {
    if (!this._state.expanded) return;
    this._state.expanded = false;
    this._panel.classList.remove('visible');
    this._el.classList.remove('expanded');
    this._applySnapPosition();
  }

  toggle() {
    if (this._state.expanded) this.collapse();
    else this.expand();
  }

  _init() {
    this._injectStyles();
    this._createDOM();
    this._bindEvents();
    this._state.snapTop = Math.round(window.innerHeight * 0.67 - 22);
    this._snap(this._state.side, false);
  }

  _injectStyles() {
    if (document.getElementById('ss-styles')) return;
    const s = document.createElement('style');
    s.id = 'ss-styles';
    s.textContent = `
.sticky-sidebar{position:fixed;z-index:9999;display:inline-flex;align-items:stretch;user-select:none}
.sticky-sidebar *{box-sizing:border-box}
.sidebar-toggle{width:44px;min-width:44px;height:44px;display:flex;align-items:center;justify-content:center;background:#000;fill:#fff;color:#fff;cursor:grab;z-index:2;position:relative;opacity:.2;transition:border-radius .2s,transform .2s,box-shadow .2s,opacity .2s}
.sidebar-toggle:hover{opacity:1}
.sidebar-toggle svg{width:22px;height:22px;min-width:22px}
.sidebar-toggle:active{cursor:grabbing}
.sidebar-toggle.ball{border-radius:50% !important;box-shadow:0 3px 12px rgba(0,0,0,.25);cursor:grabbing;opacity:1}
.sidebar-panel{display:none;width:auto;background:var(--bg-modal,#fff);color:var(--color-modal,#000);border:1px solid var(--border-input-textarea,#ddd);overflow-y:auto;-ms-overflow-style:none;scrollbar-width:none;max-height:400px}
.sidebar-panel::-webkit-scrollbar{display:none}
.sidebar-panel.visible{display:flex}
.sidebar-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;padding:10px}
.sidebar-btn{width:60px;height:60px;border-radius:12px;display:flex;align-items:center;justify-content:center;background:var(--bg-button,#fafafa);fill:var(--fill-icon,#555);color:var(--color-button,#555);border:none;cursor:pointer;transition:background .1s;margin:0;padding:0}
.sidebar-btn:hover{background:var(--bg-button-hover,#f5f5f5)}
.sidebar-btn svg{width:28px;height:28px;min-width:28px}
.sticky-sidebar.expanded .sidebar-toggle{display:none}
.sticky-sidebar.snap-right{left:auto;flex-direction:row-reverse}
.sticky-sidebar.snap-left{right:auto;flex-direction:row}
.snap-right .sidebar-toggle{border-radius:50% 0 0 50%}
.snap-left .sidebar-toggle{border-radius:0 50% 50% 0}
.snap-right .sidebar-panel{border-radius:12px 0 0 12px;border-right:none}
.snap-left .sidebar-panel{border-radius:0 12px 12px 0;border-left:none}
@keyframes ss-snap{0%{transform:scale(1)}15%{transform:scaleX(1.2) scaleY(.85)}40%{transform:scaleX(.92) scaleY(1.06)}65%{transform:scaleX(1.04) scaleY(.98)}100%{transform:scale(1)}}
@keyframes ss-ring{0%{box-shadow:0 0 0 0 rgba(0,0,0,.12)}40%{box-shadow:0 0 0 10px rgba(0,0,0,0)}100%{box-shadow:0 0 0 0 rgba(0,0,0,0)}}
.sidebar-toggle.snap-animate{animation:ss-snap .4s cubic-bezier(.34,1.56,.64,1),ss-ring .45s ease-out}
[data-theme=dark] .sidebar-toggle{background:#2a2a2a;fill:#ccc;color:#ccc}
`;
    document.head.appendChild(s);
  }

  _createDOM() {
    this._el = document.createElement('div');
    this._el.className = 'sticky-sidebar';

    this._toggle = document.createElement('div');
    this._toggle.className = 'sidebar-toggle';
    this._toggle.innerHTML = '<svg><use xlink:href="/img/icons.svg?v=200#icon-' + this._opt.icon + '"></use></svg>';
    this._toggle.draggable = false;
    this._el.appendChild(this._toggle);

    this._panel = document.createElement('div');
    this._panel.className = 'sidebar-panel';
    this._grid = document.createElement('div');
    this._grid.className = 'sidebar-grid';
    this._panel.appendChild(this._grid);
    this._el.appendChild(this._panel);

    document.body.appendChild(this._el);
    (this._opt.buttons || []).forEach(b => this.addButton(b));
  }

  _createButtonEl(cfg) {
    const btn = document.createElement('button');
    btn.className = 'sidebar-btn';
    btn.innerHTML = '<svg><use xlink:href="/img/icons.svg?v=200#icon-' + cfg.icon + '"></use></svg>';
    if (cfg.title) {
      btn.title = cfg.title;
      btn.setAttribute('tr-title', '');
    }
    btn.addEventListener('click', e => {
      e.stopPropagation();
      if (cfg.onClick) cfg.onClick(e);
    });
    return btn;
  }

  _bindEvents() {
    this._toggle.addEventListener('mousedown', e => {
      if (e.button !== 0) return;
      this._startDrag(e.clientX, e.clientY);
      e.preventDefault();
    });
    document.addEventListener('mousemove', e => {
      if (!this._state.dragging) return;
      this._continueDrag(e.clientX, e.clientY);
    });
    document.addEventListener('mouseup', e => {
      if (!this._state.dragging) return;
      this._endDrag(e.clientX, e.clientY);
    });

    this._toggle.addEventListener('touchstart', e => {
      const t = e.touches[0];
      this._startDrag(t.clientX, t.clientY);
      if (e.cancelable) e.preventDefault();
    }, { passive: false });
    document.addEventListener('touchmove', e => {
      if (!this._state.dragging) return;
      const t = e.touches[0];
      this._continueDrag(t.clientX, t.clientY);
      if (e.cancelable) e.preventDefault();
    }, { passive: false });
    document.addEventListener('touchend', () => {
      if (!this._state.dragging) return;
      this._endDrag(this._state.lastX, this._state.lastY);
    });

    document.addEventListener('click', e => {
      if (this._state.expanded && !this._el.contains(e.target)) {
        this.collapse();
      }
    });

    window.addEventListener('resize', () => this._checkBounds());
  }

  _startDrag(cx, cy) {
    if (this._state.expanded) this.collapse();
    this._state.dragging = true;
    this._state.click = true;
    this._state.wasSnapped = this._state.snapped;
    this._state.dragStartX = cx;
    this._state.dragStartY = cy;
    this._state.offsetX = 0;
    this._state.offsetY = 0;
    this._state.lastX = cx;
    this._state.lastY = cy;
  }

  _continueDrag(cx, cy) {
    const dx = cx - this._state.dragStartX;
    const dy = cy - this._state.dragStartY;

    if (this._state.click && (Math.abs(dx) > 5 || Math.abs(dy) > 5)) {
      this._state.click = false;
      this._detach();
      this._toggle.classList.add('ball');
      const tr = this._toggle.getBoundingClientRect();
      this._state.offsetX = cx - tr.left;
      this._state.offsetY = cy - tr.top;
      this._el.style.left = (cx - this._state.offsetX) + 'px';
      this._el.style.top = (cy - this._state.offsetY) + 'px';
    }

    if (!this._state.click) {
      this._el.style.left = (cx - this._state.offsetX) + 'px';
      this._el.style.top = (cy - this._state.offsetY) + 'px';
    }
    this._state.lastX = cx;
    this._state.lastY = cy;
  }

  _endDrag(cx, cy) {
    this._state.dragging = false;
    this._toggle.classList.remove('ball');

    if (this._state.click) {
      if (this._state.wasSnapped) {
        this.expand();
      } else {
        const side = cx < window.innerWidth / 2 ? 'left' : 'right';
        const r = this._el.getBoundingClientRect();
        this._state.snapTop = Math.round(r.top);
        this._snap(side, false);
        this.expand();
      }
    } else {
      const r = this._el.getBoundingClientRect();
      this._state.snapTop = Math.round(r.top);
      const side = cx < window.innerWidth / 2 ? 'left' : 'right';
      this._snap(side, true);
    }
  }

  _detach() {
    if (!this._state.snapped) return;
    const r = this._el.getBoundingClientRect();
    this._el.style.left = r.left + 'px';
    this._el.style.top = r.top + 'px';
    this._el.style.right = 'auto';
    this._el.className = 'sticky-sidebar';
    this._state.snapped = false;
  }

  _snap(side, animate) {
    this._state.side = side;
    this._state.snapped = true;
    this._el.className = 'sticky-sidebar';
    this._el.style.left = 'auto';
    this._el.style.right = 'auto';
    this._el.style.top = this._state.snapTop + 'px';
    this._el.classList.add('snap-' + side);
    if (this._state.expanded) this._el.classList.add('expanded');
    this._applySnapPosition();
    this._checkBounds();
    if (animate) {
      this._toggle.classList.add('snap-animate');
      setTimeout(() => this._toggle.classList.remove('snap-animate'), 500);
    }
  }

  _applySnapPosition() {
    const p = this._state.side === 'right' ? 'right' : 'left';
    this._el.style[p] = '0';
    this._el.style.top = this._state.snapTop + 'px';
  }

  _checkBounds() {
    const r = this._el.getBoundingClientRect();
    if (r.top < 0) {
      this._state.snapTop = 10;
      this._el.style.top = '10px';
    }
    const maxTop = this._state.expanded
      ? window.innerHeight - r.height - 10
      : window.innerHeight - 44;
    if (this._state.snapTop > maxTop) {
      this._state.snapTop = Math.max(10, maxTop);
      this._el.style.top = this._state.snapTop + 'px';
    }
  }
}
