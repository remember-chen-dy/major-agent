<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, reactive } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { storeToRefs } from 'pinia';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { ScrollToPlugin } from 'gsap/ScrollToPlugin';
import { useAuthStore } from '../stores/auth';
import { useSessionStore } from '../stores/session';
import { api } from '../api';

gsap.registerPlugin(ScrollTrigger, ScrollToPlugin);

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();
const sessionStore = useSessionStore();

// 从 store 获取响应式引用
const { sessions, currentSessionId } = storeToRefs(sessionStore);

// ============================================================
// 类型定义
// ============================================================

interface FormField {
  id: string;
  label: string;
  type: string;
  placeholder?: string;
}

interface ButtonOption {
  value: string;
  label: string;
}

interface InteractionConfig {
  type: 'form' | 'button_select' | 'tag_multi_select' | 'slider';
  fields?: FormField[];
  options?: ButtonOption[];
  tags?: string[];
  min_select?: number;
  max_select?: number;
  allow_custom?: boolean;
  custom_placeholder?: string;
  searchable?: boolean;
  min?: number;
  max?: number;
  left_label?: string;
  right_label?: string;
  preset_subjects?: string[];
}

interface ChatMessage {
  role: 'ai' | 'user';
  content: string;
  interaction?: InteractionConfig | null;
  user_input?: any;
}

interface Session {
  id: string;
  title: string;
  created_at: string;
  messages: ChatMessage[];
  isComplete: boolean;
  reportStatus?: string;
  reportProgress?: number;
  reportUrl?: string;
}

// ============================================================
// 状态管理
// ============================================================

const isTyping = ref(false);
const mainRef = ref<HTMLElement | null>(null);
const textInput = ref('');
const textareaRef = ref<HTMLTextAreaElement | null>(null);

// 报告生成相关
const isGeneratingReport = ref(false);
const loadingStepText = ref('');
const loadingStepIndex = ref(0);

// 报告库弹窗相关
const showLibrary = ref(false);
const userReports = ref<any[]>([]);
const libraryLoading = ref(false);

// 下拉搜索相关
const showProvinceSearch = ref(false);
const provinceSearchQuery = ref('');
const showMbtiSearch = ref(false);
const mbtiSearchQuery = ref('');

// 表单输入状态
const formFieldValues = reactive<Record<string, string>>({});
const sliderValue = ref(50);
const tagSelected = ref<string[]>([]);
const provinceSelected = ref('');
const customTagInput = ref('');

const API_BASE = 'http://localhost:8000';

const PROVINCES = [
  "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
  "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
  "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州",
  "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆"
];

// 报告生成步骤文案
const LOADING_STEPS = [
  '正在分析成绩与位次...',
  '正在匹配院校专业...',
  '正在评估选科优势...',
  '正在生成个性化方案...',
  '正在撰写志愿规划报告...',
];

// ============================================================
// 计算属性
// ============================================================

const currentSession = computed(() => sessionStore.currentSession);

const currentMessages = computed(() => currentSession.value?.messages ?? []);

/** 只显示当前活跃的问题（最后一个有 interaction 的 AI 消息） */
const visibleMessages = computed(() => {
  if (isGeneratingReport.value) return [];

  const msgs = currentMessages.value;
  if (msgs.length === 0) return [];

  // 找到最后一个有 interaction 的 AI 消息
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'ai' && msgs[i].interaction) {
      return [msgs[i]];
    }
  }

  // 如果没找到交互消息（如报告），显示最后一条
  return msgs.slice(-1);
});

const currentInteraction = computed(() => {
  if (isGeneratingReport.value) return null;

  const msgs = currentMessages.value;
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'ai' && msgs[i].interaction) {
      return msgs[i].interaction;
    }
  }
  return null;
});

const isComplete = computed(() => currentSession.value?.isComplete ?? false);

const filteredProvinces = computed(() => {
  if (!provinceSearchQuery.value) return PROVINCES;
  return PROVINCES.filter(p => p.includes(provinceSearchQuery.value));
});

const isProvinceSelector = (interaction?: InteractionConfig | null) =>
  interaction?.type === 'button_select' && interaction.options?.length === PROVINCES.length;

/** 过滤后的 MBTI 选项 */
const filteredMbtiOptions = computed(() => {
  const interaction = currentInteraction.value;
  if (!interaction?.options) return [];
  if (!mbtiSearchQuery.value) return interaction.options;
  const q = mbtiSearchQuery.value.toUpperCase();
  return interaction.options.filter((o: any) =>
    o.value.toUpperCase().includes(q) || o.label.includes(mbtiSearchQuery.value)
  );
});

const isInputValid = computed(() => {
  const interaction = currentInteraction.value;
  if (!interaction) return false;
  switch (interaction.type) {
    case 'form': {
      if (!interaction.fields) return false;
      return interaction.fields.every((f: any) => {
        const val = formFieldValues[f.id];
        return val !== undefined && val !== null && String(val).trim();
      });
    }
    case 'slider': return true;
    case 'button_select': {
      if (isProvinceSelector(interaction)) return !!provinceSelected.value;
      return tagSelected.value.length > 0;
    }
    case 'tag_multi_select': {
      const min = interaction.min_select ?? 1;
      if (min === 0) return true;
      return tagSelected.value.length >= min;
    }
    default: return false;
  }
});

// ============================================================
// 本地持久化
// ============================================================

// 注意：会话状态现在由 sessionStore 管理，不再需要单独的 loadSessions 和 saveSessions
// sessionStore 会自动处理 localStorage 的读写

// ============================================================
// GSAP 动画函数
// ============================================================

const animateCardExit = (card: HTMLElement): Promise<void> => {
  return new Promise((resolve) => {
    gsap.to(card, { scale: 0.95, opacity: 0, duration: 0.25, ease: 'power2.out', onComplete: resolve });
  });
};

const animateCardEnter = (card: HTMLElement): Promise<void> => {
  return new Promise((resolve) => {
    gsap.fromTo(card, { y: 30, opacity: 0 }, { y: 0, opacity: 1, duration: 0.35, ease: 'power2.out', onComplete: resolve });
  });
};

