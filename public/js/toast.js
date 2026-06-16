(function () {
    var toast = {
        init: function () {
            if (document.getElementById('toast-container')) return;
            var container = document.createElement('div');
            container.id = 'toast-container';
            var style = document.createElement('style');
            style.id = 'toast-style';
            style.textContent = `
#toast-container {
    pointer-events: none;
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    z-index: 9999;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding-top: 10px;
    box-sizing: border-box;
}
.toast-message {
    position: relative;
    width: 80%;
    max-width: 400px;
    margin-bottom: 10px;
    padding: 15px 18px;
    border: 1px solid #ddd;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    font-size: 14px;
    color: #000;
    word-break: break-all;
    background-color: #fff;
    opacity: 0;
    transform: translateY(-100%);
    animation: slideIn 0.2s ease-out forwards;
}
.toast-message.info { border-color: #ddd; }
.toast-message.success { border-color: #ddd; color: #000; }
.toast-message.warn { border-color: #FF9800; color: #FF9800; }
.toast-message.error { border-color: #F44336; color: #F44336; }
@keyframes slideIn {
    from { transform: translateY(-100%); opacity: 0; }
    to { transform: translateY(0); opacity: 1; }
}
@keyframes slideOut {
    from { transform: translateY(0); opacity: 1; }
    to { transform: translateY(-100%); opacity: 0; }
}
.toast-message.slide-out {
    animation: slideOut 0.2s ease-out forwards;
}
      `;
            document.head.appendChild(style);
            document.body.insertBefore(container, document.body.firstChild);
        },

        show: function (message, type = 'info', time = 3000) {
            if (!document.getElementById('toast-container')) this.init();
            var container = document.getElementById('toast-container');
            var toastMsg = document.createElement('div');
            toastMsg.className = 'toast-message ' + type;
            toastMsg.textContent = message;
            container.insertBefore(toastMsg, container.firstChild);
            setTimeout(function () {
                toastMsg.classList.add('slide-out');
                toastMsg.addEventListener('animationend', function () {
                    container.removeChild(toastMsg);
                }, { once: true });
            }, time);
            console.log('[Toast]', message);
        }
    };

    window.toast = toast;
})();