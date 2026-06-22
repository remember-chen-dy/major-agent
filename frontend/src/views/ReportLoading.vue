<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api } from '../api';
import { useAuthStore } from '../stores/auth';
import { useSessionStore } from '../stores/session';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const sessionStore = useSessionStore();

const sessionId = computed(() => route.params.sessionId as string);
const statusText = ref('正在整理测评答案');
const progress = ref(12);
const error = ref('');
let pollTimer: ReturnType<typeof setInterval> | null = null;
let fakeProgressTimer: ReturnType<typeof setInterval> | null = null;

const startFakeProgress = () => {
  stopFakeProgress();
  fakeProgressTimer = setInterval(() => {
    if (progress.value >= 95) return;
    const increment = 0.15 + Math.random() * 0.55;
    progress.value = Math.min(95, parseFloat((progress.value + increment).toFixed(2)));
  }, 500);
};

const stopFakeProgress = () => {
  if (fakeProgressTimer) {
    clearInterval(fakeProgressTimer);
    fakeProgressTimer = null;
  }
};

const steps = [
  { label: '整理测评答案', detail: '汇总你的分数、位次与偏好' },
  { label: '分析成绩定位', detail: '结合最新数据评估院校层次' },
  { label: '匹配专业方向', detail: '根据多维画像筛选适合专业' },
  { label: '生成志愿策略', detail: '综合城市、家庭资源制定方案' },
  { label: '整合完整报告', detail: '润色排版，输出可读报告' },
];

const currentStepIndex = computed(() => {
  if (error.value) return -1;
  return Math.min(steps.length - 1, Math.floor(progress.value / 20));
});

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

const restartAssessment = async () => {
  try {
    await sessionStore.restartAssessment(sessionId.value);
    router.replace('/assessment');
  } catch (err) {
    error.value = '重新测评失败，请稍后重试';
  }
};

const pollResults = async () => {
  if (!sessionId.value) return;

  try {
    const data = await api.getAssessmentResults(sessionId.value);
    if (data.is_complete) {
      stopPolling();
      stopFakeProgress();
      progress.value = 100;
      statusText.value = '报告生成完成';
      setTimeout(() => {
        router.replace(`/report/${sessionId.value}/ready`);
      }, 600);
      return;
    }

    if (data.is_failed) {
      stopPolling();
      stopFakeProgress();
      error.value = '报告生成失败，请返回后重新提交或重新测评';
      return;
    }

    const realProgress = data.report_progress || progress.value;
    progress.value = Math.max(progress.value, Math.min(95, realProgress));
    const stepIndex = Math.min(steps.length - 1, Math.floor(progress.value / 20));
    statusText.value = steps[stepIndex].label;
  } catch {
    statusText.value = '网络暂时不稳定，正在继续尝试...';
  }
};

onMounted(async () => {
  await authStore.login().catch(() => null);
  startFakeProgress();
  await pollResults();
  pollTimer = setInterval(pollResults, 3000);
});

onUnmounted(() => {
  stopPolling();
  stopFakeProgress();
});
</script>

