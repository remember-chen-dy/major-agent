<script setup lang="ts">
import { ref, computed, onMounted, nextTick, watch, reactive } from 'vue';

// ============================================================
// 类型定义 - 匹配后端 interaction 配置结构
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
  min?: number;
  max?: number;
  left_label?: string;
  right_label?: string;
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
}

const STORAGE_KEY = 'major-agent-sessions';

// ============================================================
// 状态管理
// ============================================================

const sessions = ref<Session[]>([]);
const currentSessionId = ref('');
const isTyping = ref(false);

// 表单输入状态
const formFieldValues = reactive<Record<string, string>>({});
const sliderValue = ref(50);
const tagSelected = ref<string[]>([]);
const customTagInput = ref('');

const API_BASE = 'http://localhost:8000';

// ============================================================
// 计算属性
// ============================================================

const currentSession = computed(() =>
  sessions.value.find(s => s.id === currentSessionId.value)
);

const currentMessages = computed(() => currentSession.value?.messages ?? []);

/** 当前需要渲染的交互组件（最后一条 AI 消息的 interaction） */
const currentInteraction = computed(() => {
  const msgs = currentMessages.value;
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'ai' && msgs[i].interaction) {
      return msgs[i].interaction;
    }
  }
  return null;
});

/** 当前 session 是否已完成 */
const isComplete = computed(() => currentSession.value?.isComplete ?? false);

/** 最后一条 AI 消息的 report（用于展示最终报告） */
const finalReport = computed(() => {
  const msgs = currentMessages.value;
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].role === 'ai' && (msgs[i] as any).report) {
      return (msgs[i] as any).report;
    }
  }
  return null;
});

// ============================================================
// 本地持久化
// ============================================================

const loadSessions = () => {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed: Session[] = JSON.parse(stored);
      sessions.value = parsed;
      if (parsed.length > 0) {
        currentSessionId.value = parsed[0].id;
      }
    }
  } catch (e) {
    console.error('加载本地会话失败:', e);
  }
};

const saveSessions = () => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions.value));
  } catch (e) {
    console.error('保存会话失败:', e);
  }
};

watch(sessions, saveSessions, { deep: true });

// ============================================================
// API 方法
// ============================================================

/** 创建新会话 */
const createSession = async () => {
  try {
    const res = await fetch(`${API_BASE}/api/assessment/session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    });
    const data = await res.json();

    const session: Session = {
      id: data.session_id,
      title: `新对话 ${sessions.value.length + 1}`,
      created_at: new Date().toISOString(),
      messages: [],
      isComplete: false,
    };

    // 解析新响应格式: { messages: [...], current_step: "..." }
    if (data.messages && Array.isArray(data.messages)) {
      for (const msg of data.messages) {
        session.messages.push({
          role: msg.role || 'ai',
          content: msg.content || '',
          interaction: msg.interaction || null,
        });
      }
    }

    sessions.value.unshift(session);
    currentSessionId.value = session.id;
    resetFormState();
  } catch (e) {
    console.error('创建会话失败:', e);
  }
};

/** 收集当前 interaction 对应的用户输入 */
const collectAnswer = (): any => {
  const interaction = currentInteraction.value;
  if (!interaction) return null;

  switch (interaction.type) {
    case 'form': {
      // 收集表单各字段的值
      const result: Record<string, any> = {};
      if (interaction.fields) {
        for (const field of interaction.fields) {
          const val = formFieldValues[field.id];
          if (field.type === 'number') {
            result[field.id] = val ? Number(val) : 0;
          } else {
            result[field.id] = val || '';
          }
        }
      }
      return result;
    }

    case 'slider':
      return sliderValue.value;

    case 'button_select':
      // 单选，返回选中的 value
      return tagSelected.value[0] || null;

    case 'tag_multi_select':
      // 多选，返回选中的 tags 数组（含自定义输入）
      return [...tagSelected.value];

    default:
      return null;
  }
};

/** 检查当前输入是否有效 */
const isInputValid = computed(() => {
  const interaction = currentInteraction.value;
  if (!interaction) return false;

  switch (interaction.type) {
    case 'form': {
      if (!interaction.fields) return false;
      return interaction.fields.every(f => {
        const val = formFieldValues[f.id];
        return val !== undefined && val !== null && String(val).trim();
      });
    }

    case 'slider':
      return true; // slider 始终有值

    case 'button_select':
      return tagSelected.value.length > 0;

    case 'tag_multi_select': {
      const min = interaction.min_select ?? 1;
      if (min === 0) return true;
      return tagSelected.value.length >= min;
    }

    default:
      return false;
  }
});

/** 提交用户输入 */
const submitInput = async () => {
  console.log('submitInput called, isInputValid:', isInputValid.value);
  console.log('currentInteraction:', currentInteraction.value);
  console.log('formFieldValues:', { ...formFieldValues });

  if (!currentSessionId.value || isTyping.value) return;
  if (!isInputValid.value) return;

  const session = sessions.value.find(s => s.id === currentSessionId.value);
  if (!session) return;

  const answer = collectAnswer();
  if (answer === null) return;

  const interaction = currentInteraction.value!;

  // 添加用户消息（本地显示）
  const userMsg: ChatMessage = {
    role: 'user',
    content: formatUserInput(answer, interaction),
    user_input: answer,
  };
  session.messages.push(userMsg);
  isTyping.value = true;
  await nextTick(scrollToBottom);

  // 更新标题
  const userMsgs = session.messages.filter(m => m.role === 'user');
  if (userMsgs.length === 1) {
    session.title = userMsg.content.slice(0, 20);
  }

  try {
    const res = await fetch(`${API_BASE}/api/assessment/chat/${currentSessionId.value}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answer }),
    });

    if (!res.ok) {
      const errorData = await res.json().catch(() => null);
      throw new Error(errorData?.detail || `HTTP ${res.status}`);
    }

    const data = await res.json();
    console.log('Chat response:', data);

    // 检查是否完成
    if (data.is_complete) {
      session.isComplete = true;
      // 将报告作为消息展示
      if (data.report) {
        session.messages.push({
          role: 'ai',
          content: data.report,
          interaction: null,
        } as any);
      }
      if (data.report_pdf_url) {
        (session as any).reportPdfUrl = data.report_pdf_url;
      }
    } else if (data.messages && Array.isArray(data.messages)) {
      // 问题阶段：添加 AI 消息
      for (const msg of data.messages) {
        session.messages.push({
          role: msg.role || 'ai',
          content: msg.content || '',
          interaction: msg.interaction || null,
        });
      }
    }

    // 重置表单状态
    resetFormState();
  } catch (e) {
    session.messages.push({ role: 'ai', content: '抱歉，网络出现了问题，请稍后重试。' });
  } finally {
    isTyping.value = false;
    await nextTick(scrollToBottom);
  }
};