const animateTagSelect = (tag: HTMLElement) => {
  const tl = gsap.timeline();
  tl.to(tag, { scale: 0.9, duration: 0.1 })
    .to(tag, { scale: 1.05, duration: 0.15, ease: 'back.out(2)' })
    .to(tag, { scale: 1, duration: 0.1 });
};

/** 平滑滚动到页面底部（弹性效果） */
const scrollToBottom = async () => {
  await nextTick();
  const el = mainRef.value;
  if (el) {
    gsap.to(el, { scrollTo: { y: el.scrollHeight, autoKill: false }, duration: 0.45, ease: 'power2.out' });
  }
};

/** 报告加载步骤文案轮播 */
let loadingStepTimer: ReturnType<typeof setInterval> | null = null;
const startLoadingSteps = () => {
  loadingStepIndex.value = 0;
  loadingStepText.value = LOADING_STEPS[0];
  loadingStepTimer = setInterval(() => {
    loadingStepIndex.value++;
    if (loadingStepIndex.value < LOADING_STEPS.length) {
      loadingStepText.value = LOADING_STEPS[loadingStepIndex.value];
    }
  }, 2500);
};
const stopLoadingSteps = () => {
  if (loadingStepTimer) {
    clearInterval(loadingStepTimer);
    loadingStepTimer = null;
  }
};

// ── 轮询报告生成状态 ──
let pollTimer: ReturnType<typeof setInterval> | null = null;

const stopPollingReport = () => {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
};

const getReportReadyRoute = (sid: string) => `/report/${sid}/ready`;

const applyReportState = (sid: string, data: any) => {
  const session = sessions.value.find((s: any) => s.id === sid);
  if (!session) return;

  session.messages = data.messages || session.messages || [];
  session.isComplete = !!data.is_complete;
  session.reportStatus = data.report_status;
  session.reportProgress = data.report_progress;
  session.reportUrl = data.report_url || '';
};

const pollReportOnce = async (sid: string, navigate = true) => {
  const data = await api.getAssessmentResults(sid);
  applyReportState(sid, data);

  if (data.is_complete) {
    stopPollingReport();
    stopLoadingSteps();
    isGeneratingReport.value = false;
    if (navigate) router.replace(getReportReadyRoute(sid));
    return data;
  }

  if (data.is_failed) {
    stopPollingReport();
    stopLoadingSteps();
    isGeneratingReport.value = false;
    showToast('报告生成失败，请稍后重试');
    return data;
  }

  if (data.is_generating) {
    isGeneratingReport.value = true;
    if (!loadingStepTimer) startLoadingSteps();
    if (navigate && currentSessionId.value !== sid) {
      router.push(`/report/${sid}/loading`);
    }
  }

  return data;
};

const startPollingReport = async (sid: string, navigateOnComplete = true) => {
  stopPollingReport();
  isGeneratingReport.value = true;
  if (!loadingStepTimer) startLoadingSteps();

  try {
    await pollReportOnce(sid, navigateOnComplete);
  } catch {
    // 网络错误时继续轮询
  }

  pollTimer = setInterval(async () => {
    try {
      await pollReportOnce(sid, navigateOnComplete);
    } catch {
      // 网络错误时继续轮询
    }
  }, 3000);
};

const showToast = (message: string) => {
  const toast = document.createElement('div');
  toast.className = 'fixed top-4 left-1/2 -translate-x-1/2 bg-[#1c1c1e] text-white px-6 py-3 rounded-xl shadow-lg z-[100] text-[13px] font-medium';
  toast.textContent = message;
  document.body.appendChild(toast);
  gsap.fromTo(toast, { y: -40, opacity: 0 }, { y: 0, opacity: 1, duration: 0.3, ease: 'power2.out' });
  setTimeout(() => {
    gsap.to(toast, { y: -40, opacity: 0, duration: 0.25, onComplete: () => toast.remove() });
  }, 2000);
};

// ============================================================
// API 方法
// ============================================================

const createSession = async () => {
  try {
    await sessionStore.createSession();
    resetFormState();
    await nextTick();
    const lastCard = document.querySelector('.message-card:last-child');
    if (lastCard) animateCardEnter(lastCard as HTMLElement);
  } catch (e) {
    console.error('创建会话失败:', e);
  }
};

const collectAnswer = (): any => {
  const interaction = currentInteraction.value;
  if (!interaction) return null;
  switch (interaction.type) {
    case 'form': {
      const result: Record<string, any> = {};
      if (interaction.fields) {
        for (const field of interaction.fields) {
          const val = formFieldValues[field.id];
          result[field.id] = field.type === 'number' ? (val ? Number(val) : 0) : (val || '');
        }
      }
      return result;
    }
    case 'slider': return sliderValue.value;
    case 'button_select': {
      if (isProvinceSelector(interaction)) return provinceSelected.value || null;
      return tagSelected.value[0] || null;
    }
    case 'tag_multi_select': {
      if (interaction.preset_subjects) return [...interaction.preset_subjects, ...tagSelected.value];
      return [...tagSelected.value];
    }
    default: return null;
  }
};

/** 提交用户输入 */
const submitInput = async () => {
  if (!currentSessionId.value || isTyping.value) return;
  if (!isInputValid.value) return;

  const session = sessions.value.find((s: any) => s.id === currentSessionId.value);
  if (!session) return;

  const answer = collectAnswer();
  if (answer === null) return;

  const interaction = currentInteraction.value!;

  // 触感反馈
  hapticFeedback('light');

  // 退场动画
  const currentCard = document.querySelector('.interaction-card');
  if (currentCard) await animateCardExit(currentCard as HTMLElement);

  // 添加用户消息
  const userMsg: ChatMessage = { role: 'user', content: formatUserInput(answer, interaction), user_input: answer };
  session.messages.push(userMsg);
  isTyping.value = true;

  // 自动滚动到底部
  await scrollToBottom();

  // 更新标题
  const userMsgs = session.messages.filter((m: any) => m.role === 'user');
  if (userMsgs.length === 1) session.title = userMsg.content.slice(0, 20);

  try {
    const sid = currentSessionId.value;
    const data = await api.sendAssessmentAnswer(sid, answer);

    if (data.is_complete) {
      applyReportState(sid, data);
      stopLoadingSteps();
      isGeneratingReport.value = false;
      router.replace(getReportReadyRoute(sid));
    } else if (data.is_generating) {
      isGeneratingReport.value = true;
      startLoadingSteps();
      applyReportState(sid, data);
      router.push(`/report/${sid}/loading`);
    } else if (data.messages && Array.isArray(data.messages)) {
      for (const msg of data.messages) {
        session.messages.push({
          role: msg.role || 'ai',
          content: msg.content || '',
          interaction: msg.interaction || null,
        });
      }
    }

    if (!data.is_generating && !data.is_complete) {
      resetFormState();
      await nextTick();
      const newCard = document.querySelector('.interaction-card');
      if (newCard) {
        await animateCardEnter(newCard as HTMLElement);
        await scrollToBottom();
      }
    }
  } catch (e) {
    stopLoadingSteps();
    isGeneratingReport.value = false;
    session.messages.push({ role: 'ai', content: '抱歉，网络出现了问题，请稍后重试。' });
  } finally {
    isTyping.value = false;
  }
};

