<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api } from '../api';
import { useAuthStore } from '../stores/auth';
import { useSessionStore } from '../stores/session';
import { message } from '../utils/message';
import bilibiliGuideSrc from '../assets/image.png';
import wechatQrSrc from '../assets/count.jpg';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const sessionStore = useSessionStore();

const sessionId = computed(() => route.params.sessionId as string);
const loading = ref(true);
const error = ref('');
const report = ref<any>(null);
const paying = ref(false);
const paymentDialogOpen = ref(false);
const paymentOrder = ref<any>(null);
const paymentStatus = ref<'idle' | 'creating' | 'waiting' | 'success' | 'error'>('idle');
const paymentError = ref('');
let pollTimer: number | null = null;

// 免费通道人工审核
const freeModalOpen = ref(false);
const BILIBILI_GUIDE_SRC = bilibiliGuideSrc;
const WECHAT_QR_SRC = wechatQrSrc;
const REPORT_UNLOCK_PRICE = '¥9.90';

const valueItems = [
  '基于国内顶尖大模型深度分析',
  '成绩定位与院校层次分析',
  '适合专业方向深度推荐',
  '志愿填报避坑清单',
  '城市与院校策略建议',
  '专属行动清单与时间节点',
];

const loadReport = async () => {
  if (!sessionId.value) {
    error.value = '缺少会话 ID';
    loading.value = false;
    return;
  }

  try {
    await authStore.login().catch(() => null);

    // 优先从 reports 表读取；失败时回退到会话结果
    let reportData: any = null;
    if (authStore.userId) {
      try {
        const bySession = await api.getReportBySession(sessionId.value, authStore.userId);
        reportData = bySession.report;
      } catch (e) {
        console.warn('从 reports 表读取失败，尝试会话结果:', e);
      }
    }

    if (!reportData) {
      const data = await api.getAssessmentResults(sessionId.value);
      if (data.is_generating) {
        router.replace(`/report/${sessionId.value}/loading`);
        return;
      }
      if (!data.is_complete) {
        error.value = '报告还没有生成完成，请稍后再试';
        return;
      }
      if (authStore.userId && data.report) {
        const saved = await api.saveReport({
          user_id: authStore.userId,
          session_id: sessionId.value,
          report_title: '志愿规划报告',
          report_content: data.report,
        });
        reportData = {
          report_id: saved.report_id,
          report_content: data.report,
          report_title: saved.report_title || '志愿规划报告',
          is_paid: false,
          session_id: sessionId.value,
          created_at: saved.created_at || new Date().toISOString(),
        };
      } else {
        error.value = '报告支付记录创建失败，请稍后重试';
        return;
      }
    }

    report.value = reportData;

    // 已支付直接进报告页
    if (reportData.is_paid) {
      router.replace(`/report/${sessionId.value}`);
      return;
    }
  } catch {
    error.value = '无法加载报告状态，请检查网络后重试';
  } finally {
    loading.value = false;
  }
};

const reportPreview = computed(() => {
  if (!report.value?.report_content) return '';
  return report.value.report_content
    .split('\n')
    .filter(Boolean)
    .slice(0, 12)
    .join('\n');
});

const paymentFrameUrl = computed(() => {
  if (!paymentOrder.value) return '';
  return paymentOrder.value.pay_url || paymentOrder.value.cashier_url || '';
});

const paymentQrImage = computed(() => {
  const image = paymentOrder.value?.qr_image;
  if (!image) return '';
  if (image.startsWith('data:') || image.startsWith('http://') || image.startsWith('https://')) {
    return image;
  }
  return `data:image/png;base64,${image}`;
});

const paymentOpenUrl = computed(() => {
  if (!paymentOrder.value) return '';
  return paymentOrder.value.pay_url2 || paymentOrder.value.pay_url || paymentOrder.value.cashier_url || '';
});

const closePaymentDialog = () => {
  paymentDialogOpen.value = false;
  paying.value = false;
  stopPaymentPolling();
};