/** 格式化用户输入显示 */
const formatUserInput = (input: any, interaction: InteractionConfig): string => {
  switch (interaction.type) {
    case 'form': {
      if (typeof input === 'object' && input !== null) {
        return Object.entries(input)
          .map(([key, val]) => {
            const field = interaction.fields?.find(f => f.id === key);
            return `${field?.label || key}: ${val}`;
          })
          .join('，');
      }
      return String(input);
    }

    case 'slider':
      return `选择了 ${input} 分`;

    case 'button_select': {
      const opt = interaction.options?.find(o => o.value === input);
      return opt?.label || String(input);
    }

    case 'tag_multi_select':
      if (Array.isArray(input)) {
        return input.join('、');
      }
      return String(input);

    default:
      return String(input);
  }
};

/** 重置表单状态 */
const resetFormState = () => {
  // 清除 reactive 对象的所有键
  Object.keys(formFieldValues).forEach(key => {
    delete formFieldValues[key];
  });
  sliderValue.value = 50;
  tagSelected.value = [];
  customTagInput.value = '';
};

/** 切换会话 */
const switchSession = (id: string) => {
  currentSessionId.value = id;
  resetFormState();
  nextTick(scrollToBottom);
};

/** 标签选择/取消 */
const toggleTag = (value: string, multiple: boolean) => {
  if (multiple) {
    const idx = tagSelected.value.indexOf(value);
    if (idx >= 0) {
      tagSelected.value.splice(idx, 1);
    } else {
      const interaction = currentInteraction.value;
      const max = interaction?.max_select ?? 999;
      if (tagSelected.value.length < max) {
        tagSelected.value.push(value);
      }
    }
  } else {
    tagSelected.value = [value];
  }
};

/** 添加自定义标签 */
const addCustomTag = () => {
  const val = customTagInput.value.trim();
  if (!val) return;
  const interaction = currentInteraction.value;
  const max = interaction?.max_select ?? 999;
  if (tagSelected.value.length >= max) return;
  if (!tagSelected.value.includes(val)) {
    tagSelected.value.push(val);
  }
  customTagInput.value = '';
};

const isTagSelected = (value: string) => tagSelected.value.includes(value);