const formatUserInput = (input: any, interaction: InteractionConfig): string => {
  switch (interaction.type) {
    case 'form': {
      if (typeof input === 'object' && input !== null) {
        return Object.entries(input).map(([key, val]) => {
          const field = interaction.fields?.find(f => f.id === key);
          return `${field?.label || key}: ${val}`;
        }).join('，');
      }
      return String(input);
    }
    case 'slider': return `选择了 ${input} 分`;
    case 'button_select': {
      const opt = interaction.options?.find(o => o.value === input);
      return opt?.label || String(input);
    }
    case 'tag_multi_select': return Array.isArray(input) ? input.join('、') : String(input);
    default: return String(input);
  }
};

const resetFormState = () => {
  Object.keys(formFieldValues).forEach(key => delete formFieldValues[key]);
  sliderValue.value = 50;
  tagSelected.value = [];
  provinceSelected.value = '';
  customTagInput.value = '';
  mbtiSearchQuery.value = '';
  provinceSearchQuery.value = '';
  showMbtiSearch.value = false;
  showProvinceSearch.value = false;
  textInput.value = '';
  nextTick(() => autoResizeTextarea());
};

/** 触感反馈（haptic feedback 概念） */
const hapticFeedback = (type: 'light' | 'medium' | 'heavy' = 'light') => {
  if ('vibrate' in navigator) {
    const durations: Record<string, number> = { light: 10, medium: 20, heavy: 30 };
    navigator.vibrate(durations[type] || 10);
  }
};

/** 自动适应 textarea 高度 */
const autoResizeTextarea = () => {
  const el = textareaRef.value;
  if (!el) return;
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
};

/** 底部输入栏发送文本消息 */
const sendTextMessage = async () => {
  const text = textInput.value.trim();
  if (!text || isTyping.value || !currentSessionId.value) return;

  const session = sessions.value.find((s: any) => s.id === currentSessionId.value);
  if (!session) return;

  hapticFeedback('light');

  session.messages.push({ role: 'user', content: text });
  textInput.value = '';
  nextTick(() => autoResizeTextarea());
  isTyping.value = true;
  await scrollToBottom();

  try {
    const sid = currentSessionId.value;
    const data = await api.sendAssessmentAnswer(sid, text);

    if (data.is_complete) {
      applyReportState(sid, data);
      stopLoadingSteps();
      isGeneratingReport.value = false;
      router.replace(getReportReadyRoute(sid));
    } else if (data.is_generating) {
      isGeneratingReport.value = true;
      startLoadingSteps();
      applyReportState(sid, data);
      router.push(`/report/${sid}/loading`);
    } else if (data.messages && Array.isArray(data.messages)) {
      for (const msg of data.messages) {
        session.messages.push({ role: msg.role || 'ai', content: msg.content || '', interaction: msg.interaction || null });
      }
      resetFormState();
      await scrollToBottom();
    }
  } catch {
    session.messages.push({ role: 'ai', content: '抱歉，网络出现了问题，请稍后重试。' });
  } finally {
    isTyping.value = false;
  }
};

const toggleTag = (value: string, multiple: boolean, event?: MouseEvent) => {
  const tag = event?.target as HTMLElement;
  if (multiple) {
    const idx = tagSelected.value.indexOf(value);
    if (idx >= 0) {
      tagSelected.value.splice(idx, 1);
    } else {
      const max = currentInteraction.value?.max_select ?? 999;
      if (tagSelected.value.length < max) {
        tagSelected.value.push(value);
        if (tag) animateTagSelect(tag);
      }
    }
  } else {
    tagSelected.value = [value];
    if (tag) animateTagSelect(tag);
  }
};

const addCustomTag = () => {
  const val = customTagInput.value.trim();
  if (!val) return;
  const max = currentInteraction.value?.max_select ?? 999;
  if (tagSelected.value.length >= max) return;
  if (!tagSelected.value.includes(val)) tagSelected.value.push(val);
  customTagInput.value = '';
};

const isTagSelected = (value: string) => tagSelected.value.includes(value);
const removeTag = (value: string) => {
  const idx = tagSelected.value.indexOf(value);
  if (idx >= 0) tagSelected.value.splice(idx, 1);
};

const selectProvince = (province: string) => {
  provinceSelected.value = province;
  showProvinceSearch.value = false;
  provinceSearchQuery.value = '';
};

/** 选择 MBTI 类型 */
const selectMbti = (value: string, event?: MouseEvent) => {
  tagSelected.value = [value];
  showMbtiSearch.value = false;
  mbtiSearchQuery.value = '';
  const tag = event?.target as HTMLElement;
  if (tag) animateTagSelect(tag);
};

const handleClickOutside = (e: MouseEvent) => {
  const target = e.target as HTMLElement;
  if (!target.closest('.province-search-wrapper')) showProvinceSearch.value = false;
  if (!target.closest('.mbti-search-wrapper')) showMbtiSearch.value = false;
};

const goBack = () => {
  window.history.length > 1 ? window.history.back() : (window.location.href = '/');
};

const openLibrary = async () => {
  showLibrary.value = true;
  await loadUserReports();
};

const closeLibrary = () => {
  showLibrary.value = false;
};

