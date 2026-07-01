type MessageType = 'success' | 'error' | 'warning' | 'info';

interface MessageOptions {
  type?: MessageType;
  duration?: number;
}

const CONTAINER_ID = '__app_message_container__';

function getContainer(): HTMLElement {
  let container = document.getElementById(CONTAINER_ID);
  if (!container) {
    container = document.createElement('div');
    container.id = CONTAINER_ID;
    container.style.cssText =
      'position:fixed;top:24px;left:50%;transform:translateX(-50%);z-index:99999;display:flex;flex-direction:column;align-items:center;gap:10px;pointer-events:none;';
    document.body.appendChild(container);
  }
  return container;
}

const TYPE_STYLES: Record<MessageType, { bg: string; color: string; icon: string }> = {
  success: { bg: '#e6f4ea', color: '#1e8e3e', icon: '✓' },
  error: { bg: '#fde8e8', color: '#b42318', icon: '✕' },
  warning: { bg: '#fff7e6', color: '#b45309', icon: '!' },
  info: { bg: '#e8f3ff', color: '#1677ff', icon: 'i' },
};

function showMessage(content: string, options: MessageOptions = {}): void {
  const { type = 'success', duration = 2500 } = options;
  const container = getContainer();
  const style = TYPE_STYLES[type];

  const el = document.createElement('div');
  el.style.cssText = `
    display:flex;align-items:center;gap:8px;
    padding:10px 20px;border-radius:10px;
    background:${style.bg};color:${style.color};
    font-size:14px;font-weight:700;
    box-shadow:0 6px 24px rgba(0,0,0,0.1);
    pointer-events:auto;
    opacity:0;transform:translateY(-12px);
    transition:opacity 0.3s ease,transform 0.3s ease;
  `;
  el.innerHTML = `<span style="font-size:16px;font-weight:900;">${style.icon}</span><span>${content}</span>`;
  container.appendChild(el);

  // 触发动画
  requestAnimationFrame(() => {
    el.style.opacity = '1';
    el.style.transform = 'translateY(0)';
  });

  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(-12px)';
    el.addEventListener('transitionend', () => {
      el.remove();
      // 容器为空时移除
      if (container.children.length === 0) {
        container.remove();
      }
    });
  }, duration);
}

export const message = {
  success: (content: string, duration?: number) => showMessage(content, { type: 'success', duration }),
  error: (content: string, duration?: number) => showMessage(content, { type: 'error', duration }),
  warning: (content: string, duration?: number) => showMessage(content, { type: 'warning', duration }),
  info: (content: string, duration?: number) => showMessage(content, { type: 'info', duration }),
};