const stopPaymentPolling = () => {
  if (pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
};

const confirmPaymentSuccess = () => {
  paymentStatus.value = 'success';
  report.value.is_paid = true;
  closePaymentDialog();
  router.replace(`/report/${sessionId.value}`);
};

const checkPaymentStatus = async () => {
  if (!report.value?.report_id || !paymentOrder.value?.out_trade_no) return;

  try {
    const data = await api.getReportPaymentStatus(
      report.value.report_id,
      paymentOrder.value.out_trade_no
    );
    if (data.is_paid) {
      confirmPaymentSuccess();
    }
  } catch (error) {
    console.warn('查询支付状态失败:', error);
  }
};

const startPaymentPolling = () => {
  stopPaymentPolling();
  pollTimer = window.setInterval(checkPaymentStatus, 3000);
};

const openPaymentInNewWindow = () => {
  if (!paymentOpenUrl.value) return;
  window.open(paymentOpenUrl.value, '_blank', 'noopener,noreferrer');
};

const retryPayment = () => {
  paying.value = false;
  handlePay();
};

const handlePaymentMessage = (event: MessageEvent) => {
  const data = event.data;
  if (!data || data.type !== 'xpay-return') return;
  if (data.paid && Number(data.reportId) === Number(report.value?.report_id)) {
    confirmPaymentSuccess();
  } else {
    checkPaymentStatus();
  }
};

const handlePay = async () => {
  if (!report.value || paying.value) return;

  // 兜底：如果 report_id 为 0（从老会话回退），直接放行查看
  if (!report.value.report_id) {
    router.push(`/report/${sessionId.value}`);
    return;
  }

  paying.value = true;
  paymentStatus.value = 'creating';
  paymentError.value = '';
  paymentOrder.value = null;
  paymentDialogOpen.value = true;
  try {
    const order = await api.payReport(report.value.report_id, 'alipay');
    if (order.is_paid || order.paid) {
      confirmPaymentSuccess();
      return;
    }

    paymentOrder.value = order;
    paymentStatus.value = 'waiting';
    startPaymentPolling();
  } catch (error) {
    console.error('支付失败:', error);
    paymentStatus.value = 'error';
    paymentError.value = error instanceof Error ? error.message : '支付处理失败，请稍后重试';
    paying.value = false;
  }
};

const goHome = () => {
  router.push({ path: '/', query: { landing: '1' } });
};

// 临时测试入口：绕过支付直接查看报告
const skipPaymentForTest = () => {
  router.push(`/report/${sessionId.value}?test=1`);
};

const goReportLibrary = () => {
  router.push('/assessment?reportLibrary=1');
};

const restartAssessment = async () => {
  if (!sessionId.value) return;
  loading.value = true;
  error.value = '';
  try {
    await sessionStore.restartAssessment(sessionId.value);
    router.replace('/assessment');
  } catch {
    error.value = '重新测评失败，请稍后重试';
    loading.value = false;
  }
};

// 优先使用 session_id，精确控制解锁范围
const freeUnlockCommand = computed(() => sessionId.value || authStore.userId || '');

const copyUnlockCommand = async () => {
  const text = freeUnlockCommand.value;
  if (!text) {
    message.warning('暂时没有可复制的指令，请稍后重试');
    return;
  }

  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.setAttribute('readonly', 'true');
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand('copy');
      document.body.removeChild(textarea);
    }
    message.success('复制成功');
  } catch {
    message.error('复制失败，请重新点击按钮');
  }
};

// 打开免费通道弹窗
const openFreeModal = () => {
  freeModalOpen.value = true;
};

// 关闭免费通道弹窗
const closeFreeModal = () => {
  freeModalOpen.value = false;
};

onMounted(async () => {
  window.addEventListener('message', handlePaymentMessage);
  await loadReport();
});

onBeforeUnmount(() => {
  window.removeEventListener('message', handlePaymentMessage);
  stopPaymentPolling();
});
</script>

