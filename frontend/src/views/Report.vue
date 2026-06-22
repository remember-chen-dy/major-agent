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
const isTestMode = computed(() => route.query.test === '1');
const loading = ref(true);
const error = ref('');
const report = ref<any>(null);

const loadReport = async () => {
  if (!sessionId.value) {
    error.value = '缺少会话 ID';
    loading.value = false;
    return;
  }

  try {
    await authStore.login().catch(() => null);

    // 优先从 reports 表读取报告及支付状态
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
      // 兼容旧数据：从会话结果读取
      const data = await api.getAssessmentResults(sessionId.value);
      if (data.is_generating) {
        router.replace(`/report/${sessionId.value}/loading`);
        return;
      }
      if (!data.is_complete) {
        error.value = '报告还没有生成完成';
        loading.value = false;
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
        loading.value = false;
        return;
      }
    }

    // 未支付则跳转到解锁页
    if (!reportData.is_paid) {
      router.replace(`/report/${sessionId.value}/unlock`);
      return;
    }

    report.value = reportData;

    if (!reportData.report_content?.trim()) {
      error.value = '报告内容还没有写入成功，请返回重新测评或稍后重试';
    }
  } catch {
    error.value = '无法加载报告，请稍后重试';
  } finally {
    loading.value = false;
  }
};

const reportHtml = computed(() => {
  if (!report.value?.report_content) return '';
  return renderMarkdown(report.value.report_content);
});

const reportSummary = computed(() => {
  if (!report.value?.report_content) return ['成绩定位', '专业方向', '志愿梯度', '城市策略', '行动清单'];
  const headings = report.value.report_content
    .split('\n')
    .map((line: string) => line.trim())
    .filter((line: string) => /^#{2,3}\s+/.test(line))
    .map((line: string) => line.replace(/^#{2,3}\s+/, '').replace(/^\d+[、.]\s*/, ''))
    .slice(0, 5);

  return headings.length ? headings : ['成绩定位', '专业方向', '志愿梯度', '城市策略', '行动清单'];
});

const escapeHtml = (text: string) =>
  text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function renderInline(text: string) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>');
}

function renderMarkdown(md: string): string {
  if (!md.trim()) return '<p>报告内容为空。</p>';

  const lines = md.split('\n');
  const html: string[] = [];
  let paragraph: string[] = [];
  let listOpen = false;
  let tableLines: string[] = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    html.push(`<p>${renderInline(paragraph.join(' '))}</p>`);
    paragraph = [];
  };

  const flushList = () => {
    if (listOpen) {
      html.push('</ul>');
      listOpen = false;
    }
  };

  const flushTable = () => {
    if (!tableLines.length) return;
    const rows = tableLines
      .filter(line => !/^\|\s*:?-{3,}/.test(line))
      .map(line => line.split('|').slice(1, -1).map(cell => renderInline(cell.trim())));
    if (rows.length) {
      const [head, ...body] = rows;
      html.push('<div class="table-scroll"><table>');
      html.push(`<thead><tr>${head.map(cell => `<th>${cell}</th>`).join('')}</tr></thead>`);
      html.push(`<tbody>${body.map(row => `<tr>${row.map(cell => `<td>${cell}</td>`).join('')}</tr>`).join('')}</tbody>`);
      html.push('</table></div>');
    }
    tableLines = [];
  };

  for (const raw of lines) {
    const line = raw.trim();

    if (!line) {
      flushTable();
      flushParagraph();
      flushList();
      continue;
    }

    if (line.startsWith('|') && line.endsWith('|')) {
      flushParagraph();
      flushList();
      tableLines.push(line);
      continue;
    }
    flushTable();

    const heading = line.match(/^(#{1,4})\s+(.+)$/);
    if (heading) {
      flushParagraph();
      flushList();
      const level = Math.min(heading[1].length, 3);
      html.push(`<h${level}>${renderInline(heading[2])}</h${level}>`);
      continue;
    }

    const bullet = line.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      if (!listOpen) {
        html.push('<ul>');
        listOpen = true;
      }
      html.push(`<li>${renderInline(bullet[1])}</li>`);
      continue;
    }

    paragraph.push(line);
  }

  flushTable();
  flushParagraph();
  flushList();
  return html.join('');
}

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
  await authStore.login().catch(() => null);
  await loadReport();
});
</script>

