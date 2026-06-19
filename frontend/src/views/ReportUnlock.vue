<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api } from '../api';
import { useAuthStore } from '../stores/auth';
import { useSessionStore } from '../stores/session';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const sessionStore = useSessionStore();

const sessionId = computed(() => route.params.sessionId as string);
const loading = ref(true);
const error = ref('');
const report = ref<any>(null);
const paying = ref(false);

const valueItems = [
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
      reportData = {
        report_id: 0,
        report_content: data.report || '',
        report_title: '志愿规划报告',
        is_paid: true,
        session_id: sessionId.value,
      };
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

const handlePay = async () => {
  if (!report.value || paying.value) return;

  // 兜底：如果 report_id 为 0（从老会话回退），直接放行查看
  if (!report.value.report_id) {
    router.push(`/report/${sessionId.value}`);
    return;
  }

  paying.value = true;
  try {
    await api.payReport(report.value.report_id);
    report.value.is_paid = true;
    router.replace(`/report/${sessionId.value}`);
  } catch (error) {
    console.error('支付失败:', error);
    alert('支付处理失败，请稍后重试');
  } finally {
    paying.value = false;
  }
};

const goHome = () => {
  router.push({ path: '/', query: { landing: '1' } });
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

onMounted(async () => {
  await loadReport();
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
        <p class="subtext">点击下方按钮支付 3 元即可查看完整报告。报告会直接在页面内展示，手机端也可以完整阅读。</p>
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
          <h2>完整报告需付费解锁</h2>
          <p>包含成绩定位、专业建议、避坑提醒、城市策略和行动清单。</p>

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
            <span class="original-price">¥29.9</span>
            <span class="price">¥3.00</span>
          </div>
          <div class="price-hint">限时特惠 · 一次性解锁，永久查看</div>

          <button class="pay-btn" @click="handlePay" :disabled="paying">
            <span v-if="paying">支付处理中...</span>
            <span v-else>立即解锁完整报告</span>
          </button>
          <div class="secondary-actions">
            <button class="text-link" @click="restartAssessment">重新测评</button>
            <span class="divider">·</span>
            <button class="text-link" @click="goHome">返回首页</button>
          </div>
        </aside>
      </div>
    </section>
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
}
</style>
