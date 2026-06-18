<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { api } from '../api';
import { useAuthStore } from '../stores/auth';

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const sessionId = computed(() => route.params.sessionId as string);
const statusText = ref('正在整理测评答案...');
const progress = ref(12);
const error = ref('');
let pollTimer: ReturnType<typeof setInterval> | null = null;
let fakeProgressTimer: ReturnType<typeof setInterval> | null = null;

const startFakeProgress = () => {
  stopFakeProgress();
  fakeProgressTimer = setInterval(() => {
    if (progress.value >= 95) return;
    const increment = 0.2 + Math.random() * 0.6;
    progress.value = Math.min(95, parseFloat((progress.value + increment).toFixed(2)));
  }, 400);
};

const stopFakeProgress = () => {
  if (fakeProgressTimer) {
    clearInterval(fakeProgressTimer);
    fakeProgressTimer = null;
  }
};

const steps = [
  '正在整理测评答案...',
  '正在分析成绩与位次...',
  '正在匹配院校与专业方向...',
  '正在生成个性化志愿规划...',
  '正在整理完整报告内容...',
];

const stopPolling = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
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
      router.replace(`/report/${sessionId.value}/ready`);
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
    const stepIndex = Math.min(steps.length - 1, Math.floor(progress.value / 22));
    statusText.value = steps[stepIndex];
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
  <main class="report-flow">
    <section class="loading-panel">
      <div class="loading-mark">
        <span></span>
        <span></span>
        <span></span>
      </div>

      <p class="eyebrow">报告生成中</p>
      <h1>正在生成你的志愿规划报告</h1>
      <p class="subtext">这一步可能需要几分钟,请不要退出页面，否则报告生成可能会失败。</p>

      <div class="progress-wrap">
        <div class="progress-bar" :style="{ width: `${progress}%` }"></div>
      </div>
      <p class="status">{{ error || statusText }}</p>

      <div class="actions">
        <button class="primary-btn" @click="pollResults">刷新状态</button>
      </div>
    </section>
  </main>
</template>

<style scoped>
.report-flow {
  min-height: 100vh;
  min-height: 100dvh;
  background: #faf7f2;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  color: #1c1c1e;
}
.loading-panel {
  width: min(100%, 520px);
  background: white;
  border: 1px solid #eee2d6;
  border-radius: 18px;
  padding: 28px;
  box-shadow: 0 18px 60px rgba(42, 31, 22, 0.08);
}
.loading-mark {
  width: 54px;
  height: 54px;
  border-radius: 16px;
  background: #1f6feb;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
}
.loading-mark span {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: white;
  animation: bounce 1.1s infinite ease-in-out;
}
.loading-mark span:nth-child(2) { animation-delay: 0.15s; }
.loading-mark span:nth-child(3) { animation-delay: 0.3s; }
.eyebrow {
  margin-top: 24px;
  font-size: 13px;
  font-weight: 700;
  color: #1f6feb;
}
h1 {
  margin-top: 8px;
  font-size: 28px;
  line-height: 1.2;
  font-weight: 800;
}
.subtext {
  margin-top: 12px;
  font-size: 15px;
  line-height: 1.7;
  color: #6b625a;
}
.progress-wrap {
  height: 10px;
  border-radius: 999px;
  background: #f0ebe5;
  overflow: hidden;
  margin-top: 26px;
}
.progress-bar {
  height: 100%;
  border-radius: inherit;
  background: #1f6feb;
  transition: width 0.35s ease;
}
.status {
  min-height: 22px;
  margin-top: 12px;
  font-size: 14px;
  color: #6b625a;
}
.actions {
  display: flex;
  gap: 10px;
  margin-top: 24px;
}
.primary-btn,
.ghost-btn {
  flex: 1;
  border: none;
  border-radius: 12px;
  padding: 12px 14px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
}
.primary-btn {
  background: #1f6feb;
  color: white;
}
.ghost-btn {
  background: #f6f1eb;
  color: #4b4037;
}
@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); opacity: 0.45; }
  40% { transform: translateY(-7px); opacity: 1; }
}
@media (max-width: 520px) {
  .loading-panel { padding: 22px; }
  h1 { font-size: 24px; }
  .actions { flex-direction: column; }
}
</style>