<template>
  <main class="report-page">
    <header class="report-nav">
      <button class="home-btn" @click="goHome">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
          <polyline points="9 22 9 12 15 12 15 22"/>
        </svg>
        返回首页
      </button>
      <strong>志愿规划报告</strong>
      <button @click="goReportLibrary">报告库</button>
    </header>

    <section v-if="loading" class="state">正在打开报告...</section>
    <section v-else-if="error" class="state error">
      <p>{{ error }}</p>
      <div class="state-actions">
        <button @click="loadReport">重试</button>
        <button @click="goHome">返回首页</button>
        <button @click="restartAssessment">重新测评</button>
      </div>
    </section>
    <article v-else class="report-shell">
      <div class="report-title">
        <p>AI 志愿规划</p>
        <h1>{{ report?.report_title || '高考志愿规划报告' }}</h1>
        <div class="summary-row">
          <span v-for="item in reportSummary" :key="item">{{ item }}</span>
        </div>
      </div>
      <div class="report-content" v-html="reportHtml"></div>

      <div class="report-actions">
        <button class="primary-action" @click="restartAssessment">重新测评</button>
        <button class="secondary-action" @click="goHome">返回首页</button>
      </div>
    </article>
  </main>
</template>

<style scoped>
.report-page {
  min-height: 100vh;
  min-height: 100dvh;
  background:
    linear-gradient(180deg, #f6f8fb 0%, #fff7ed 48%, #f7f3ed 100%);
  color: #1f2328;
}
.report-nav {
  position: sticky;
  top: 0;
  z-index: 20;
  min-height: 58px;
  padding: 8px 16px;
  display: grid;
  grid-template-columns: minmax(110px, 140px) 1fr minmax(110px, 140px);
  align-items: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid #e6eaf0;
  backdrop-filter: blur(12px);
}
.report-nav strong {
  text-align: center;
  font-size: 16px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.report-nav button,
.state-actions button {
  border: none;
  border-radius: 10px;
  padding: 9px 14px;
  background: #1f6feb;
  color: white;
  font-weight: 750;
  cursor: pointer;
  white-space: nowrap;
}
.report-nav .home-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  background: #f2f6fd;
  color: #1f6feb;
}
.report-nav .home-btn svg {
  flex-shrink: 0;
}
.report-shell {
  width: min(100%, 920px);
  margin: 0 auto;
  padding: 24px 18px 56px;
}
.report-title {
  background:
    linear-gradient(135deg, #14213d 0%, #21566f 58%, #2f6f73 100%);
  color: white;
  border-radius: 16px 16px 0 0;
  padding: 30px;
}
.report-title p {
  margin: 0;
  color: #9ec5ff;
  font-size: 13px;
  font-weight: 800;
}
.report-title h1 {
  margin: 8px 0 0;
  font-size: clamp(28px, 6vw, 44px);
  line-height: 1.1;
}
.report-time {
  margin-top: 10px;
  color: rgba(255, 255, 255, 0.72);
  font-size: 13px;
}
.summary-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 22px;
}
.summary-row span {
  max-width: 100%;
  border: 1px solid rgba(255, 255, 255, 0.24);
  border-radius: 999px;
  padding: 7px 10px;
  background: rgba(255, 255, 255, 0.12);
  color: rgba(255, 255, 255, 0.92);
  font-size: 13px;
  font-weight: 700;
  overflow-wrap: anywhere;
}
.report-content {
  background: white;
  border: 1px solid #e6eaf0;
  border-top: none;
  border-radius: 0 0 16px 16px;
  padding: 34px;
  box-shadow: 0 18px 50px rgba(31, 41, 55, 0.08);
  overflow-wrap: anywhere;
}
.report-content :deep(h1),
.report-content :deep(h2),
.report-content :deep(h3) {
  color: #1f2328;
  line-height: 1.25;
}
.report-content :deep(h1) {
  font-size: 26px;
  margin: 4px 0 18px;
}
.report-content :deep(h2) {
  font-size: 22px;
  margin: 34px 0 14px;
  padding: 13px 14px;
  border-left: 4px solid #2f6f73;
  border-radius: 0 10px 10px 0;
  background: #f1f7f6;
}
.report-content :deep(h3) {
  font-size: 18px;
  margin: 24px 0 10px;
}
.report-content :deep(p),
.report-content :deep(li) {
  color: #374151;
  font-size: 16px;
  line-height: 1.85;
}
.report-content :deep(ul) {
  padding-left: 0;
  list-style: none;
}
.report-content :deep(li) {
  position: relative;
  margin: 9px 0;
  padding-left: 22px;
}
.report-content :deep(li::before) {
  content: "";
  position: absolute;
  left: 4px;
  top: 0.84em;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #2f6f73;
}
.report-content :deep(strong) {
  color: #1f6feb;
}
.report-content :deep(code) {
  background: #f2ede7;
  border-radius: 6px;
  padding: 2px 5px;
}
.report-content :deep(.table-scroll) {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  margin: 18px 0 22px;
  border: 1px solid #e6eaf0;
  border-radius: 12px;
}
.report-content :deep(table) {
  min-width: 620px;
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.report-content :deep(th),
.report-content :deep(td) {
  padding: 12px 14px;
  border-bottom: 1px solid #e6eaf0;
  text-align: left;
  vertical-align: top;
}
.report-content :deep(th) {
  background: #f6f8fb;
  color: #1f2328;
  font-weight: 800;
}
.report-content :deep(tr:last-child td) {
  border-bottom: none;
}
.state {
  min-height: calc(100vh - 58px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 24px;
  color: #62584f;
}
.state.error {
  color: #b42318;
}
.state-actions {
  display: flex;
  gap: 10px;
}
.report-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  margin-top: 32px;
}
.primary-action,
.secondary-action {
  border: none;
  border-radius: 12px;
  padding: 13px 24px;
  font-size: 15px;
  font-weight: 800;
  cursor: pointer;
}
.primary-action {
  background: #1f6feb;
  color: white;
}
.secondary-action {
  background: #f2ede7;
  color: #3d352e;
}
@media (max-width: 640px) {
  .report-nav {
    grid-template-columns: 96px 1fr 96px;
    padding: 8px 10px;
  }
  .report-nav button {
    padding: 8px 10px;
    font-size: 13px;
  }
  .report-nav strong {
    font-size: 14px;
  }
  .report-shell {
    padding: 12px 10px 36px;
  }
  .report-title {
    padding: 22px 16px;
    border-radius: 12px 12px 0 0;
  }
  .summary-row {
    margin-top: 16px;
    gap: 6px;
  }
  .summary-row span {
    font-size: 12px;
    padding: 6px 9px;
  }
  .report-content {
    padding: 20px 14px;
    border-radius: 0 0 12px 12px;
  }
  .report-content :deep(p),
  .report-content :deep(li) {
    font-size: 15px;
    line-height: 1.75;
  }
  .report-actions {
    flex-direction: column;
    margin-top: 24px;
  }
  .primary-action,
  .secondary-action {
    width: 100%;
  }
  .report-content :deep(h2) {
    font-size: 19px;
    padding: 11px 12px;
  }
  .report-content :deep(table) {
    min-width: 560px;
  }
}
</style>
