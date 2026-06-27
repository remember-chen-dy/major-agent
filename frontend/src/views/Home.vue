<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../stores/auth';
import { api } from '../api';

const route = useRoute();

// ============================================================
// 状态管理
// ============================================================

const router = useRouter();
const authStore = useAuthStore();

/** 导航栏滚动状态 */
const isScrolled = ref(false);

/** 移动端菜单打开状态 */
const isMenuOpen = ref(false);

/** 最新报告状态 */
const latestReport = ref<any>(null);
const reportLoading = ref(true);
const reportError = ref('');

// ============================================================
// 用户评价数据
// ============================================================

interface Testimonial {
  quote: string;
  name: string;
  title: string;
  score: number;
}

const testimonials = ref<Testimonial[]>([
  {
    quote: '孩子成绩中上但不知道选什么专业，做了这个测评后发现她适合心理学方向。报告里还列出了开设这个专业的院校梯度，非常实用，志愿填报那几天全靠它了。',
    name: '陈女士',
    title: '考生家长 · 女儿考入华东师范大学',
    score: 5,
  },
  {
    quote: '说实话一开始没抱太大期望，结果AI问了我十几分钟的问题，比我班主任了解我还准。推荐了数据科学这个方向，我之前完全没想过，现在学了一学期真的很喜欢。',
    name: '赵同学',
    title: '2025届考生 · 就读于电子科技大学',
    score: 5,
  },
  {
    quote: '我是复读生，去年随便选了个专业读了一年很痛苦。今年重新做了这个测评，报告里把我的性格、兴趣分析得很透彻，转到了真正适合我的专业，感谢！',
    name: '刘同学',
    title: '2025届考生 · 就读于武汉大学',
    score: 5,
  },
  {
    quote: '家里三代人都没上过大学，志愿填报完全两眼一抹黑。这个报告把每个推荐专业的就业方向、薪资水平都列清楚了，让我们这些普通家庭也能做出理性选择。',
    name: '周先生',
    title: '考生家长 · 儿子考入西安交通大学',
    score: 5,
  },
  {
    quote: '我理科成绩不错但偏科严重，AI分析后建议我走工科而不是纯理科，还给出了具体的专业排序。最后按建议填报的，六个志愿全部命中第一专业，省了好多纠结。',
    name: '孙同学',
    title: '2025届考生 · 就读于哈尔滨工业大学',
    score: 4,
  },
]);

/** 当前激活的评价索引（移动端轮播） */
const activeTestimonial = ref(0);

/** 触摸滑动状态 */
const touchStartX = ref(0);
const touchDeltaX = ref(0);
const isSwiping = ref(false);

const onTouchStart = (e: TouchEvent) => {
  touchStartX.value = e.touches[0].clientX;
  touchDeltaX.value = 0;
  isSwiping.value = true;
};

const onTouchMove = (e: TouchEvent) => {
  if (!isSwiping.value) return;
  touchDeltaX.value = e.touches[0].clientX - touchStartX.value;
};

const onTouchEnd = () => {
  if (!isSwiping.value) return;
  isSwiping.value = false;
  const threshold = 50;
  if (touchDeltaX.value < -threshold && activeTestimonial.value < testimonials.value.length - 1) {
    activeTestimonial.value++;
  } else if (touchDeltaX.value > threshold && activeTestimonial.value > 0) {
    activeTestimonial.value--;
  }
  touchDeltaX.value = 0;
};

// ============================================================
// 滚动监听 - 导航栏背景透明度变化
// ============================================================

const handleScroll = () => {
  isScrolled.value = window.scrollY > 20;
};

// ============================================================
// 报告相关
// ============================================================

const loadLatestReport = async () => {
  // 从报告页点击"返回首页"时，强制展示最初的落地页
  if (route.query.landing === '1') {
    reportLoading.value = false;
    return;
  }

  if (!authStore.userId) {
    reportLoading.value = false;
    return;
  }

  reportLoading.value = true;
  reportError.value = '';
  try {
    const data = await api.getLatestReport(authStore.userId);
    latestReport.value = data.report || null;

    // 未支付的报告直接跳转到支付页面，避免首页重复展示
    if (latestReport.value && !latestReport.value.is_paid) {
      const sessionId = latestReport.value.session_id;
      if (sessionId) {
        router.replace(`/report/${sessionId}/unlock`);
        return;
      }
    }
  } catch (error) {
    console.error('加载最新报告失败:', error);
    reportError.value = '加载报告失败，请稍后重试';
  } finally {
    reportLoading.value = false;
  }
};