<template>
  <main class="ready-page">
    <section class="ready-shell">
      <div class="hero">
        <p class="eyebrow">
          <span class="dot" />
          报告已生成
        </p>
        <h1>
          <span class="title-line">你的志愿规划报告</span>
          <span class="title-highlight">已经准备好了</span>
        </h1>
        <p class="subtext">点击下方按钮使用支付宝支付 9.9 元即可查看完整报告。报告会直接在页面内展示，手机端也可以完整阅读。</p>
      </div>

      <div v-if="loading" class="state-card">正在确认报告状态...</div>
      <div v-else-if="error" class="state-card error">
        <p>{{ error }}</p>
        <button @click="loadReport">重试</button>
      </div>
      <div v-else class="ready-grid">
        <article class="preview-card">
          <pre>{{ reportPreview || '报告内容已生成，支付后即可查看完整内容。' }}</pre>
          <div class="fade"></div>
        </article>

        <aside class="action-card">
          <div class="lock">🔒</div>
          <h2>方式一：极速通道（推荐）</h2>
          <p>无需等待，直接支付 <strong>9.9元</strong>，输入信息立即生成报告。</p>

          <ul class="value-list">
            <li v-for="item in valueItems" :key="item">
              <span class="check">✓</span>
              {{ item }}
            </li>
          </ul>

          <div class="social-proof">
            <span class="spark">✦</span>
            已有 12,580 位考生解锁完整报告
          </div>

          <div class="price-row">
            <span class="original-price">¥14.9</span>
            <span class="price">{{ REPORT_UNLOCK_PRICE }}</span>
          </div>
          <div class="price-hint" >支付宝扫码支付 · 一次性解锁，永久查看</div>
          <div class="refund-hint" >本产品属于虚拟服务/数字商品，其特殊性在于一经发出即可被获取，故无法适用退货退款流程。</div>

          <button class="pay-btn" @click="handlePay" :disabled="paying">
            <span v-if="paying">正在等待支付宝支付...</span>
            <span v-else>支付宝支付解锁完整报告</span>
          </button>
          <!-- <div class="free-channel-summary">
            <strong>方式二：免费通道（需人工审核）</strong>
            <span>B站一键三连 + 添加微信 + 发送截图，1小时内人工审核解锁。</span>
          </div> -->
          <button class="ghost-btn group-entry-btn" @click="openFreeModal">
            免费查看报告
          </button>
          <div class="secondary-actions">
            <button class="text-link" @click="restartAssessment">重新测评</button>
            <span class="divider">·</span>
            <button class="text-link" @click="goHome">返回首页</button>
          </div>

          <!-- <button class="test-btn" @click="skipPaymentForTest">
            [测试] 跳过支付直接看报告
          </button> -->
        </aside>
      </div>
    </section>

    <div v-if="paymentDialogOpen" class="payment-overlay" @click.self="closePaymentDialog">
      <section class="payment-dialog" role="dialog" aria-modal="true" aria-labelledby="payment-title">
        <button class="dialog-close" type="button" aria-label="关闭支付弹框" @click="closePaymentDialog">×</button>
        <div class="payment-head">
          <span class="alipay-badge">支付宝</span>
          <h2 id="payment-title">扫码支付 {{ REPORT_UNLOCK_PRICE }}</h2>
          <p>支付成功后会自动打开完整报告。</p>
        </div>

        <div v-if="paymentStatus === 'creating'" class="payment-state">正在创建支付宝订单...</div>
        <div v-else-if="paymentStatus === 'error'" class="payment-state error">
          <p>{{ paymentError }}</p>
          <button class="retry-btn" type="button" @click="retryPayment">重新发起支付</button>
        </div>
        <div v-else class="payment-body">
          <div v-if="paymentQrImage" class="qr-box">
            <img :src="paymentQrImage" alt="支付宝支付二维码" />
          </div>
          <iframe
            v-else-if="paymentFrameUrl"
            class="payment-frame"
            :src="paymentFrameUrl"
            title="支付宝支付"
          ></iframe>
          <div v-else class="payment-state error">暂时无法获取支付二维码，请稍后重试。</div>

          <div class="payment-meta">
            <p class="save-tip">手机端可长按保存二维码图片，再打开支付宝扫码支付。</p>
            <p class="refund-tip">虚拟产品，支付完成后不支持退款。</p>
            <p>订单号：{{ paymentOrder?.out_trade_no }}</p>
            <p v-if="paymentOrder?.gateway_error" class="gateway-note">{{ paymentOrder.gateway_error }}</p>
          </div>

          <div class="dialog-actions">
            <button type="button" class="open-pay-btn" @click="openPaymentInNewWindow">打开支付宝收银台</button>
            <button type="button" class="check-btn" @click="checkPaymentStatus">我已完成支付</button>
          </div>
        </div>
      </section>
    </div>

    <!-- 免费通道人工审核弹窗 -->
    <div v-if="freeModalOpen" class="payment-overlay group-overlay" @click.self="closeFreeModal">
      <section class="payment-dialog group-dialog" role="dialog" aria-modal="true" aria-labelledby="free-title">
        <button class="dialog-close" type="button" aria-label="关闭免费通道弹窗" @click="closeFreeModal">×</button>
        <div class="payment-head">
          <span class="group-badge">免费通道</span>
          <h2 id="free-title">方式二：免费通道（需人工审核）</h2>
          <p>B站一键三连 + 添加微信 + 发送截图，1小时内人工审核解锁。</p>
        </div>

        <div class="free-steps">
          <section class="free-step">
            <div class="step-index">1</div>
            <div class="step-content">
              <h3>复制解锁指令</h3>
              <p>点击按钮复制专属指令，稍后和截图一起发给我。</p>
              <button type="button" class="copy-command-btn" @click="copyUnlockCommand">
                复制指令
              </button>
            </div>
          </section>

          <section class="free-step">
            <div class="step-index">2</div>
            <div class="step-content">
              <h3>去B站完成一键三连</h3>
              <p>按图示在B站搜索 <strong>rn攻城狮</strong> 账号，对图片中的视频一键三连，并保存截图。</p>
              <div class="guide-image video-guide">
                <img :src="BILIBILI_GUIDE_SRC" alt="B站搜索 rn攻城狮账号指引" />
              </div>
            </div>
          </section>

          <section class="free-step">
            <div class="step-index">3</div>
            <div class="step-content">
              <h3>添加微信发送资料</h3>
              <p>扫码加我微信，把刚才复制的内容和一键三连截图一并发给我，可以免费解锁报告。</p>
              <div class="guide-image wechat-guide">
                <img :src="WECHAT_QR_SRC" alt="微信二维码" />
              </div>
            </div>
          </section>
        </div>
      </section>
    </div>
  </main>