const loadUserReports = async () => {
  if (!authStore.userId) return;
  libraryLoading.value = true;
  try {
    const data = await api.getUserReports(authStore.userId);
    userReports.value = data.reports || [];
  } catch (error) {
    console.error('加载报告库失败:', error);
  } finally {
    libraryLoading.value = false;
  }
};

const viewReportFromLibrary = (report: any) => {
  closeLibrary();
  if (report.session_id) {
    router.push(`/report/${report.session_id}`);
  }
};

const formatReportTime = (iso: string) => {
  if (!iso) return '';
  const d = new Date(iso);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`;
};

// ============================================================
// 生命周期
// ============================================================

let hasInitialized = false;

onMounted(async () => {
  if (hasInitialized) return;
  hasInitialized = true;

  try {
    // 登录
    await authStore.login();

    // 从 localStorage 加载会话状态
    sessionStore.loadFromStorage();

    // 从服务端获取当前用户唯一会话
    if (authStore.userId) {
      try {
        const data = await api.getUserSessions(authStore.userId);
        const latestSession = data.sessions?.[0];
        if (latestSession) {
          sessions.value = [{
            id: latestSession.session_id,
            title: latestSession.title || '志愿测评',
            created_at: latestSession.created_at || new Date().toISOString(),
            messages: [],
            isComplete: latestSession.report_status === 'completed',
            reportStatus: latestSession.report_status,
            reportProgress: latestSession.report_progress,
            reportUrl: latestSession.report_url,
            report: latestSession.report,
          }];
          currentSessionId.value = latestSession.session_id;

          // 如果已有报告，直接跳转到报告查看页面
          if (latestSession.report_status === 'completed' && latestSession.report) {
            router.replace(`/report/${latestSession.session_id}`);
            return;
          }

          if (sessions.value[0].messages.length === 0) {
            await sessionStore.loadSessionMessages(latestSession.session_id).catch(() => null);
          }
        } else {
          sessionStore.clearCurrentSession();
        }
      } catch (err) {
        console.warn('[onMounted] 获取当前会话失败:', err);
      }
    }

    // 如果没有会话，创建新会话
    if (sessions.value.length === 0) {
      await createSession();
    } else if (currentSessionId.value && route.query.fromReport !== '1') {
      try {
        const data = await api.getAssessmentResults(currentSessionId.value);
        applyReportState(currentSessionId.value, data);

        if (data.is_generating) {
          router.replace(`/report/${currentSessionId.value}/loading`);
          return;
        }

        if (data.is_failed) {
          // 报告失败时只重置状态，不自动创建新会话（避免重复调用 POST /api/sessions）
          sessionStore.clearCurrentSession();
          showToast('报告生成失败，请重新测评');
          return;
        }

        if (data.is_complete) {
          router.replace(`/report/${currentSessionId.value}`);
          return;
        }
      } catch {
        // 离线或服务端暂时不可用时，继续展示本地会话
      }
    }

    document.addEventListener('click', handleClickOutside);

    // 添加 beforeunload 处理器，保存进度
    window.addEventListener('beforeunload', () => {
      sessionStore.saveToStorage();
    });

    // 如果从报告库入口进入，自动打开报告库
    if (route.query.reportLibrary === '1') {
      openLibrary();
    }
  } catch (error) {
    console.error('[onMounted] 初始化失败:', error);
  }
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
  stopPollingReport();
  stopLoadingSteps();
  gsap.killTweensOf('*');
  ScrollTrigger.getAll().forEach(t => t.kill());
});
</script>

<template>
  <div class="coze-chat">
    <!-- 顶部导航栏 -->
    <header class="coze-nav">
      <div class="coze-nav-inner">
        <button @click="goBack" class="coze-nav-btn" aria-label="返回">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>
        </button>
        <h1 class="coze-nav-title">{{ currentSession?.title ?? 'AI 志愿顾问' }}</h1>
        <button @click="openLibrary" class="coze-nav-btn" aria-label="报告库">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>
          </svg>
        </button>
      </div>
    </header>

    <!-- 消息列表区域 - 居中单问题模式 -->
    <main ref="mainRef" class="coze-messages">
      <div class="coze-messages-center">
        <div v-for="(msg, i) in visibleMessages" :key="i" class="coze-msg-row"
          :class="msg.role === 'user' ? 'coze-msg-user' : 'coze-msg-ai'">

          <!-- AI 头像 -->
          <div v-if="msg.role === 'ai'" class="coze-avatar">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M12 2a10 10 0 1010 10A10 10 0 0012 2zm0 3a2 2 0 11-2 2 2 2 0 012-2zm0 14.2a6 6 0 01-5-2.7 1 1 0 01.1-1.1 6.6 6.6 0 019.8 0 1 1 0 01.1 1.1A6 6 0 0112 19.2z"/></svg>
          </div>

          <!-- 消息气泡 -->
          <div class="coze-bubble" :class="msg.role === 'user' ? 'coze-bubble-user' : 'coze-bubble-ai'">
            <div class="coze-bubble-text" v-html="msg.content.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')"></div>

            <!-- form: 多字段表单 -->
            <div v-if="msg.role === 'ai' && msg.interaction?.type === 'form' && !isComplete" class="interaction-card mt-3">
              <div class="space-y-3">
                <div v-for="field in (msg.interaction.fields || [])" :key="field.id">
                  <label class="coze-label">{{ field.label }}</label>
                  <input v-model="formFieldValues[field.id]" :type="field.type || 'text'" :placeholder="field.placeholder || ''"
                    class="coze-input" @keydown.enter="submitInput" />
                </div>
              </div>
              <button @click="submitInput" :disabled="!isInputValid" class="coze-action-btn mt-3" :class="isInputValid ? '' : 'coze-action-btn-disabled'">提交</button>
            </div>

            <!-- slider -->
            <div v-if="msg.role === 'ai' && msg.interaction?.type === 'slider' && !isComplete" class="interaction-card mt-3">
              <div class="space-y-3">
                <div class="flex justify-between coze-label">
                  <span class="max-w-[45%]">{{ msg.interaction.left_label || '低' }}</span>
                  <span class="max-w-[45%] text-right">{{ msg.interaction.right_label || '高' }}</span>
                </div>
                <div class="relative">
                  <input type="range" v-model.number="sliderValue" :min="msg.interaction.min ?? 0" :max="msg.interaction.max ?? 100" class="coze-slider" />
                  <div class="coze-slider-tooltip" :style="{ left: `calc(${((sliderValue - (msg.interaction.min ?? 0)) / ((msg.interaction.max ?? 100) - (msg.interaction.min ?? 0))) * 100}% - 16px)` }">{{ sliderValue }}</div>
                </div>
              </div>
              <button @click="submitInput" class="coze-action-btn mt-3">确认</button>
            </div>

            <!-- button_select -->
            <div v-if="msg.role === 'ai' && msg.interaction?.type === 'button_select' && !isComplete" class="interaction-card mt-3">
              <template v-if="isProvinceSelector(msg.interaction)">
                <div class="province-search-wrapper relative">
                  <button @click.stop="showProvinceSearch = !showProvinceSearch" class="coze-select-btn">
                    <span :class="provinceSelected ? 'text-[#1c1c1e]' : 'text-[#8e8e93]'">{{ provinceSelected || '请选择省份' }}</span>
                    <svg class="w-4 h-4 text-[#8e8e93]" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                  </button>
                  <div v-if="showProvinceSearch" class="coze-select-dropdown">
                    <div class="p-2.5 border-b border-[#e5e5ea]">
                      <input v-model="provinceSearchQuery" type="text" placeholder="搜索省份..." class="coze-input !text-[13px]" />
                    </div>
                    <div class="max-h-44 overflow-y-auto">
                      <button v-for="province in filteredProvinces" :key="province" @click="selectProvince(province)"
                        class="coze-select-option" :class="provinceSelected === province ? 'coze-select-option-active' : ''">{{ province }}</button>
                    </div>
                  </div>
                </div>
              </template>
              <template v-else-if="msg.interaction.searchable || (msg.interaction.options && msg.interaction.options.length >= 16)">
                <div class="mbti-search-wrapper relative">
                  <button @click.stop="showMbtiSearch = !showMbtiSearch" class="coze-select-btn">
                    <span :class="tagSelected[0] ? 'text-[#1c1c1e]' : 'text-[#8e8e93]'">
                      {{ tagSelected[0] ? (msg.interaction.options?.find((o: any) => o.value === tagSelected[0])?.label || tagSelected[0]) : '请选择 MBTI 类型' }}
                    </span>
                    <svg class="w-4 h-4 text-[#8e8e93] transition-transform" :class="showMbtiSearch ? 'rotate-180' : ''" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                  </button>
                  <div v-if="showMbtiSearch" class="coze-select-dropdown">
                    <div class="p-2.5 border-b border-[#e5e5ea]">
                      <input v-model="mbtiSearchQuery" type="text" placeholder="搜索..." class="coze-input !text-[13px]" />
                    </div>
                    <div class="max-h-52 overflow-y-auto">
                      <button v-for="opt in filteredMbtiOptions" :key="opt.value" @click="selectMbti(opt.value, $event)"
                        class="coze-select-option" :class="tagSelected[0] === opt.value ? 'coze-select-option-active' : ''">{{ opt.label }}</button>
                      <div v-if="filteredMbtiOptions.length === 0" class="coze-select-empty">没有匹配的结果</div>
                    </div>
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="flex flex-col gap-2">
                  <button v-for="(opt, idx) in (msg.interaction.options || [])" :key="idx" @click="toggleTag(opt.value, false, $event)"
                    class="coze-option-btn" :class="isTagSelected(opt.value) ? 'coze-option-btn-active' : ''">{{ opt.label }}</button>
                </div>
              </template>
              <button @click="submitInput" :disabled="!isInputValid" class="coze-action-btn mt-3" :class="isInputValid ? '' : 'coze-action-btn-disabled'">确认</button>
            </div>

            <!-- tag_multi_select -->
            <div v-if="msg.role === 'ai' && msg.interaction?.type === 'tag_multi_select' && !isComplete" class="interaction-card mt-3">
              <div v-if="msg.interaction.preset_subjects" class="coze-preset-box">
                <div class="flex flex-wrap gap-1.5">
                  <span v-for="subject in msg.interaction.preset_subjects" :key="subject" class="coze-preset-tag">{{ subject }}</span>
                </div>
                <p class="coze-hint mt-1.5">以上为必考科目，请从下方选择 3 门选考科目</p>
              </div>
              <div v-if="tagSelected.length > 0" class="flex flex-wrap gap-1.5 mb-2.5">
                <span v-for="tag in tagSelected" :key="tag" class="coze-tag-selected">
                  {{ tag }}
                  <button @click="removeTag(tag)" class="ml-0.5 hover:text-blue-200"><svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><path d="M18 6L6 18M6 6l12 12"/></svg></button>
                </span>
              </div>
              <div class="flex flex-wrap gap-2">
                <button v-for="(tag, idx) in (msg.interaction.tags || [])" :key="idx" @click="toggleTag(tag, true, $event)"
                  class="coze-tag-btn" :class="isTagSelected(tag) ? 'coze-tag-btn-active' : ''">{{ tag }}</button>
              </div>
              <div v-if="msg.interaction.allow_custom" class="flex gap-2 mt-2.5">
                <input v-model="customTagInput" :placeholder="msg.interaction.custom_placeholder || '自定义...'" class="coze-input flex-1 !text-[13px]" @keydown.enter="addCustomTag" />
                <button @click="addCustomTag" :disabled="!customTagInput.trim()" class="coze-action-btn-sm !mt-0 disabled:opacity-40">添加</button>
              </div>
              <p v-if="msg.interaction.min_select === 0" class="coze-hint mt-2">不选也可以，直接确认即可跳过</p>
              <button @click="submitInput" :disabled="!isInputValid" class="coze-action-btn mt-3" :class="isInputValid ? '' : 'coze-action-btn-disabled'">确认</button>
            </div>
          </div>
        </div>

        <!-- 输入中状态 -->
        <div v-if="isTyping && !isGeneratingReport" class="coze-msg-ai">
          <div class="coze-avatar"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2"><path d="M12 2a10 10 0 1010 10A10 10 0 0012 2zm0 3a2 2 0 11-2 2 2 2 0 012-2zm0 14.2a6 6 0 01-5-2.7 1 1 0 01.1-1.1 6.6 6.6 0 019.8 0 1 1 0 01.1 1.1A6 6 0 0112 19.2z"/></svg></div>
          <div class="coze-bubble-ai coze-typing">
            <div class="flex gap-1.5 items-center h-5">
              <div class="coze-dot" style="animation-delay:0s"></div>
              <div class="coze-dot" style="animation-delay:0.15s"></div>
              <div class="coze-dot" style="animation-delay:0.3s"></div>
            </div>
          </div>
        </div>

        <!-- 报告生成中 -->
        <div v-if="isGeneratingReport" class="flex justify-center py-12">
          <div class="text-center">
            <div class="coze-spinner mx-auto mb-4">
              <div></div><div></div><div></div><div></div>
            </div>
            <p class="coze-body font-medium text-[#8e8e93] mb-1">{{ loadingStepText }}</p>
          </div>
        </div>
      </div>
    </main>

    <!-- 报告库弹窗 -->
    <div v-if="showLibrary" class="library-overlay" @click="closeLibrary">
      <div class="library-panel" @click.stop>
        <div class="library-header">
          <h2>报告库</h2>
          <button @click="closeLibrary" aria-label="关闭">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>
          </button>
        </div>

        <div v-if="libraryLoading" class="library-empty">正在加载报告...</div>
        <div v-else-if="userReports.length === 0" class="library-empty">
          暂无报告，完成测评后即可在这里查看。
        </div>
        <ul v-else class="library-list">
          <li v-for="report in userReports" :key="report.report_id" @click="viewReportFromLibrary(report)">
            <div class="library-item">
              <div class="library-item-info">
                <p class="library-item-title">{{ report.report_title }}</p>
                <p class="library-item-time">{{ formatReportTime(report.created_at) }}</p>
              </div>
              <span class="library-item-status" :class="report.is_paid ? 'paid' : 'unpaid'">
                {{ report.is_paid ? '已支付' : '未支付' }}
              </span>
            </div>
          </li>
        </ul>
      </div>
    </div>

  </div>
</template>

<style scoped>
/* ============================================================
   Coze (扣子) Design System - 暖色背景
   ============================================================ */

/* --- 设计令牌 --- */
.coze-chat {
  --coze-bg: #faf7f2;
  --coze-blue: #007aff;
  --coze-blue-hover: #0066d6;
  --coze-text: #1c1c1e;
  --coze-text-secondary: #8e8e93;
  --coze-separator: #e5e5ea;
  --coze-font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', sans-serif;
  --coze-card-bg: #ffffff;
  --coze-card-radius: 14px;
  --coze-card-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  --coze-bubble-ai: #ffffff;

  min-height: 100vh;
  min-height: 100dvh;
  background: var(--coze-bg);
  font-family: var(--coze-font);
  display: flex;
  flex-direction: column;
  color: var(--coze-text);
}

/* --- 排版层级 --- */
.coze-title { font-size: 22px; font-weight: 600; line-height: 1.3; }
.coze-card-title { font-size: 17px; font-weight: 600; line-height: 1.4; }
.coze-body { font-size: 15px; font-weight: 400; line-height: 1.5; }
.coze-sub { font-size: 13px; font-weight: 400; line-height: 1.4; color: var(--coze-text-secondary); }
.coze-label { display: block; font-size: 13px; font-weight: 500; color: var(--coze-text-secondary); margin-bottom: 4px; }
.coze-hint { font-size: 12px; font-weight: 400; color: var(--coze-text-secondary); }

/* --- 导航栏 --- */
.coze-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(250, 247, 242, 0.85);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-bottom: 0.5px solid var(--coze-separator);
}
.coze-nav-inner {
  max-width: 680px;
  margin: 0 auto;
  padding: 8px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 44px;
}
.coze-nav-btn {
  width: 34px; height: 34px;
  border-radius: 50%;
  background: transparent;
  border: none;
  display: flex; align-items: center; justify-content: center;
  color: var(--coze-blue);
  cursor: pointer;
  transition: background 0.15s;
}
.coze-nav-btn:active { background: rgba(0, 0, 0, 0.05); }
.coze-nav-spacer {
  width: 34px;
  height: 34px;
}
.coze-nav-title {
  font-size: 17px;
  font-weight: 600;
  color: var(--coze-text);
  text-align: center;
  flex: 1;
  padding: 0 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* --- 下拉菜单 --- */
.coze-dropdown {
  position: absolute;
  right: 0; top: 44px;
  width: 280px;
  background: var(--coze-card-bg);
  border-radius: var(--coze-card-radius);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  z-index: 60;
}
.coze-dropdown-header {
  padding: 12px 16px;
  border-bottom: 0.5px solid var(--coze-separator);
  display: flex; align-items: center; justify-content: space-between;
}
.coze-dropdown-title { font-size: 13px; font-weight: 600; color: var(--coze-text); }
.coze-dropdown-add {
  width: 24px; height: 24px;
  border-radius: 50%;
  background: var(--coze-blue);
  color: white;
  border: none;
  display: flex; align-items: center; justify-content: center;
  cursor: pointer;
}
.coze-dropdown-list { max-height: 288px; overflow-y: auto; padding: 4px 0; }
.coze-dropdown-item {
  width: 100%;
  text-align: left;
  padding: 10px 16px;
  background: transparent;
  border: none;
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: background 0.12s;
}
.coze-dropdown-item:active { background: rgba(0, 0, 0, 0.04); }
.coze-dropdown-item-active { background: rgba(0, 122, 255, 0.06); }
.coze-dropdown-item-title { font-size: 14px; font-weight: 500; color: var(--coze-text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.coze-dropdown-item-sub { font-size: 12px; color: var(--coze-text-secondary); margin-top: 2px; }
.coze-dropdown-item > button:first-child { background: transparent; border: none; padding: 0; cursor: pointer; font-family: var(--coze-font); }
.coze-dropdown-item-del {
  margin-left: 8px;
  width: 24px; height: 24px;
  border-radius: 50%;
  background: transparent;
  border: none;
  display: flex; align-items: center; justify-content: center;
  color: #c7c7cc;
  cursor: pointer;
  transition: all 0.12s;
}
.coze-dropdown-item-del:hover { background: rgba(255, 59, 48, 0.06); color: #ff3b30; }

/* --- 消息列表 --- */
.coze-messages {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
  overscroll-behavior-y: contain;
}
.coze-messages-center {
  max-width: 680px;
  margin: 0 auto;
  padding: 24px 16px;
  min-height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 12px;
}
.coze-messages-inner {
  max-width: 680px;
  margin: 0 auto;
  padding: 24px 16px;
}

/* 极简滚动条 */
.coze-messages::-webkit-scrollbar { width: 3px; }
.coze-messages::-webkit-scrollbar-track { background: transparent; }
.coze-messages::-webkit-scrollbar-thumb { background: rgba(0, 0, 0, 0.12); border-radius: 3px; }

/* --- 消息行 --- */
.coze-msg-row {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  margin-bottom: 12px;
  animation: cozeFadeIn 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.coze-msg-user { justify-content: flex-end; }
.coze-msg-ai { justify-content: flex-start; }

@keyframes cozeFadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* --- 头像 --- */
.coze-avatar {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #007aff, #5856d6);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}

/* --- 消息气泡 --- */
.coze-bubble {
  max-width: 85%;
  padding: 10px 14px;
  word-break: break-word;
}
.coze-bubble-text {
  font-size: 15px;
  line-height: 1.5;
  white-space: pre-wrap;
}
.coze-bubble-text :deep(strong) { font-weight: 600; }

.coze-bubble-user {
  background: var(--coze-blue);
  color: white;
  border-radius: 16px 16px 4px 16px;
  box-shadow: var(--coze-card-shadow);
}
.coze-bubble-ai {
  background: var(--coze-bubble-ai);
  color: var(--coze-text);
  border-radius: 16px;
  box-shadow: var(--coze-card-shadow);
  max-width: 100%;
}

/* --- 输入中动画 --- */
.coze-typing { padding: 12px 16px; }
.coze-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--coze-text-secondary);
  animation: cozeBounce 1.2s infinite;
}
@keyframes cozeBounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.3; }
  30% { transform: translateY(-4px); opacity: 1; }
}

/* --- 报告加载 spinner --- */
.coze-spinner {
  width: 28px; height: 28px;
  position: relative;
}
.coze-spinner div {
  position: absolute;
  width: 5px; height: 5px;
  border-radius: 50%;
  background: var(--coze-blue);
  animation: cozeSpinner 1.2s infinite ease-in-out;
}
.coze-spinner div:nth-child(1) { top: 1px; left: 11px; animation-delay: -0.9s; }
.coze-spinner div:nth-child(2) { top: 7px; right: 3px; animation-delay: -0.6s; }
.coze-spinner div:nth-child(3) { bottom: 7px; right: 3px; animation-delay: -0.3s; }
.coze-spinner div:nth-child(4) { bottom: 1px; left: 11px; animation-delay: 0s; }
@keyframes cozeSpinner {
  0%, 80%, 100% { transform: scale(0.4); opacity: 0.3; }
  40% { transform: scale(1); opacity: 1; }
}

/* --- 卡片 --- */
.coze-card {
  background: var(--coze-card-bg);
  border-radius: var(--coze-card-radius);
  overflow: hidden;
  box-shadow: var(--coze-card-shadow);
}
.coze-card-header {
  background: linear-gradient(135deg, #007aff, #5856d6);
  padding: 20px 16px;
  text-align: center;
}

/* --- 输入框 --- */
.coze-input {
  width: 100%;
  padding: 10px 14px;
  font-size: 15px;
  font-family: var(--coze-font);
  border: none;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.03);
  color: var(--coze-text);
  outline: none;
  transition: background 0.2s, box-shadow 0.2s;
}
.coze-input:focus {
  background: white;
  box-shadow: 0 0 0 2px rgba(0, 122, 255, 0.15);
}
.coze-input::placeholder { color: var(--coze-text-secondary); }

/* --- 主操作按钮 --- */
.coze-action-btn {
  width: 100%;
  padding: 11px 16px;
  border-radius: 10px;
  background: var(--coze-blue);
  color: white;
  font-size: 15px;
  font-weight: 600;
  font-family: var(--coze-font);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: background 0.15s, transform 0.1s;
}
.coze-action-btn:active:not(:disabled) { transform: scale(0.98); background: var(--coze-blue-hover); }
.coze-action-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.coze-action-btn-disabled { opacity: 0.4; cursor: not-allowed; }

.coze-action-btn-sm {
  padding: 8px 14px;
  border-radius: 8px;
  background: var(--coze-blue);
  color: white;
  font-size: 13px;
  font-weight: 600;
  font-family: var(--coze-font);
  border: none;
  cursor: pointer;
}

/* --- 描边按钮 --- */
.coze-outline-btn {
  width: 100%;
  padding: 11px 16px;
  border-radius: 10px;
  background: transparent;
  color: var(--coze-text);
  font-size: 15px;
  font-weight: 600;
  font-family: var(--coze-font);
  border: 1.5px solid var(--coze-separator);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  transition: background 0.15s, transform 0.1s;
}
.coze-outline-btn:active:not(:disabled) { transform: scale(0.98); background: rgba(0, 0, 0, 0.03); }
.coze-outline-btn:disabled { opacity: 0.5; }

/* --- 选项按钮 --- */
.coze-option-btn {
  width: 100%;
  text-align: left;
  padding: 11px 14px;
  font-size: 15px;
  font-family: var(--coze-font);
  border: none;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.03);
  color: var(--coze-text);
  cursor: pointer;
  transition: all 0.12s;
}
.coze-option-btn:active { background: rgba(0, 0, 0, 0.06); }
.coze-option-btn-active {
  background: var(--coze-blue);
  color: white;
}

/* --- 下拉选择 --- */
.coze-select-btn {
  width: 100%;
  text-align: left;
  padding: 11px 14px;
  font-size: 15px;
  font-family: var(--coze-font);
  border: none;
  border-radius: 10px;
  background: rgba(0, 0, 0, 0.03);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  color: var(--coze-text);
  transition: background 0.12s;
}
.coze-select-btn:active { background: rgba(0, 0, 0, 0.06); }
.coze-select-dropdown {
  position: absolute;
  top: 100%;
  left: 0; right: 0;
  margin-top: 4px;
  background: var(--coze-card-bg);
  border-radius: 12px;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  z-index: 10;
}
.coze-select-option {
  width: 100%;
  text-align: left;
  padding: 10px 16px;
  font-size: 14px;
  font-family: var(--coze-font);
  border: none;
  background: transparent;
  color: var(--coze-text);
  cursor: pointer;
  transition: background 0.12s;
}
.coze-select-option:active { background: rgba(0, 0, 0, 0.04); }
.coze-select-option-active { color: var(--coze-blue); font-weight: 500; background: rgba(0, 122, 255, 0.06); }
.coze-select-empty { padding: 12px 16px; font-size: 13px; color: var(--coze-text-secondary); text-align: center; }

/* --- 标签 --- */
.coze-tag-btn {
  padding: 6px 14px;
  font-size: 14px;
  font-weight: 500;
  font-family: var(--coze-font);
  border: 1.5px solid var(--coze-separator);
  border-radius: 18px;
  background: white;
  color: var(--coze-text);
  cursor: pointer;
  transition: all 0.12s;
}
.coze-tag-btn:active { background: rgba(0, 0, 0, 0.03); }
.coze-tag-btn-active {
  background: var(--coze-blue);
  color: white;
  border-color: var(--coze-blue);
}
.coze-tag-selected {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 12px;
  background: var(--coze-blue);
  color: white;
}
.coze-preset-tag {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 8px;
  background: rgba(0, 122, 255, 0.08);
  color: var(--coze-blue);
}
.coze-preset-box {
  padding: 10px 12px;
  background: rgba(0, 0, 0, 0.02);
  border-radius: 10px;
  margin-bottom: 10px;
}

/* --- 滑块 --- */
.coze-slider {
  -webkit-appearance: none;
  width: 100%;
  height: 4px;
  border-radius: 4px;
  background: linear-gradient(to right, rgba(0, 122, 255, 0.2), var(--coze-blue));
  outline: none;
}
.coze-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 28px; height: 28px;
  border-radius: 50%;
  background: white;
  border: none;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
  cursor: pointer;
  transition: box-shadow 0.15s;
}
.coze-slider::-webkit-slider-thumb:active {
  box-shadow: 0 2px 8px rgba(0, 122, 255, 0.25), 0 0 0 3px rgba(0, 122, 255, 0.12);
}
.coze-slider::-moz-range-thumb {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: white;
  border: none;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12);
  cursor: pointer;
}
.coze-slider-tooltip {
  position: absolute;
  top: -28px;
  font-size: 12px;
  font-weight: 600;
  color: var(--coze-text);
  background: white;
  padding: 2px 8px;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  pointer-events: none;
  transform: translateX(-50%);
}

/* --- 芯片按钮（报告头部） --- */
.coze-chip-btn {
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 500;
  font-family: var(--coze-font);
  color: white;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.12s;
}
.coze-chip-btn:active { background: rgba(255, 255, 255, 0.3); }

/* --- 报告内容排版 --- */
.coze-prose { font-size: 14px; line-height: 1.6; color: var(--coze-text); }
.coze-prose :deep(h1) { font-size: 22px; font-weight: 700; margin: 16px 0 8px; }
.coze-prose :deep(h2) { font-size: 18px; font-weight: 600; margin: 14px 0 6px; }
.coze-prose :deep(h3) { font-size: 16px; font-weight: 600; margin: 10px 0 4px; }
.coze-prose :deep(p) { margin: 6px 0; }
.coze-prose :deep(ul), .coze-prose :deep(ol) { padding-left: 20px; margin: 6px 0; }
.coze-prose :deep(li) { margin: 3px 0; }
.coze-prose :deep(table) { width: 100%; border-collapse: collapse; margin: 10px 0; font-size: 13px; }
.coze-prose :deep(th) { background: #f5f5f7; font-weight: 600; padding: 8px 10px; border: 0.5px solid var(--coze-separator); text-align: left; }
.coze-prose :deep(td) { padding: 8px 10px; border: 0.5px solid var(--coze-separator); }
.coze-prose :deep(strong) { font-weight: 600; }
.coze-prose :deep(blockquote) { border-left: 3px solid var(--coze-blue); padding-left: 12px; color: var(--coze-text-secondary); margin: 10px 0; }

/* --- 报告库弹窗 --- */
.library-overlay {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: flex-end;
  justify-content: center;
}
.library-panel {
  width: 100%;
  max-width: 520px;
  max-height: 70vh;
  background: var(--coze-card-bg);
  border-radius: 20px 20px 0 0;
  box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.1);
  display: flex;
  flex-direction: column;
  animation: slideUp 0.25s ease-out;
}
@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}
.library-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 0.5px solid var(--coze-separator);
}
.library-header h2 {
  font-size: 17px;
  font-weight: 700;
  margin: 0;
}
.library-header button {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.05);
  color: var(--coze-text);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.library-list {
  list-style: none;
  margin: 0;
  padding: 8px 0;
  overflow-y: auto;
}
.library-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 16px;
  cursor: pointer;
  transition: background 0.12s;
}
.library-item:active {
  background: rgba(0, 0, 0, 0.04);
}
.library-item-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--coze-text);
  margin: 0;
}
.library-item-time {
  font-size: 12px;
  color: var(--coze-text-secondary);
  margin: 4px 0 0;
}
.library-item-status {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 600;
  padding: 4px 10px;
  border-radius: 999px;
}
.library-item-status.paid {
  background: #e6f4ea;
  color: #1e8e3e;
}
.library-item-status.unpaid {
  background: #fce8e6;
  color: #d93025;
}
.library-empty {
  padding: 40px 16px;
  text-align: center;
  color: var(--coze-text-secondary);
  font-size: 14px;
}

/* --- 减少动画偏好 --- */
@media (prefers-reduced-motion: reduce) {
  .coze-msg-row { animation: none; }
  .coze-dot { animation: none; opacity: 0.5; }
  * { transition-duration: 0.01ms !important; }
}
</style>