<template>
  <main class="loading-page">
    <div class="ambient-glow" aria-hidden="true" />
    <div class="ambient-glow secondary" aria-hidden="true" />

    <section class="loading-card">
      <div class="card-header">
        <div class="brand-mark">
          <svg class="mark-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        </div>
        <span class="brand-text">AI 志愿规划师</span>
      </div>

      <div class="hero">
        <div class="spinner" aria-hidden="true">
          <div class="ring ring-1" />
          <div class="ring ring-2" />
          <div class="ring ring-3" />
          <div class="core">AI</div>
        </div>

        <p class="eyebrow">{{ error ? '生成异常' : '报告生成中' }}</p>
        <h1>{{ error || statusText }}</h1>
        <p class="subtext">
          {{ error ? '请检查网络后重试，或返回重新测评' : '正在结合你的测评数据、最新院校信息与 AI 模型生成专属志愿规划报告' }}
        </p>
      </div>

      <div class="progress-section">
        <div class="progress-header">
          <span class="progress-label">生成进度</span>
          <span class="progress-value" :class="{ done: progress >= 100 }">{{ Math.round(progress) }}%</span>
        </div>
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: `${progress}%` }">
            <div class="shimmer" />
          </div>
        </div>
      </div>

      <div class="timeline">
        <div
          v-for="(step, index) in steps"
          :key="step.label"
          class="timeline-item"
          :class="{
            active: index === currentStepIndex && !error,
            completed: index < currentStepIndex && !error,
            pending: index > currentStepIndex && !error,
            error: error,
          }"
        >
          <div class="dot">
            <svg v-if="index < currentStepIndex && !error" class="check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          </div>
          <div class="step-body">
            <p class="step-title">{{ step.label }}</p>
            <p class="step-detail">{{ step.detail }}</p>
          </div>
        </div>
      </div>

      <div class="hint">
        <svg class="hint-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10" />
          <path d="M12 16v-4" />
          <path d="M12 8h.01" />
        </svg>
        <p>报告生成约需 30–90 秒，请勿关闭页面，以免中断生成。</p>
      </div>

      <div class="actions" :class="{ error: error }">
        <template v-if="error">
          <button class="primary-btn" @click="pollResults">重试</button>
          <button class="ghost-btn" @click="restartAssessment">重新测评</button>
        </template>
        <button v-else class="ghost-btn" @click="pollResults">刷新状态</button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.loading-page {
  min-height: 100vh;
  min-height: 100dvh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(ellipse at 20% 20%, rgba(31, 111, 235, 0.08) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 80%, rgba(47, 111, 115, 0.08) 0%, transparent 50%),
    linear-gradient(180deg, #faf8f5 0%, #f5f0e8 100%);
  color: #1c1c1e;
}

.ambient-glow {
  position: absolute;
  width: 420px;
  height: 420px;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.45;
  pointer-events: none;
  background: radial-gradient(circle, rgba(31, 111, 235, 0.22) 0%, transparent 70%);
  top: -120px;
  right: -120px;
  animation: float 10s ease-in-out infinite;
}

.ambient-glow.secondary {
  width: 360px;
  height: 360px;
  background: radial-gradient(circle, rgba(47, 111, 115, 0.2) 0%, transparent 70%);
  top: auto;
  right: auto;
  bottom: -100px;
  left: -100px;
  animation-delay: -5s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-16px, 20px); }
}

.loading-card {
  position: relative;
  z-index: 1;
  width: min(100%, 560px);
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(234, 223, 211, 0.8);
  border-radius: 24px;
  padding: 36px;
  box-shadow:
    0 24px 70px rgba(42, 31, 22, 0.08),
    0 1px 0 rgba(255, 255, 255, 0.6) inset;
  backdrop-filter: blur(12px);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 28px;
}

.brand-mark {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  background: linear-gradient(135deg, #1f6feb 0%, #2f6f73 100%);
  display: grid;
  place-items: center;
  color: white;
  box-shadow: 0 6px 16px rgba(31, 111, 235, 0.22);
}

.mark-icon {
  width: 18px;
  height: 18px;
}

.brand-text {
  font-size: 15px;
  font-weight: 800;
  letter-spacing: -0.01em;
  color: #2c2c2e;
}

.hero {
  text-align: center;
}

.spinner {
  position: relative;
  width: 88px;
  height: 88px;
  margin: 0 auto 24px;
}

.ring {
  position: absolute;
  inset: 0;
  border-radius: 50%;
  border: 2px solid transparent;
}

.ring-1 {
  border-top-color: #1f6feb;
  animation: spin 1.4s linear infinite;
}

.ring-2 {
  inset: 10px;
  border-right-color: #2f6f73;
  animation: spin 1.2s linear infinite reverse;
}

.ring-3 {
  inset: 20px;
  border-bottom-color: #c9a84c;
  animation: spin 1s linear infinite;
}

.core {
  position: absolute;
  inset: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #1f6feb 0%, #2f6f73 100%);
  color: white;
  font-size: 13px;
  font-weight: 900;
  display: grid;
  place-items: center;
  box-shadow: 0 8px 24px rgba(31, 111, 235, 0.25);
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #1f6feb;
  background: linear-gradient(135deg, rgba(31, 111, 235, 0.1) 0%, rgba(31, 111, 235, 0.03) 100%);
  border: 1px solid rgba(31, 111, 235, 0.16);
  border-radius: 999px;
  padding: 6px 12px;
  margin: 0 auto 14px;
}

h1 {
  font-size: clamp(26px, 5vw, 34px);
  line-height: 1.2;
  font-weight: 850;
  letter-spacing: -0.02em;
  color: #1a1a1c;
  margin: 0;
}

.subtext {
  max-width: 420px;
  margin: 12px auto 0;
  font-size: 15px;
  line-height: 1.7;
  color: #6b625a;
}

.progress-section {
  margin-top: 32px;
}

.progress-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.progress-label {
  font-size: 13px;
  font-weight: 700;
  color: #6b625a;
}

.progress-value {
  font-size: 14px;
  font-weight: 800;
  color: #1f6feb;
  font-variant-numeric: tabular-nums;
}

.progress-value.done {
  color: #1e8e3e;
}

.progress-track {
  height: 10px;
  border-radius: 999px;
  background: rgba(234, 223, 211, 0.6);
  overflow: hidden;
  position: relative;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #1f6feb 0%, #2f6f73 55%, #1e8e3e 100%);
  background-size: 200% 100%;
  transition: width 0.5s cubic-bezier(0.22, 1, 0.36, 1);
  position: relative;
  box-shadow: 0 2px 8px rgba(31, 111, 235, 0.22);
}

.shimmer {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0) 0%,
    rgba(255, 255, 255, 0.35) 50%,
    rgba(255, 255, 255, 0) 100%
  );
  background-size: 200% 100%;
  animation: shimmer 1.8s infinite;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.timeline {
  margin-top: 28px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.timeline-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 12px 14px;
  border-radius: 14px;
  transition: all 0.35s ease;
}