const goToReportLibrary = () => {
  router.push('/assessment?reportLibrary=1');
};

const goToReport = () => {
  const sessionId = latestReport.value?.session_id;
  if (sessionId) {
    router.push(`/report/${sessionId}`);
  }
};

const handleStartAssessment = () => {
  router.push('/assessment');
};

const restartAssessment = async () => {
  router.push('/assessment');
};

// ============================================================
// Markdown 渲染（与 Report.vue 保持一致）
// ============================================================

const escapeHtml = (text: string) =>
  text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

function renderInline(text: string) {
  return escapeHtml(text)
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code>$1</code>');
}

function renderMarkdown(md: string): string {
  if (!md || !md.trim()) return '<p>报告内容为空。</p>';

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

const reportHtml = computed(() => {
  if (!latestReport.value?.report_content) return '';
  return renderMarkdown(latestReport.value.report_content);
});

// ============================================================
// 生命周期
// ============================================================

onMounted(async () => {
  // 先登录/恢复用户态
  try {
    await authStore.login();
  } catch (error) {
    console.error('登录失败:', error);
  }

  // 加载最新报告
  await loadLatestReport();

  // 如果没有报告，保持原来的首页 landing 并启用滚动动画
  if (!latestReport.value) {
    window.addEventListener('scroll', handleScroll, { passive: true });
    initScrollAnimations();
  }
});

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll);
});

// ============================================================
// GSAP 滚动动画初始化
// ============================================================

const initScrollAnimations = async () => {
  const { default: gsap } = await import('gsap');
  const { ScrollTrigger } = await import('gsap/ScrollTrigger');

  gsap.registerPlugin(ScrollTrigger);

  gsap.utils.toArray('.animate-on-scroll').forEach((el, index) => {
    gsap.to(el as Element, {
      opacity: 1,
      y: 0,
      duration: 0.35,
      delay: index * 0.08,
      ease: 'power3.out',
      scrollTrigger: {
        trigger: el as Element,
        start: 'top 85%',
        toggleActions: 'play none none none',
      },
    });
  });

  gsap.utils.toArray('.step-item').forEach((el, index) => {
    gsap.from(el as Element, {
      opacity: 0,
      y: 40,
      duration: 0.3,
      delay: index * 0.1,
      ease: 'power2.out',
      scrollTrigger: {
        trigger: el as Element,
        start: 'top 85%',
        toggleActions: 'play none none none',
      },
    });
  });
};

// ============================================================
// 事件处理
// ============================================================

/** 了解更多 - 滚动到特色功能区 */
const handleLearnMore = () => {
  document.getElementById('features')?.scrollIntoView({ behavior: 'smooth' });
};

/** 切换移动端菜单 */
const toggleMenu = () => {
  isMenuOpen.value = !isMenuOpen.value;
};

/** 关闭移动端菜单 */
const closeMenu = () => {
  isMenuOpen.value = false;
};

</script>