</template>

<style scoped>
.ready-page {
  min-height: 100vh;
  min-height: 100dvh;
  background: #f7f3ed;
  color: #1f2328;
  padding: 16px;
}
.ready-shell {
  max-width: 980px;
  margin: 0 auto;
}
.back-btn {
  border: none;
  background: transparent;
  color: #1f6feb;
  font-weight: 700;
  padding: 6px 0;
  cursor: pointer;
}
.hero {
  padding: 10px 0 18px;
}
.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  font-weight: 800;
  color: #1f6feb;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  background: linear-gradient(135deg, rgba(31, 111, 235, 0.12) 0%, rgba(31, 111, 235, 0.04) 100%);
  border: 1px solid rgba(31, 111, 235, 0.18);
  border-radius: 999px;
  padding: 7px 14px;
  box-shadow: 0 4px 12px rgba(31, 111, 235, 0.08);
}
.eyebrow .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1f6feb 0%, #4b8ff7 100%);
  box-shadow: 0 0 0 3px rgba(31, 111, 235, 0.18);
}
h1 {
  max-width: 720px;
  margin-top: 14px;
  font-size: clamp(32px, 6.5vw, 56px);
  line-height: 1.12;
  font-weight: 900;
  letter-spacing: -0.02em;
}
.title-line {
  display: block;
  color: #1f2328;
}
.title-highlight {
  display: block;
  background: linear-gradient(135deg, #1f6feb 0%, #4b8ff7 100%);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.subtext {
  max-width: 620px;
  margin-top: 14px;
  color: #62584f;
  line-height: 1.7;
}
.ready-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(280px, 0.75fr);
  gap: 18px;
  align-items: start;
}
.preview-card,
.action-card,
.state-card {
  background: #fff;
  border: 1px solid #eadfd3;
  border-radius: 18px;
  box-shadow: 0 18px 50px rgba(38, 29, 20, 0.08);
}
.preview-card {
  position: relative;
  min-height: 360px;
  max-height: 520px;
  overflow: hidden;
}
.preview-card pre {
  margin: 0;
  padding: 26px;
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.8;
  color: #4e463f;
  font-family: inherit;
  font-size: 15px;
}
.fade {
  position: absolute;
  inset: auto 0 0;
  height: 140px;
  background: linear-gradient(to bottom, rgba(255,255,255,0), #fff);
}
.action-card {
  padding: 24px;
  text-align: center;
}
.lock {
  width: 50px;
  height: 50px;
  border-radius: 14px;
  background: #f2ede7;
  display: grid;
  place-items: center;
  font-size: 26px;
  margin: 0 auto;
}
.action-card h2 {
  margin-top: 16px;
  font-size: 22px;
  font-weight: 850;
}
.action-card > p {
  margin-top: 10px;
  line-height: 1.65;
  color: #62584f;
}
.value-list {
  list-style: none;
  margin: 16px 0 0;
  padding: 0;
  text-align: left;
}
.value-list li {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 7px 0;
  font-size: 14px;
  color: #4e463f;
  border-bottom: 1px solid rgba(234, 223, 211, 0.6);
}
.value-list li:last-child {
  border-bottom: none;
}
.value-list .check {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #e6f4ea;
  color: #1e8e3e;
  font-size: 10px;
  font-weight: 900;
  display: grid;
  place-items: center;
  margin-top: 1px;
}
.social-proof {
  margin-top: 14px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #8e6a4b;
  background: rgba(140, 106, 75, 0.08);
  padding: 6px 12px;
  border-radius: 999px;
}
.social-proof .spark {
  color: #f5a623;
}
.price-row {
  margin-top: 18px;
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 10px;
}
.original-price {
  font-size: 16px;
  color: #8e8e93;
  text-decoration: line-through;
}
.price {
  font-size: 34px;
  font-weight: 900;
  color: #1f2328;
}
.price-hint {
  margin-top: 4px;
  font-size: 12px;
  color: #8e8e93;
}
.refund-hint {
  margin-top: 6px;
  font-size: 11px;
  line-height: 1.5;
  color: #a47d61;
}
.free-channel-summary {
  margin-top: 14px;
  padding: 12px;
  border: 1px solid rgba(30, 142, 62, 0.18);
  border-radius: 12px;
  background: #f2fbf5;
  text-align: left;
}
.free-channel-summary strong,
.free-channel-summary span {
  display: block;
}
.free-channel-summary strong {
  color: #176b31;
  font-size: 14px;
  font-weight: 850;
}
.free-channel-summary span {
  margin-top: 5px;
  color: #4f6355;
  font-size: 12px;
  line-height: 1.55;
}
.pay-btn,
.ghost-btn,
.state-card button {
  width: 100%;
  border: none;
  border-radius: 12px;
  padding: 13px 16px;
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
}
.pay-btn {
  margin-top: 18px;
  background: #1f6feb;
  color: #fff;
}
.pay-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.ghost-btn {
  margin-top: 10px;
  background: #f2ede7;
  color: #3d352e;
}
.test-btn {
  width: 100%;
  margin-top: 12px;
  border: 1px dashed #c9a84c;
  border-radius: 10px;
  padding: 10px 14px;
  background: rgba(201, 168, 76, 0.08);
  color: #8a6d2e;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}
.test-btn:hover {
  background: rgba(201, 168, 76, 0.16);
  color: #6b521e;
}
.secondary-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid rgba(234, 223, 211, 0.8);
}
.text-link {
  border: none;
  background: transparent;
  color: #8e6a4b;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: all 0.2s ease;
}
.text-link:hover {
  color: #1f6feb;
  background: rgba(31, 111, 235, 0.06);
}
.divider {
  color: #d6c9bc;
  font-weight: 700;
}
.state-card {
  padding: 24px;
  color: #62584f;
}
.state-card.error {
  color: #b42318;
}
.state-card button {
  max-width: 180px;
  margin-top: 14px;
  background: #1f6feb;
  color: white;
}
.payment-overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: grid;
  place-items: center;
  padding: 18px;
  background: rgba(31, 35, 40, 0.48);
  backdrop-filter: blur(4px);
}
.payment-dialog {
  position: relative;
  width: min(440px, 100%);
  max-height: calc(100vh - 36px);
  overflow: auto;
  background: #fff;
  border: 1px solid #eadfd3;
  border-radius: 18px;
  box-shadow: 0 24px 80px rgba(19, 28, 40, 0.28);
  padding: 24px;
}
.dialog-close {
  position: absolute;
  top: 12px;
  right: 12px;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 50%;
  background: #f2ede7;
  color: #3d352e;
  font-size: 22px;
  line-height: 1;
  cursor: pointer;
}
.payment-head {
  text-align: center;
  padding: 6px 24px 16px;
}
.alipay-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  height: 28px;
  border-radius: 999px;
  background: #e8f3ff;
  color: #1677ff;
  font-size: 13px;
  font-weight: 900;
}
.payment-head h2 {
  margin-top: 12px;
  font-size: 24px;
  font-weight: 900;
  color: #1f2328;
}
.payment-head p {
  margin-top: 8px;
  color: #62584f;
  font-size: 14px;
}
.payment-state {
  min-height: 220px;
  display: grid;
  place-items: center;
  text-align: center;
  color: #62584f;
  line-height: 1.7;
}
.payment-state.error {
  color: #b42318;
}
.retry-btn,
.open-pay-btn,
.check-btn {
  border: none;
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 14px;
  font-weight: 800;
  cursor: pointer;
}
.retry-btn,
.open-pay-btn {
  background: #1677ff;
  color: #fff;
}
.qr-box {
  width: min(280px, 100%);
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  margin: 0 auto;
  border: 1px solid #eadfd3;
  border-radius: 16px;
  background: #fff;
  padding: 16px;
}
.qr-box img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.payment-frame {
  display: block;
  width: 100%;
  height: 430px;
  border: 1px solid #eadfd3;
  border-radius: 14px;
  background: #fff;
}
.payment-meta {
  margin-top: 14px;
  color: #8e8e93;
  font-size: 12px;
  text-align: center;
  word-break: break-all;
}
.payment-meta p {
  margin: 4px 0;
}
.save-tip {
  color: #3d352e;
  font-size: 13px;
  font-weight: 700;
}
.refund-tip {
  color: #a47d61;
  font-size: 11px;
}
.gateway-note {
  color: #8e6a4b;
}
.dialog-actions {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 16px;
}
.check-btn {
  background: #f2ede7;
  color: #3d352e;
}
.group-entry-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  margin-top: 10px;
}
.group-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  height: 28px;
  border-radius: 999px;
  background: #e6f4ea;
  color: #1e8e3e;
  font-size: 13px;
  font-weight: 900;
}
.group-dialog {
  width: min(680px, 100%);
}
.free-steps {
  display: grid;
  gap: 14px;
  padding-bottom: 4px;
}
.free-step {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr);
  gap: 12px;
  padding: 14px;
  border: 1px solid #eadfd3;
  border-radius: 14px;
  background: #fffdfb;
}
.step-index {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: #1f6feb;
  color: #fff;
  font-size: 15px;
  font-weight: 900;
}
.step-content h3 {
  margin: 4px 0 6px;
  color: #1f2328;
  font-size: 16px;
  font-weight: 850;
}
.step-content p {
  margin: 0;
  color: #62584f;
  font-size: 14px;
  line-height: 1.65;
}
.copy-command-btn {
  margin-top: 12px;
  border: none;
  border-radius: 12px;
  padding: 11px 16px;
  background: #1677ff;
  color: #fff;
  font-size: 14px;
  font-weight: 850;
  cursor: pointer;
}
.guide-image {
  margin-top: 12px;
  overflow: hidden;
  border: 1px solid #eadfd3;
  border-radius: 14px;
  background: #f7f3ed;
}
.guide-image img {
  display: block;
  width: 100%;
  height: auto;
}
.wechat-guide {
  width: min(260px, 100%);
  margin-left: auto;
  margin-right: auto;
  padding: 10px;
  background: #fff;
}

@media (max-width: 760px) {
  .ready-page {
    padding: 16px;
  }
  .ready-grid {
    grid-template-columns: 1fr;
  }
  .preview-card {
    min-height: 260px;
    max-height: 360px;
  }
  .preview-card pre {
    padding: 20px;
    font-size: 14px;
  }
  .action-card {
    padding: 20px;
  }
  .payment-dialog {
    padding: 20px;
  }
  .payment-frame {
    height: 360px;
  }
  .dialog-actions {
    grid-template-columns: 1fr;
  }
  .free-step {
    grid-template-columns: 30px minmax(0, 1fr);
    padding: 12px;
  }
  .step-index {
    width: 30px;
    height: 30px;
  }
}
</style>