.timeline-item.active {
  background: rgba(31, 111, 235, 0.06);
  border: 1px solid rgba(31, 111, 235, 0.12);
}

.timeline-item.completed {
  opacity: 0.75;
}

.timeline-item.pending {
  opacity: 0.45;
}

.timeline-item.error {
  opacity: 0.4;
}

.dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 2px;
  display: grid;
  place-items: center;
  border: 2px solid currentColor;
  color: #c5b89f;
  transition: all 0.35s ease;
}

.timeline-item.active .dot {
  color: #1f6feb;
  background: rgba(31, 111, 235, 0.1);
  border-color: #1f6feb;
  box-shadow: 0 0 0 4px rgba(31, 111, 235, 0.1);
}

.timeline-item.completed .dot {
  color: #1e8e3e;
  background: #e6f4ea;
  border-color: #1e8e3e;
}

.check {
  width: 12px;
  height: 12px;
}

.step-body {
  flex: 1;
}

.step-title {
  font-size: 14px;
  font-weight: 750;
  color: #2c2c2e;
  margin: 0;
}

.step-detail {
  font-size: 12px;
  color: #8a7f75;
  margin: 3px 0 0;
  line-height: 1.5;
}

.timeline-item.active .step-title {
  color: #1f6feb;
}

.timeline-item.completed .step-title {
  color: #1e8e3e;
}

.hint {
  margin-top: 24px;
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 14px 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, rgba(201, 168, 76, 0.1) 0%, rgba(201, 168, 76, 0.04) 100%);
  border: 1px solid rgba(201, 168, 76, 0.18);
  color: #7a612e;
}

.hint-icon {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  margin-top: 1px;
  color: #c9a84c;
}

.hint p {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
}

.actions {
  display: flex;
  justify-content: center;
  margin-top: 28px;
}

.actions.error {
  gap: 12px;
}

.primary-btn,
.ghost-btn {
  border: none;
  border-radius: 12px;
  padding: 13px 28px;
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s ease;
}

.primary-btn {
  background: linear-gradient(135deg, #1f6feb 0%, #2f6f73 100%);
  color: white;
  box-shadow: 0 8px 22px rgba(31, 111, 235, 0.28);
}

.primary-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 26px rgba(31, 111, 235, 0.34);
}

.ghost-btn {
  background: rgba(234, 223, 211, 0.5);
  color: #5a5047;
}

.ghost-btn:hover {
  background: rgba(234, 223, 211, 0.8);
}

@media (max-width: 520px) {
  .loading-card {
    padding: 26px 22px;
    border-radius: 20px;
  }

  .spinner {
    width: 76px;
    height: 76px;
  }

  .core {
    inset: 24px;
    font-size: 11px;
  }

  .timeline-item {
    padding: 10px 12px;
  }

  .hint {
    padding: 12px 14px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ambient-glow,
  .ring,
  .shimmer {
    animation: none;
  }
}
</style>