<template>
  <div class="min-h-screen overflow-hidden bg-[#fafbff]">
    <!-- 加载中 -->
    <div v-if="reportLoading" class="flex min-h-screen items-center justify-center">
      <div class="text-center text-warm-500">
        <div class="mx-auto mb-4 h-8 w-8 animate-spin rounded-full border-4 border-warm-200 border-t-warm-500"></div>
        <p>正在加载报告...</p>
      </div>
    </div>

    <!-- 加载失败 -->
    <div v-else-if="reportError" class="flex min-h-screen flex-col items-center justify-center px-6">
      <p class="text-warm-600">{{ reportError }}</p>
      <button class="btn-primary mt-4" @click="loadLatestReport">重试</button>
    </div>

    <!-- ============================================================
         报告视图（有最新报告时直接展示）
         ============================================================ -->
    <template v-else-if="latestReport">
      <main class="report-page">
        <header class="report-nav">
          <button class="home-btn" @click="router.push({ path: '/', query: { landing: '1' } })">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
              <polyline points="9 22 9 12 15 12 15 22"/>
            </svg>
            返回首页
          </button>
          <strong>{{ latestReport.report_title }}</strong>
          <button @click="goToReportLibrary">报告库</button>
        </header>

        <section v-if="latestReport.is_paid" class="report-shell">
          <div class="report-title">
            <p>AI 志愿规划</p>
            <h1>{{ latestReport.report_title }}</h1>
            <p class="report-time">生成于 {{ new Date(latestReport.created_at).toLocaleString() }}</p>
          </div>
          <div class="report-content" v-html="reportHtml"></div>
          <div class="report-actions">
            <button class="btn-primary" @click="restartAssessment">重新测评</button>
            <button class="btn-secondary" @click="goToReportLibrary">查看报告库</button>
          </div>
        </section>

      </main>
    </template>

    <!-- ============================================================
         引导视图（暂无报告时展示原有落地页）
         ============================================================ -->
    <template v-else>
      <!-- 顶部导航栏 -->
      <nav class="navbar" :class="{ scrolled: isScrolled }">
        <div class="mx-auto flex h-full max-w-7xl items-center justify-between px-6">
          <!-- Logo -->
          <div class="flex items-center gap-2.5">
            <div class="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-blue-600 to-blue-500 text-white shadow-sm shadow-blue-500/20">
              <svg class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
              </svg>
            </div>
            <span class="text-lg font-bold tracking-tight text-slate-800">智志愿</span>
          </div>

          <!-- 桌面端导航链接 -->
          <div class="hidden items-center gap-8 md:flex">
            <a href="#features" class="text-sm font-medium text-slate-400 transition-colors duration-200 hover:text-slate-700">
              核心优势
            </a>
            <a href="#steps" class="text-sm font-medium text-slate-400 transition-colors duration-200 hover:text-slate-700">
              使用流程
            </a>
            <button class="btn-primary !rounded-lg !px-5 !py-2.5 text-sm" @click="handleStartAssessment">
              开始测评
            </button>
          </div>

          <!-- 移动端汉堡菜单按钮 -->
          <button class="flex h-11 w-11 items-center justify-center rounded-xl md:hidden" @click="toggleMenu" aria-label="菜单">
            <div class="flex h-5 w-5 flex-col justify-between">
              <span class="block h-0.5 w-full rounded-full bg-slate-700 transition-all duration-300" :class="{ 'translate-y-2 rotate-45': isMenuOpen }" />
              <span class="block h-0.5 w-full rounded-full bg-slate-700 transition-all duration-300" :class="{ 'opacity-0': isMenuOpen }" />
              <span class="block h-0.5 w-full rounded-full bg-slate-700 transition-all duration-300" :class="{ '-translate-y-2 -rotate-45': isMenuOpen }" />
            </div>
          </button>
        </div>

        <!-- 移动端下拉菜单 -->
        <transition name="slide-down">
          <div v-if="isMenuOpen" class="border-t border-slate-100 bg-white/95 px-6 py-4 backdrop-blur-xl md:hidden">
            <div class="flex flex-col gap-2">
              <a href="#features" class="rounded-lg px-4 py-3 text-base font-medium text-slate-600 hover:bg-slate-50" @click="closeMenu">
                核心优势
              </a>
              <a href="#steps" class="rounded-lg px-4 py-3 text-base font-medium text-slate-600 hover:bg-slate-50" @click="closeMenu">
                使用流程
              </a>
              <button class="btn-primary mt-2 w-full text-center !rounded-lg" @click="handleStartAssessment">
                开始测评
              </button>
            </div>
          </div>
        </transition>
      </nav>

      <!-- ============================================================
           2. Hero区域
           ============================================================ -->
      <section class="relative flex flex-col items-center justify-center overflow-hidden px-6 pt-32 pb-16 md:pt-40 md:pb-24">
        <!-- 背景装饰 - 专业蓝色渐变光晕 -->
        <div class="pointer-events-none absolute inset-0">
          <div class="absolute -top-24 left-1/4 h-[500px] w-[500px] rounded-full bg-blue-100/40 blur-[100px]" />
          <div class="absolute -bottom-32 right-1/4 h-[400px] w-[400px] rounded-full bg-indigo-100/30 blur-[80px]" />
          <div class="absolute left-1/2 top-1/3 h-72 w-72 -translate-x-1/2 rounded-full bg-sky-100/40 blur-[60px]" />
          <!-- 网格装饰 -->
          <div class="absolute inset-0 opacity-[0.015]" style="background-image: radial-gradient(circle, #1e293b 1px, transparent 1px); background-size: 32px 32px;" />
        </div>

        <div class="relative z-10 mx-auto max-w-4xl text-center">
          <!-- 标签 -->
          <div class="animate-fade-in-up mb-6 inline-flex items-center gap-2 rounded-full border border-blue-100 bg-blue-50/80 px-4 py-1.5 text-xs font-medium text-blue-600 backdrop-blur-sm">
            <span class="h-1.5 w-1.5 rounded-full bg-blue-500 animate-pulse" />
            AI 驱动 · 科学选专业
          </div>

          <!-- 大标题 -->
          <h1 class="animate-fade-in-up text-4xl font-extrabold leading-tight tracking-tight text-slate-900 md:text-6xl lg:text-7xl">
            让 AI 帮你找到<br class="hidden md:block" />
            <span class="gradient-text">最适合的专业</span>
          </h1>

          <!-- 副标题 -->
          <p class="mx-auto mt-6 max-w-2xl text-lg font-normal text-slate-500 md:text-xl md:leading-relaxed">
            基于深度对话式测评，从兴趣、性格、能力多维度分析<br class="hidden md:block" />
            为你生成个性化的专业推荐与志愿规划报告
          </p>

          <!-- CTA按钮 -->
          <div class="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
            <button class="btn-primary w-full sm:w-auto" @click="handleStartAssessment">
              免费开始测评
            </button>
            <button class="btn-secondary w-full sm:w-auto" @click="handleLearnMore">
              了解更多 ↓
            </button>
          </div>

          <!-- 信任指标 -->
          <div class="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-slate-400">
            <span class="flex items-center gap-1.5">
              <svg class="h-3.5 w-3.5 text-blue-400" fill="currentColor" viewBox="0 0 20 20"><path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/></svg>
              免费测评
            </span>
            <span class="flex items-center gap-1.5">
              <svg class="h-3.5 w-3.5 text-blue-400" fill="currentColor" viewBox="0 0 20 20"><path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/></svg>
              5 分钟完成
            </span>
            <span class="flex items-center gap-1.5">
              <svg class="h-3.5 w-3.5 text-blue-400" fill="currentColor" viewBox="0 0 20 20"><path d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"/></svg>
              已有 10,000+ 考生使用
            </span>
          </div>
        </div>

        <!-- iPhone模型 / 对话界面预览 -->
        <div class="mt-16 animate-fade-in-up [animation-delay:0.15s] w-full max-w-md opacity-0 md:mt-20">
          <div class="iphone-mockup">
            <!-- 状态栏 -->
            <div class="flex items-center justify-between border-b border-slate-100 px-6 pt-10 pb-3">
              <span class="text-xs font-semibold text-slate-700">9:41</span>
              <div class="flex items-center gap-1.5">
                <svg class="h-3 w-3 text-slate-500" fill="currentColor" viewBox="0 0 24 24"><path d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.08 2.93 1 9zm8 8l3 3 3-3c-1.65-1.66-4.34-1.66-6 0zm-4-4l2 2c2.76-2.76 7.24-2.76 10 0l2-2C15.14 9.14 8.87 9.14 5 13z"/></svg>
                <svg class="h-3 w-3 text-slate-500" fill="currentColor" viewBox="0 0 24 24"><path d="M15.67 4H14V2h-4v2H8.33C7.6 4 7 4.6 7 5.33v15.33C7 21.4 7.6 22 8.33 22h7.33c.74 0 1.34-.6 1.34-1.33V5.33C17 4.6 16.4 4 15.67 4z"/></svg>
              </div>
            </div>
            <!-- 对话区域 -->
            <div class="bg-gradient-to-b from-slate-50 to-white px-4 py-6">
              <!-- AI 消息 -->
              <div class="mb-3 flex gap-2">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-blue-500 shadow-sm shadow-blue-500/20">
                  <svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                  </svg>
                </div>
                <div class="rounded-2xl rounded-tl-md bg-white px-4 py-3 text-sm text-slate-600 shadow-sm ring-1 ring-slate-100">
                  你好！我是你的 AI 志愿顾问。让我们一起探索最适合你的专业方向吧
                </div>
              </div>
              <!-- 用户消息 -->
              <div class="mb-3 flex justify-end gap-2">
                <div class="rounded-2xl rounded-tr-md bg-gradient-to-r from-blue-600 to-blue-500 px-4 py-3 text-sm text-white shadow-sm shadow-blue-500/20">
                  我对计算机和数学都很感兴趣...
                </div>
              </div>
              <!-- AI 消息 -->
              <div class="mb-3 flex gap-2">
                <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-blue-500 shadow-sm shadow-blue-500/20">
                  <svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                  </svg>
                </div>
                <div class="rounded-2xl rounded-tl-md bg-white px-4 py-3 text-sm text-slate-600 shadow-sm ring-1 ring-slate-100">
                  根据你的兴趣和优势，我为你推荐了以下 3 个专业方向👇
                </div>
              </div>
              <!-- 推荐卡片 -->
              <div class="flex gap-2 overflow-x-auto pb-2">
                <div class="shrink-0 rounded-xl bg-white p-3 text-left shadow-sm ring-1 ring-slate-100">
                  <p class="text-xs font-semibold text-blue-600">计算机科学与技术</p>
                  <p class="mt-1 text-xs text-slate-400">匹配度 <span class="font-semibold text-emerald-500">95%</span></p>
                </div>
                <div class="shrink-0 rounded-xl bg-white p-3 text-left shadow-sm ring-1 ring-slate-100">
                  <p class="text-xs font-semibold text-blue-600">数据科学与大数据</p>
                  <p class="mt-1 text-xs text-slate-400">匹配度 <span class="font-semibold text-emerald-500">92%</span></p>
                </div>
                <div class="shrink-0 rounded-xl bg-white p-3 text-left shadow-sm ring-1 ring-slate-100">
                  <p class="text-xs font-semibold text-blue-600">人工智能</p>
                  <p class="mt-1 text-xs text-slate-400">匹配度 <span class="font-semibold text-emerald-500">89%</span></p>
                </div>
              </div>
            </div>
            <!-- 底部输入框 -->
            <div class="border-t border-slate-100 bg-white px-4 py-3">
              <div class="flex items-center gap-2 rounded-full bg-slate-50 px-4 py-2.5">
                <span class="flex-1 text-sm text-slate-300">输入消息...</span>
                <div class="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-r from-blue-600 to-blue-500 shadow-sm shadow-blue-500/20">
                  <svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ============================================================
           3. 核心优势卡片区
           ============================================================ -->
      <section id="features" class="bg-slate-50/60 px-6 py-20 md:py-32">
        <div class="mx-auto max-w-6xl">
          <h2 class="animate-on-scroll text-center text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">
            为什么选择我们
          </h2>
          <p class="mx-auto mt-4 max-w-xl text-center text-base text-slate-400 md:text-lg">
            融合 AI 技术与教育大数据，让选专业不再盲目
          </p>

          <!-- 卡片网格 -->
          <div class="mt-14 grid gap-5 md:grid-cols-2 lg:grid-cols-3">
            <!-- 卡片1：智能对话测评 -->
            <div class="animate-on-scroll card-hover group rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-100">
              <div class="mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-blue-50 text-blue-600 transition-colors group-hover:bg-blue-100">
                <svg class="h-6 w-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
                </svg>
              </div>
              <h3 class="text-lg font-bold text-slate-800">智能对话测评</h3>
              <p class="mt-3 text-sm leading-relaxed text-slate-400">
                以自然对话替代传统问卷，AI 实时理解你的兴趣与能力，5 分钟完成全面评估。
              </p>
            </div>

            <!-- 卡片2：多维数据分析 -->
            <div class="animate-on-scroll card-hover group rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-100">
              <div class="mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 transition-colors group-hover:bg-emerald-100">
                <svg class="h-6 w-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
                </svg>
              </div>
              <h3 class="text-lg font-bold text-slate-800">多维数据分析</h3>
              <p class="mt-3 text-sm leading-relaxed text-slate-400">
                综合百万考生真实数据与专业画像，从兴趣、性格、成绩等多维度精准匹配。
              </p>
            </div>

            <!-- 卡片3：专业报告解读 -->
            <div class="animate-on-scroll card-hover group rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-100 md:col-span-2 lg:col-span-1">
              <div class="mb-6 flex h-12 w-12 items-center justify-center rounded-xl bg-violet-50 text-violet-600 transition-colors group-hover:bg-violet-100">
                <svg class="h-6 w-6" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
              </div>
              <h3 class="text-lg font-bold text-slate-800">专业报告解读</h3>
              <p class="mt-3 text-sm leading-relaxed text-slate-400">
                生成包含专业推荐、职业前景、院校建议的完整报告，帮你全面了解每个选择。
              </p>
            </div>
          </div>
        </div>
      </section>

      <!-- ============================================================
           4. 流程展示区
           ============================================================ -->
      <section id="steps" class="px-6 py-20 md:py-32">
        <div class="mx-auto max-w-5xl">
          <h2 class="animate-on-scroll text-center text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">
            三步找到理想专业
          </h2>
          <p class="mx-auto mt-4 max-w-lg text-center text-base text-slate-400">
            简单高效，全程不超过 5 分钟
          </p>

          <!-- 桌面端水平步骤条 -->
          <div class="mt-16 hidden md:block">
            <div class="relative flex items-start justify-between">
              <div class="gradient-line absolute left-[16%] right-[16%] top-7" />

              <div class="step-item relative z-10 flex w-1/3 flex-col items-center text-center">
                <div class="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-blue-500 text-lg font-bold text-white shadow-lg shadow-blue-500/20">
                  1
                </div>
                <h3 class="mt-6 text-lg font-bold text-slate-800">开始对话</h3>
                <p class="mt-2 max-w-[220px] text-sm leading-relaxed text-slate-400">回答 AI 的问题，轻松自然，就像和朋友聊天</p>
              </div>

              <div class="step-item relative z-10 flex w-1/3 flex-col items-center text-center">
                <div class="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-blue-500 text-lg font-bold text-white shadow-lg shadow-blue-500/20">
                  2
                </div>
                <h3 class="mt-6 text-lg font-bold text-slate-800">AI 深度分析</h3>
                <p class="mt-2 max-w-[220px] text-sm leading-relaxed text-slate-400">综合你的兴趣、性格与成绩，精准匹配专业方向</p>
              </div>

              <div class="step-item relative z-10 flex w-1/3 flex-col items-center text-center">
                <div class="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-blue-500 text-lg font-bold text-white shadow-lg shadow-blue-500/20">
                  3
                </div>
                <h3 class="mt-6 text-lg font-bold text-slate-800">获取报告</h3>
                <p class="mt-2 max-w-[220px] text-sm leading-relaxed text-slate-400">获得专业推荐报告，包含志愿填报行动建议</p>
              </div>
            </div>
          </div>

          <!-- 移动端垂直步骤条 -->
          <div class="mt-12 md:hidden">
            <div class="relative">
              <div class="gradient-line-vertical absolute left-7 top-0 bottom-0" />

              <div class="step-item relative z-10 mb-10 flex items-start gap-4 pl-16">
                <div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-blue-500 text-lg font-bold text-white shadow-lg shadow-blue-500/20">
                  1
                </div>
                <div>
                  <h3 class="text-lg font-bold text-slate-800">开始对话</h3>
                  <p class="mt-1 text-sm text-slate-400">回答 AI 的问题，轻松自然，就像和朋友聊天</p>
                </div>
              </div>

              <div class="step-item relative z-10 mb-10 flex items-start gap-4 pl-16">
                <div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-blue-500 text-lg font-bold text-white shadow-lg shadow-blue-500/20">
                  2
                </div>
                <div>
                  <h3 class="text-lg font-bold text-slate-800">AI 深度分析</h3>
                  <p class="mt-1 text-sm text-slate-400">综合你的兴趣、性格与成绩，精准匹配专业方向</p>
                </div>
              </div>

              <div class="step-item relative z-10 flex items-start gap-4 pl-16">
                <div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-blue-500 text-lg font-bold text-white shadow-lg shadow-blue-500/20">
                  3
                </div>
                <div>
                  <h3 class="text-lg font-bold text-slate-800">获取报告</h3>
                  <p class="mt-1 text-sm text-slate-400">获得专业推荐报告，包含志愿填报行动建议</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- ============================================================
           5. 用户评价区
           ============================================================ -->
      <section class="bg-slate-50/60 px-6 py-20 md:py-32">
        <div class="mx-auto max-w-6xl">
          <h2 class="animate-on-scroll text-center text-3xl font-bold tracking-tight text-slate-900 md:text-4xl">
            真实用户反馈
          </h2>
          <p class="mx-auto mt-4 max-w-xl text-center text-base text-slate-400">
            超过 10,000+ 考生和家长已通过测评找到方向
          </p>

          <!-- 桌面端网格布局 -->
          <div class="mt-14 hidden grid-cols-1 gap-5 md:grid md:grid-cols-3">
            <div
              v-for="(item, index) in testimonials.slice(0, 3)"
              :key="index"
              class="animate-on-scroll card-hover rounded-2xl bg-white p-8 shadow-sm ring-1 ring-slate-100"
            >
              <!-- 星级 -->
              <div class="mb-4 flex gap-0.5">
                <svg v-for="s in 5" :key="s" class="h-4 w-4" :class="s <= item.score ? 'text-amber-400' : 'text-slate-200'" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                </svg>
              </div>
              <p class="text-sm leading-relaxed text-slate-500">
                {{ item.quote }}
              </p>
              <div class="mt-6 flex items-center gap-3 border-t border-slate-50 pt-4">
                <div class="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-500 text-xs font-bold text-white">
                  {{ item.name.charAt(0) }}
                </div>
                <div>
                  <p class="text-sm font-semibold text-slate-700">{{ item.name }}</p>
                  <p class="mt-0.5 text-xs text-slate-400">{{ item.title }}</p>
                </div>
              </div>
            </div>
          </div>

          <!-- 移动端轮播布局（支持手指滑动） -->
          <div
            class="mt-8 md:hidden"
            @touchstart.passive="onTouchStart"
            @touchmove.passive="onTouchMove"
            @touchend="onTouchEnd"
          >
            <div class="overflow-hidden rounded-2xl">
              <div
                class="flex transition-transform duration-300 ease-out"
                :style="{ transform: `translateX(calc(-${activeTestimonial * 100}% + ${isSwiping ? touchDeltaX : 0}px))` }"
              >
                <div
                  v-for="(item, index) in testimonials"
                  :key="index"
                  class="w-full shrink-0 bg-white p-7 shadow-sm ring-1 ring-slate-100"
                  :class="index === 0 ? 'rounded-l-2xl' : index === testimonials.length - 1 ? 'rounded-r-2xl' : ''"
                >
                  <!-- 星级 -->
                  <div class="mb-3 flex gap-0.5">
                    <svg v-for="s in 5" :key="s" class="h-4 w-4" :class="s <= item.score ? 'text-amber-400' : 'text-slate-200'" fill="currentColor" viewBox="0 0 20 20">
                      <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
                    </svg>
                  </div>
                  <p class="text-sm leading-relaxed text-slate-500">
                    {{ item.quote }}
                  </p>
                  <div class="mt-5 flex items-center gap-3 border-t border-slate-50 pt-4">
                    <div class="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-br from-blue-500 to-indigo-500 text-xs font-bold text-white">
                      {{ item.name.charAt(0) }}
                    </div>
                    <div>
                      <p class="text-sm font-semibold text-slate-700">{{ item.name }}</p>
                      <p class="mt-0.5 text-xs text-slate-400">{{ item.title }}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <!-- 指示器 -->
            <div class="mt-5 flex items-center justify-center gap-2">
              <button
                v-for="(_, index) in testimonials"
                :key="index"
                class="h-1.5 rounded-full transition-all duration-300"
                :class="activeTestimonial === index ? 'w-6 bg-gradient-to-r from-blue-500 to-indigo-500' : 'w-1.5 bg-slate-300'"
                @click="activeTestimonial = index"
              />
            </div>
          </div>
        </div>
      </section>

      <!-- ============================================================
           6. 底部CTA区
           ============================================================ -->
      <section class="relative overflow-hidden px-6 py-20 md:py-32">
        <div class="pointer-events-none absolute inset-0">
          <div class="absolute left-1/2 top-1/2 h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-gradient-to-br from-blue-100/40 to-indigo-100/30 blur-[80px]" />
        </div>

        <div class="relative z-10 mx-auto max-w-3xl text-center">
          <h2 class="animate-on-scroll text-3xl font-bold tracking-tight text-slate-900 md:text-5xl">
            准备好找到<br class="md:hidden" />
            <span class="gradient-text">最适合的专业</span>
            了吗？
          </h2>
          <p class="mx-auto mt-4 max-w-lg text-base text-slate-400 md:text-lg">
            只需 5 分钟，AI 将为你量身定制专业推荐报告
          </p>

          <button class="btn-primary mx-auto mt-8 text-lg" @click="handleStartAssessment">
            立即开始测评
          </button>

          <div class="mt-12 flex flex-wrap items-center justify-center gap-8">
            <div class="flex items-center gap-2 text-sm text-slate-400">
              <svg class="h-5 w-5 text-blue-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
              </svg>
              <span>数据安全加密</span>
            </div>
            <div class="flex items-center gap-2 text-sm text-slate-400">
              <svg class="h-5 w-5 text-blue-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
              </svg>
              <span>AI 技术驱动</span>
            </div>
            <div class="flex items-center gap-2 text-sm text-slate-400">
              <svg class="h-5 w-5 text-blue-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
              </svg>
              <span>10,000+ 考生信赖</span>
            </div>
          </div>
        </div>
      </section>

      <!-- ============================================================
           7. 页脚
           ============================================================ -->
      <footer class="border-t border-slate-100 bg-slate-50/40 px-6 py-10">
        <div class="mx-auto max-w-6xl">
          <div class="flex flex-col items-center justify-between gap-4 md:flex-row">
            <p class="text-sm text-slate-400">
              &copy; {{ new Date().getFullYear() }} 智志愿 · AI 志愿规划平台
            </p>
            <a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer" class="text-sm text-slate-400 transition-colors duration-200 hover:text-slate-600">
              陕ICP备2026015941号-1
            </a>
            <div class="flex items-center gap-6">
              <a href="#privacy" class="text-sm text-slate-400 transition-colors duration-200 hover:text-slate-600">
                隐私政策
              </a>
              <a href="#contact" class="text-sm text-slate-400 transition-colors duration-200 hover:text-slate-600">
                联系我们
              </a>
              <a href="#terms" class="text-sm text-slate-400 transition-colors duration-200 hover:text-slate-600">
                使用条款
              </a>
            </div>
          </div>
        </div>
      </footer>
    </template>
  </div>