/** 移除单个标签 */
const removeTag = (value: string) => {
  const idx = tagSelected.value.indexOf(value);
  if (idx >= 0) tagSelected.value.splice(idx, 1);
};

// ============================================================
// 工具方法
// ============================================================

const messagesRef = ref<HTMLElement | null>(null);
const scrollToBottom = () => {
  if (messagesRef.value) {
    messagesRef.value.scrollTo({
      top: messagesRef.value.scrollHeight,
      behavior: 'smooth',
    });
  }
};

const goBack = () => {
  window.history.length > 1 ? window.history.back() : (window.location.href = '/');
};

/** 删除会话 */
const deleteSession = (id: string) => {
  sessions.value = sessions.value.filter(s => s.id !== id);
  if (currentSessionId.value === id) {
    currentSessionId.value = sessions.value[0]?.id || '';
  }
};

// ============================================================
// 生命周期
// ============================================================

onMounted(() => {
  loadSessions();
  if (sessions.value.length === 0) {
    createSession();
  }
});
</script>

<template>
  <div class="min-h-screen bg-warm-50 flex">
    <!-- ============================================================
         左侧会话列表
         ============================================================ -->
    <aside class="w-72 bg-warm-100/60 border-r border-warm-200 flex flex-col shrink-0">
      <!-- 头部 -->
      <div class="px-5 py-4 border-b border-warm-200">
        <div class="flex items-center justify-between mb-4">
          <button
            @click="goBack"
            class="text-warm-500 hover:text-warm-700 transition-colors"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <h2 class="text-sm font-semibold text-warm-700">对话列表</h2>
          <button
            @click="createSession"
            class="w-7 h-7 rounded-full bg-warm-500 text-white flex items-center justify-center hover:bg-warm-600 transition-colors"
          >
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
          </button>
        </div>
      </div>

      <!-- 会话列表 -->
      <div class="flex-1 overflow-y-auto py-2 px-3 space-y-1">
        <div
          v-for="session in sessions"
          :key="session.id"
          class="group relative"
        >
          <button
            @click="switchSession(session.id)"
            class="w-full text-left px-4 py-3 rounded-xl text-sm transition-colors"
            :class="
              session.id === currentSessionId
                ? 'bg-white/80 text-warm-800 font-medium shadow-sm'
                : 'text-warm-600 hover:bg-white/40'
            "
          >
            <div class="truncate pr-6">{{ session.title }}</div>
            <div class="text-xs text-warm-400 mt-1">
              {{ session.created_at.slice(0, 10) }}
              <span v-if="session.isComplete" class="ml-2 text-green-500">✓ 完成</span>
            </div>
          </button>
          <button
            @click="deleteSession(session.id)"
            class="absolute right-2 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full opacity-0 group-hover:opacity-100 hover:bg-red-100 text-warm-400 hover:text-red-500 transition-all flex items-center justify-center"
          >
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </div>
    </aside>

    <!-- ============================================================
         右侧对话区域
         ============================================================ -->
    <main class="flex-1 flex flex-col min-w-0">
      <!-- 顶部导航 -->
      <header class="sticky top-0 z-50 bg-warm-50/80 backdrop-blur-xl border-b border-warm-200">
        <div class="mx-auto max-w-3xl px-6 py-4">
          <h1 class="text-lg font-bold text-warm-800 text-center truncate">
            {{ currentSession?.title ?? 'AI 志愿顾问' }}
          </h1>
        </div>
      </header>

      <!-- 消息列表 -->
      <div ref="messagesRef" class="flex-1 overflow-y-auto">
        <div class="mx-auto max-w-3xl px-6 py-8 space-y-6">
          <div
            v-for="(msg, i) in currentMessages"
            :key="i"
            class="flex"
            :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
          >
            <div
              class="max-w-[80%] px-5 py-3 text-sm leading-relaxed whitespace-pre-wrap"
              :class="
                msg.role === 'user'
                  ? 'bg-warm-500 text-white rounded-2xl rounded-tr-sm'
                  : 'bg-white/80 backdrop-blur-sm text-warm-800 rounded-2xl rounded-tl-sm shadow-sm'
              "
            >
              <!-- 报告消息（Markdown 样式） -->
              <div
                v-if="msg.role === 'ai' && (msg as any).report"
                class="prose prose-sm prose-warm max-w-none"
                v-html="(msg as any).report"
              />
              <!-- 普通消息 -->
              <template v-else>
                {{ msg.content }}
              </template>

              <!-- ============================================================
                   交互组件渲染
                   ============================================================ -->

              <!--
                form: 多字段表单
                只在最后一条 AI 消息上展示，且该消息必须有 interaction.type === 'form'
              -->
              <div
                v-if="msg.role === 'ai' && msg.interaction?.type === 'form' && i === currentMessages.length - 1 && !isComplete"
                class="mt-3"
              >
                <div class="space-y-3">
                  <div
                    v-for="field in (msg.interaction.fields || [])"
                    :key="field.id"
                  >
                    <label class="block text-xs font-medium text-warm-500 mb-1">
                      {{ field.label }}
                    </label>
                    <input
                      v-model="formFieldValues[field.id]"
                      :type="field.type || 'text'"
                      :placeholder="field.placeholder || ''"
                      class="w-full rounded-xl px-4 py-2.5 text-sm border border-warm-200 bg-white text-warm-800 outline-none focus:border-warm-400 focus:ring-2 focus:ring-warm-200/50 transition-all"
                      @keydown.enter="submitInput"
                    />
                  </div>
                </div>
                <button
                  @click="submitInput"
                  :disabled="!isInputValid"
                  class="w-full mt-3 py-2.5 rounded-xl bg-warm-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-warm-600 transition-colors"
                >
                  提交
                </button>
              </div>

              <!--
                slider: 范围滑块
              -->
              <div
                v-if="msg.role === 'ai' && msg.interaction?.type === 'slider' && i === currentMessages.length - 1 && !isComplete"
                class="mt-3"
              >
                <div class="space-y-3">
                  <!-- 左右标签 -->
                  <div class="flex justify-between text-xs text-warm-500">
                    <span class="max-w-[45%]">{{ msg.interaction.left_label || '低' }}</span>
                    <span class="max-w-[45%] text-right">{{ msg.interaction.right_label || '高' }}</span>
                  </div>

                  <!-- 滑块 -->
                  <div class="relative">
                    <input
                      type="range"
                      v-model.number="sliderValue"
                      :min="msg.interaction.min ?? 0"
                      :max="msg.interaction.max ?? 100"
                      class="w-full h-2 rounded-full appearance-none bg-gradient-to-r from-warm-200 to-warm-400 cursor-pointer slider-input"
                    />
                    <!-- 当前值气泡 -->
                    <div
                      class="absolute -top-8 text-xs font-bold text-warm-700 bg-white px-2 py-1 rounded-lg shadow-sm border border-warm-200"
                      :style="{ left: `calc(${((sliderValue - (msg.interaction.min ?? 0)) / ((msg.interaction.max ?? 100) - (msg.interaction.min ?? 0))) * 100}% - 20px)` }"
                    >
                      {{ sliderValue }}
                    </div>
                  </div>
                </div>
                <button
                  @click="submitInput"
                  class="w-full mt-4 py-2.5 rounded-xl bg-warm-500 text-white text-sm font-medium hover:bg-warm-600 transition-colors"
                >
                  确认
                </button>
              </div>

              <!--
                button_select: 单选按钮组
              -->
              <div
                v-if="msg.role === 'ai' && msg.interaction?.type === 'button_select' && i === currentMessages.length - 1 && !isComplete"
                class="mt-3"
              >
                <div class="flex flex-col gap-2">
                  <button
                    v-for="(opt, idx) in (msg.interaction.options || [])"
                    :key="idx"
                    @click="toggleTag(opt.value, false)"
                    class="w-full text-left px-4 py-3 text-sm border rounded-xl transition-all"
                    :class="
                      isTagSelected(opt.value)
                        ? 'bg-warm-500 text-white border-warm-500 shadow-sm'
                        : 'bg-white text-warm-700 border-warm-200 hover:border-warm-400'
                    "
                  >
                    {{ opt.label }}
                  </button>
                </div>
                <button
                  @click="submitInput"
                  :disabled="!isInputValid"
                  class="w-full mt-3 py-2.5 rounded-xl bg-warm-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-warm-600 transition-colors"
                >
                  确认
                </button>
              </div>

              <!--
                tag_multi_select: 多选标签 + 可选自定义输入
              -->
              <div
                v-if="msg.role === 'ai' && msg.interaction?.type === 'tag_multi_select' && i === currentMessages.length - 1 && !isComplete"
                class="mt-3"
              >
                <!-- 已选标签预览 -->
                <div v-if="tagSelected.length > 0" class="flex flex-wrap gap-1.5 mb-3">
                  <span
                    v-for="tag in tagSelected"
                    :key="tag"
                    class="inline-flex items-center gap-1 px-2.5 py-1 text-xs rounded-full bg-warm-500 text-white"
                  >
                    {{ tag }}
                    <button @click="removeTag(tag)" class="hover:text-warm-200">
                      <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </span>
                </div>

                <!-- 标签选项 -->
                <div class="flex flex-wrap gap-2">
                  <button
                    v-for="(tag, idx) in (msg.interaction.tags || [])"
                    :key="idx"
                    @click="toggleTag(tag, true)"
                    class="px-4 py-2 text-sm border rounded-full transition-all"
                    :class="
                      isTagSelected(tag)
                        ? 'bg-warm-500 text-white border-warm-500'
                        : 'bg-white text-warm-700 border-warm-200 hover:border-warm-400'
                    "
                  >
                    {{ tag }}
                  </button>
                </div>

                <!-- 自定义输入 -->
                <div v-if="msg.interaction.allow_custom" class="flex gap-2 mt-2">
                  <input
                    v-model="customTagInput"
                    :placeholder="msg.interaction.custom_placeholder || '自定义输入...'"
                    class="flex-1 rounded-xl px-4 py-2 text-sm border border-warm-200 bg-white text-warm-800 outline-none focus:border-warm-400 transition-all"
                    @keydown.enter="addCustomTag"
                  />
                  <button
                    @click="addCustomTag"
                    :disabled="!customTagInput.trim()"
                    class="shrink-0 px-4 py-2 rounded-xl bg-warm-100 text-warm-600 text-sm font-medium hover:bg-warm-200 disabled:opacity-40 transition-colors"
                  >
                    添加
                  </button>
                </div>

                <!-- 提示文字 -->
                <p v-if="msg.interaction.min_select === 0" class="mt-2 text-xs text-warm-400">
                  不选也可以，直接确认即可跳过
                </p>

                <button
                  @click="submitInput"
                  :disabled="!isInputValid"
                  class="w-full mt-3 py-2.5 rounded-xl bg-warm-500 text-white text-sm font-medium disabled:opacity-40 disabled:cursor-not-allowed hover:bg-warm-600 transition-colors"
                >
                  确认
                </button>
              </div>
            </div>
          </div>

          <!-- 输入中状态 -->
          <div v-if="isTyping" class="flex justify-start">
            <div class="bg-white/80 backdrop-blur-sm rounded-2xl rounded-tl-sm px-5 py-3 shadow-sm">
              <div class="flex gap-1.5">
                <div class="w-2 h-2 rounded-full bg-warm-300 animate-bounce" style="animation-delay: 0s" />
                <div class="w-2 h-2 rounded-full bg-warm-300 animate-bounce" style="animation-delay: 0.15s" />
                <div class="w-2 h-2 rounded-full bg-warm-300 animate-bounce" style="animation-delay: 0.3s" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
