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
const reportPreview = ref('');

const loadStatus = async () => {
  if (!sessionId.value) {
    error.value = '缺少会话 ID';
    loading.value = false;
    return;
  }

  try {
    const data = await api.getAssessmentResults(sessionId.value);
    if (data.is_generating) {
      router.replace(`/report/${sessionId.value}/loading`);
      return;
    }
    if (!data.is_complete) {
      error.value = '报告还没有生成完成，请稍后再试';
      return;
    }
    reportPreview.value = (data.report || '').split('\n').filter(Boolean).slice(0, 10).join('\n');
  } catch {
    error.value = '无法加载报告状态，请检查网络后重试';
  } finally {
    loading.value = false;
  }
};

const viewReport = () => {
  router.push(`/report/${sessionId.value}`);
};

const goHome = () => {
  router.push('/');
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
  await authStore.login().catch(() => null);
  await loadStatus();
});
</script>

<template>
  <main class="ready-page">
    <section class="ready-shell">
      <button class="back-btn" @click="goHome">返回首页</button>

      <div class="hero">
        <p class="eyebrow">报告已生成</p>
        <h1>你的志愿规划报告已经准备好了</h1>
        <p class="subtext">点击下方按钮即可查看完整报告。报告会直接在页面内展示，手机端也可以完整阅读。</p>
      </div>

      <div v-if="loading" class="state-card">正在确认报告状态...</div>
      <div v-else-if="error" class="state-card error">
        <p>{{ error }}</p>
        <button @click="loadStatus">重试</button>
      </div>
      <div v-else class="ready-grid">
        <article class="preview-card">
          <pre>{{ reportPreview || '报告内容已生成，点击查看完整报告。' }}</pre>
          <div class="fade"></div>
        </article>

        <aside class="action-card">
          <div class="check">✓</div>
          <h2>完整报告可查看</h2>
          <p>包含成绩定位、专业建议、避坑提醒、城市策略和行动清单。</p>
          <button class="primary-btn" @click="viewReport">查看志愿报告</button>
          <button class="ghost-btn" @click="restartAssessment">重新测评</button>
          <button class="ghost-btn" @click="goHome">返回首页</button>
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
  padding: 22px;
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
  padding: 10px 0;
  cursor: pointer;
}
.hero {
  padding: 28px 0 22px;
}
.eyebrow {
  font-size: 13px;
  font-weight: 800;
  color: #1f6feb;
}
h1 {
  max-width: 720px;
  margin-top: 8px;
  font-size: clamp(30px, 6vw, 52px);
  line-height: 1.08;
  font-weight: 900;
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
}
.check {
  width: 46px;
  height: 46px;
  border-radius: 14px;
  background: #1f6feb;
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 24px;
  font-weight: 900;
}
.action-card h2 {
  margin-top: 18px;
  font-size: 22px;
  font-weight: 850;
}
.action-card p {
  margin-top: 10px;
  line-height: 1.65;
  color: #62584f;
}
.primary-btn,
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
.primary-btn {
  margin-top: 22px;
  background: #1f6feb;
  color: #fff;
}
.ghost-btn {
  margin-top: 10px;
  background: #f2ede7;
  color: #3d352e;
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