</template>

<style scoped>
/* 过渡动画 */
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-10px);
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 滚动条美化 */
::-webkit-scrollbar {
  width: 6px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(100, 116, 139, 0.15);
  border-radius: 3px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(100, 116, 139, 0.25);
}

/* 报告页样式 */
.report-page {
  min-height: 100vh;
  min-height: 100dvh;
  background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 50%, #e2e8f0 100%);
  color: #1e293b;
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
.report-nav button {
  border: none;
  border-radius: 10px;
  padding: 9px 14px;
  background: #1f6feb;
  color: white;
  font-weight: 750;
  cursor: pointer;
  white-space: nowrap;
}
.report-nav button:first-child {
  background: transparent;
  color: #1f6feb;
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
.report-actions {
  display: flex;
  gap: 12px;
  justify-content: center;
  margin-top: 28px;
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
  .report-content {
    padding: 20px 14px;
    border-radius: 0 0 12px 12px;
  }
  .report-content :deep(p),
  .report-content :deep(li) {
    font-size: 15px;
    line-height: 1.75;
  }
  .report-content :deep(h2) {
    font-size: 19px;
    padding: 11px 12px;
  }
  .report-content :deep(table) {
    min-width: 560px;
  }
  .report-actions {
    flex-direction: column;
  }
}

/* 响应式优化 */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