main > div:first-child::-webkit-scrollbar {
  display: none;
}
main > div:first-child {
  -ms-overflow-style: none;
  scrollbar-width: none;
}

/* 滑块样式 */
.slider-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #c4b49a;
  cursor: pointer;
  border: 3px solid white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

.slider-input::-moz-range-thumb {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #c4b49a;
  cursor: pointer;
  border: 3px solid white;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
}

/* Markdown 内容样式 */
.prose-warm :deep(h1) { font-size: 1.5rem; font-weight: 700; margin-top: 1rem; margin-bottom: 0.5rem; color: #1a1a2e; }
.prose-warm :deep(h2) { font-size: 1.25rem; font-weight: 600; margin-top: 1rem; margin-bottom: 0.5rem; color: #16213e; }
.prose-warm :deep(h3) { font-size: 1.1rem; font-weight: 600; margin-top: 0.75rem; margin-bottom: 0.25rem; }
.prose-warm :deep(p) { margin: 0.5rem 0; }
.prose-warm :deep(ul), .prose-warm :deep(ol) { padding-left: 1.5rem; margin: 0.5rem 0; }
.prose-warm :deep(li) { margin: 0.25rem 0; }
.prose-warm :deep(table) { width: 100%; border-collapse: collapse; margin: 0.75rem 0; font-size: 0.8rem; }
.prose-warm :deep(th) { background: #f0f0f0; font-weight: 600; padding: 8px 12px; border: 1px solid #ddd; text-align: left; }
.prose-warm :deep(td) { padding: 8px 12px; border: 1px solid #ddd; }
.prose-warm :deep(tr:nth-child(even)) { background: #fafafa; }
.prose-warm :deep(strong) { color: #16213e; }
.prose-warm :deep(blockquote) { border-left: 4px solid #e94560; padding-left: 16px; color: #555; margin: 12px 0; }
</style>
