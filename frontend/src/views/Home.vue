<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue';
import { useRouter } from 'vue-router';

// ============================================================
// 状态管理
// ============================================================

const router = useRouter();

/** 导航栏滚动状态 */
const isScrolled = ref(false);

/** 移动端菜单打开状态 */
const isMenuOpen = ref(false);

// ============================================================
// 用户评价数据
// ============================================================

interface Testimonial {
  quote: string;
  name: string;
  title: string;
}

const testimonials = ref<Testimonial[]>([
  {
    quote: '这个测评真的帮了我大忙！原本对选专业毫无头绪，通过AI对话，我找到了真正适合自己的方向。',
    name: '张同学',
    title: '2024届考生，清华大学',
  },
  {
    quote: '报告非常详细，不仅推荐了专业，还给出了未来职业规划建议，让我更有信心面对高考志愿。',
    name: '李同学',
    title: '2024届考生，北京大学',
  },
  {
    quote: '作为一名家长，我帮孩子做了测评。AI的分析比我们查了很多资料还要专业，强烈推荐！',
    name: '王女士',
    title: '考生家长，上海交通大学',
  },
]);

/** 当前激活的评价索引（移动端轮播） */
const activeTestimonial = ref(0);

// ============================================================
// 滚动监听 - 导航栏背景透明度变化
// ============================================================

const handleScroll = () => {
  isScrolled.value = window.scrollY > 20;
};

onMounted(() => {
  window.addEventListener('scroll', handleScroll, { passive: true });
  initScrollAnimations();
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
      duration: 0.6,
      delay: index * 0.15,
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
      duration: 0.5,
      delay: index * 0.2,
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

/** 跳转到测评页面 */
const handleStartAssessment = () => {
  router.push('/assessment');
};

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

/** 处理评价卡片切换（移动端轮播） */
const showTestimonial = (index: number) => {
  activeTestimonial.value = index;
};
</script>

<template>
  <div class="min-h-screen overflow-hidden bg-warm-50">
    <!-- ============================================================
         1. 顶部导航栏
         ============================================================ -->
    <nav class="navbar" :class="{ scrolled: isScrolled }">
      <div class="mx-auto flex h-full max-w-7xl items-center justify-between px-6">
        <!-- Logo -->
        <div class="flex items-center gap-2">
          <div class="flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br from-warm-500 to-warm-300 text-white">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <span class="text-lg font-bold tracking-tight text-warm-800">专业推荐</span>
        </div>

        <!-- 桌面端导航链接 -->
        <div class="hidden items-center gap-8 md:flex">
          <a href="#about" class="text-sm font-medium text-warm-400 transition-all duration-300 ease-warm-out hover:scale-105 hover:text-warm-800">
            关于我们
          </a>
          <button class="btn-primary !rounded-full !px-6 !py-2 text-sm" @click="handleStartAssessment">
            开始测评
          </button>
        </div>

        <!-- 移动端汉堡菜单按钮 -->
        <button class="flex h-11 w-11 items-center justify-center rounded-xl md:hidden" @click="toggleMenu" aria-label="菜单">
          <div class="flex h-5 w-5 flex-col justify-between">
            <span class="block h-0.5 w-full rounded-full bg-warm-800 transition-all duration-300 ease-warm-out" :class="{ 'translate-y-2 rotate-45': isMenuOpen }" />
            <span class="block h-0.5 w-full rounded-full bg-warm-800 transition-all duration-300 ease-warm-out" :class="{ 'opacity-0': isMenuOpen }" />
            <span class="block h-0.5 w-full rounded-full bg-warm-800 transition-all duration-300 ease-warm-out" :class="{ '-translate-y-2 -rotate-45': isMenuOpen }" />
          </div>
        </button>
      </div>

      <!-- 移动端下拉菜单 -->
      <transition name="slide-down">
        <div v-if="isMenuOpen" class="border-t border-warm-200 bg-warm-50/95 px-6 py-4 backdrop-blur-xl md:hidden">
          <div class="flex flex-col gap-4">
            <a href="#about" class="rounded-xl px-4 py-3 text-base font-medium text-warm-600 hover:bg-warm-100" @click="closeMenu">
              关于我们
            </a>
            <button class="btn-primary w-full text-center" @click="handleStartAssessment">
              开始测评
            </button>
          </div>
        </div>
      </transition>
    </nav>

    <!-- ============================================================
         2. Hero区域 - 扣子风格暖色渐变背景
         ============================================================ -->
    <section class="relative flex flex-col items-center justify-center overflow-hidden px-6 pt-32 pb-16 md:pt-40 md:pb-24">
      <!-- 背景装饰 - 暖色渐变光晕 -->
      <div class="pointer-events-none absolute inset-0">
        <div class="absolute left-1/4 top-20 h-72 w-72 rounded-full bg-warm-200/30 blur-3xl" />
        <div class="absolute bottom-20 right-1/4 h-96 w-96 rounded-full bg-cosmos-purple/5 blur-3xl" />
        <div class="absolute left-1/2 top-1/3 h-64 w-64 -translate-x-1/2 rounded-full bg-warm-300/20 blur-3xl" />
      </div>

      <div class="relative z-10 mx-auto max-w-4xl text-center">
        <!-- 大标题 -->
        <h1 class="animate-fade-in-up text-4xl font-extrabold leading-tight tracking-tight text-warm-900 md:text-6xl lg:text-7xl">
          找到属于你的<br class="md:hidden" />
          <span class="gradient-text">未来</span>
        </h1>

        <!-- 副标题 -->
        <p class="mx-auto mt-6 max-w-2xl text-lg font-light text-warm-400 md:text-xl md:leading-relaxed">
          <span class="gradient-text font-normal">AI对话式测评</span>，科学推荐最适合你的大学专业
        </p>

        <!-- CTA按钮 -->
        <div class="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center">
          <button class="btn-primary w-full sm:w-auto" @click="handleStartAssessment">
            开始免费测评
          </button>
          <button class="btn-secondary w-full sm:w-auto" @click="handleLearnMore">
            了解更多
          </button>
        </div>
      </div>

      <!-- iPhone模型 / 对话界面预览 -->
      <div class="mt-16 animate-fade-in-up [animation-delay:0.3s] w-full max-w-md opacity-0 md:mt-20">
        <div class="iphone-mockup">
          <!-- 状态栏 -->
          <div class="flex items-center justify-between border-b border-warm-100 px-6 pt-10 pb-3">
            <span class="text-xs font-semibold text-warm-800">9:41</span>
            <div class="flex gap-1">
              <div class="h-2.5 w-2.5 rounded-full bg-warm-300" />
              <div class="h-2.5 w-2.5 rounded-full bg-warm-300" />
              <div class="h-2.5 w-4 rounded-full bg-warm-800" />
            </div>
          </div>
          <!-- 对话区域 -->
          <div class="bg-gradient-to-b from-warm-50 to-white px-4 py-6">
            <!-- AI 消息 -->
            <div class="mb-4 flex gap-2">
              <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-warm-500 to-warm-300">
                <svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
              </div>
              <div class="rounded-2xl rounded-tl-md bg-white px-4 py-3 text-sm text-warm-700 shadow-sm">
                你好！我是你的AI志愿顾问。让我们一起探索最适合你的专业方向吧 
              </div>
            </div>
            <!-- 用户消息 -->
            <div class="mb-4 flex justify-end gap-2">
              <div class="rounded-2xl rounded-tr-md bg-gradient-to-r from-warm-500 to-warm-300 px-4 py-3 text-sm text-white shadow-sm">
                我对计算机和数学都很感兴趣...
              </div>
            </div>
            <!-- AI 消息 -->
            <div class="mb-4 flex gap-2">
              <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-warm-500 to-warm-300">
                <svg class="h-4 w-4 text-white" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                </svg>
              </div>
              <div class="rounded-2xl rounded-tl-md bg-white px-4 py-3 text-sm text-warm-700 shadow-sm">
                根据你的兴趣和优势，我为你推荐了以下3个专业方向...
              </div>
            </div>
            <!-- 推荐卡片 -->
            <div class="flex gap-2 overflow-x-auto pb-2">
              <div class="shrink-0 rounded-xl bg-white p-3 text-left shadow-sm">
                <p class="text-xs font-semibold text-warm-500">计算机科学与技术</p>
                <p class="mt-1 text-xs text-warm-400">匹配度 95%</p>
              </div>
              <div class="shrink-0 rounded-xl bg-white p-3 text-left shadow-sm">
                <p class="text-xs font-semibold text-warm-500">数据科学与大数据</p>
                <p class="mt-1 text-xs text-warm-400">匹配度 92%</p>
              </div>
              <div class="shrink-0 rounded-xl bg-white p-3 text-left shadow-sm">
                <p class="text-xs font-semibold text-warm-500">人工智能</p>
                <p class="mt-1 text-xs text-warm-400">匹配度 89%</p>
              </div>
            </div>
          </div>
          <!-- 底部输入框 -->
          <div class="border-t border-warm-100 bg-white px-4 py-3">
            <div class="flex items-center gap-2 rounded-full bg-warm-50 px-4 py-2.5">
              <span class="flex-1 text-sm text-warm-300">输入消息...</span>
              <div class="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-r from-warm-500 to-warm-300">
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
         3. 特色功能卡片区
         ============================================================ -->
    <section id="features" class="bg-warm-100/50 px-6 py-20 md:py-32">
      <div class="mx-auto max-w-6xl">
        <h2 class="animate-on-scroll text-center text-3xl font-bold tracking-tight text-warm-900 md:text-4xl">
          为什么选择我们
        </h2>
        <p class="mx-auto mt-4 max-w-xl text-center text-base text-warm-400 md:text-lg">
          基于前沿AI技术和海量数据，为你提供最科学的专业推荐
        </p>

        <!-- 卡片网格 -->
        <div class="mt-12 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <!-- 卡片1：智能对话测评 -->
          <div class="animate-on-scroll card-hover rounded-card bg-white p-8 shadow-sm">
            <div class="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-warm-100">
              <svg class="h-7 w-7 text-warm-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z" />
              </svg>
            </div>
            <h3 class="text-xl font-bold text-warm-800">智能对话测评</h3>
            <p class="mt-3 text-sm leading-relaxed text-warm-400">
              通过自然的AI对话方式，深入了解你的兴趣、性格和能力，5分钟完成全面测评，告别枯燥的问卷填表。
            </p>
          </div>

          <!-- 卡片2：大数据分析匹配 -->
          <div class="animate-on-scroll card-hover rounded-card bg-white p-8 shadow-sm">
            <div class="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-warm-100">
              <svg class="h-7 w-7 text-warm-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
              </svg>
            </div>
            <h3 class="text-xl font-bold text-warm-800">大数据分析匹配</h3>
            <p class="mt-3 text-sm leading-relaxed text-warm-400">
              基于数百万份真实考生数据，运用深度学习算法，精准匹配你的特质与专业要求，推荐成功率高达96%。
            </p>
          </div>

          <!-- 卡片3：个性化报告解读 -->
          <div class="animate-on-scroll card-hover rounded-card bg-white p-8 shadow-sm md:col-span-2 lg:col-span-1">
            <div class="mb-6 flex h-14 w-14 items-center justify-center rounded-2xl bg-warm-100">
              <svg class="h-7 w-7 text-warm-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <h3 class="text-xl font-bold text-warm-800">个性化报告解读</h3>
            <p class="mt-3 text-sm leading-relaxed text-warm-400">
              生成详细的专业分析报告，包含匹配度评分、职业发展前景、推荐院校等维度，帮你全面了解每个选择。
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================
         4. 流程展示区
         ============================================================ -->
    <section class="px-6 py-20 md:py-32">
      <div class="mx-auto max-w-5xl">
        <h2 class="animate-on-scroll text-center text-3xl font-bold tracking-tight text-warm-900 md:text-4xl">
          三步找到理想专业
        </h2>

        <!-- 桌面端水平步骤条 -->
        <div class="mt-16 hidden md:block">
          <div class="relative flex items-start justify-between">
            <div class="gradient-line absolute left-[16%] right-[16%] top-7" />

            <div class="step-item relative z-10 flex w-1/3 flex-col items-center text-center">
              <div class="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-warm-500 to-warm-300 text-lg font-bold text-white shadow-lg">
                1
              </div>
              <h3 class="mt-6 text-lg font-bold text-warm-800">智能对话</h3>
              <p class="mt-2 max-w-[200px] text-sm text-warm-400">5分钟完成测评，轻松自然地回答问题</p>
            </div>

            <div class="step-item relative z-10 flex w-1/3 flex-col items-center text-center">
              <div class="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-warm-500 to-warm-300 text-lg font-bold text-white shadow-lg">
                2
              </div>
              <h3 class="mt-6 text-lg font-bold text-warm-800">AI分析</h3>
              <p class="mt-2 max-w-[200px] text-sm text-warm-400">深度学习模型精准匹配你的特质</p>
            </div>

            <div class="step-item relative z-10 flex w-1/3 flex-col items-center text-center">
              <div class="flex h-14 w-14 items-center justify-center rounded-full bg-gradient-to-br from-warm-500 to-warm-300 text-lg font-bold text-white shadow-lg">
                3
              </div>
              <h3 class="mt-6 text-lg font-bold text-warm-800">获得推荐</h3>
              <p class="mt-2 max-w-[200px] text-sm text-warm-400">获取详细专业报告和志愿建议</p>
            </div>
          </div>
        </div>

        <!-- 移动端垂直步骤条 -->
        <div class="mt-12 md:hidden">
          <div class="relative">
            <div class="gradient-line-vertical absolute left-7 top-0 bottom-0" />

            <div class="step-item relative z-10 mb-10 flex items-start gap-4 pl-16">
              <div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-warm-500 to-warm-300 text-lg font-bold text-white shadow-lg">
                1
              </div>
              <div>
                <h3 class="text-lg font-bold text-warm-800">智能对话</h3>
                <p class="mt-1 text-sm text-warm-400">5分钟完成测评，轻松自然地回答问题</p>
              </div>
            </div>

            <div class="step-item relative z-10 mb-10 flex items-start gap-4 pl-16">
              <div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-warm-500 to-warm-300 text-lg font-bold text-white shadow-lg">
                2
              </div>
              <div>
                <h3 class="text-lg font-bold text-warm-800">AI分析</h3>
                <p class="mt-1 text-sm text-warm-400">深度学习模型精准匹配你的特质</p>
              </div>
            </div>

            <div class="step-item relative z-10 flex items-start gap-4 pl-16">
              <div class="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-warm-500 to-warm-300 text-lg font-bold text-white shadow-lg">
                3
              </div>
              <div>
                <h3 class="text-lg font-bold text-warm-800">获得推荐</h3>
                <p class="mt-1 text-sm text-warm-400">获取详细专业报告和志愿建议</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================
         5. 用户评价区
         ============================================================ -->
    <section class="bg-warm-100/50 px-6 py-20 md:py-32">
      <div class="mx-auto max-w-6xl">
        <h2 class="animate-on-scroll text-center text-3xl font-bold tracking-tight text-warm-900 md:text-4xl">
          听听他们怎么说
        </h2>
        <p class="mx-auto mt-4 max-w-xl text-center text-base text-warm-400">
          超过10,000+考生和家长已经通过我们的测评找到了方向
        </p>

        <!-- 桌面端网格布局 -->
        <div class="mt-12 hidden grid-cols-1 gap-6 md:grid md:grid-cols-3">
          <div
            v-for="(item, index) in testimonials"
            :key="index"
            class="animate-on-scroll card-hover rounded-card border-l-4 border-warm-400 bg-white p-8 shadow-sm"
          >
            <p class="text-sm italic leading-relaxed text-warm-600">
              "{{ item.quote }}"
            </p>
            <div class="mt-6 border-t border-warm-100 pt-4">
              <p class="text-sm font-semibold text-warm-800">{{ item.name }}</p>
              <p class="mt-0.5 text-xs text-warm-400">{{ item.title }}</p>
            </div>
          </div>
        </div>

        <!-- 移动端轮播布局 -->
        <div class="mt-8 md:hidden">
          <div class="overflow-hidden rounded-card bg-white p-8 shadow-sm">
            <transition-group name="fade" mode="out-in">
              <div :key="activeTestimonial">
                <p class="text-sm italic leading-relaxed text-warm-600">
                  "{{ testimonials[activeTestimonial].quote }}"
                </p>
                <div class="mt-6 border-t border-warm-100 pt-4">
                  <p class="text-sm font-semibold text-warm-800">{{ testimonials[activeTestimonial].name }}</p>
                  <p class="mt-0.5 text-xs text-warm-400">{{ testimonials[activeTestimonial].title }}</p>
                </div>
              </div>
            </transition-group>
          </div>
          <div class="mt-6 flex justify-center gap-2">
            <button
              v-for="(_, index) in testimonials"
              :key="index"
              class="h-2 w-8 rounded-full transition-all duration-300"
              :class="activeTestimonial === index ? 'bg-gradient-to-r from-warm-500 to-warm-300' : 'bg-warm-200'"
              @click="showTestimonial(index)"
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
        <div class="absolute left-1/2 top-1/2 h-[500px] w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-full bg-gradient-to-br from-warm-200/30 to-warm-300/20 blur-3xl" />
      </div>

      <div class="relative z-10 mx-auto max-w-3xl text-center">
        <h2 class="animate-on-scroll text-3xl font-bold tracking-tight text-warm-900 md:text-5xl">
          准备好探索你的<br class="md:hidden" />
          <span class="gradient-text">未来</span>
          了吗？
        </h2>
        <p class="mx-auto mt-4 max-w-lg text-base text-warm-400 md:text-lg">
          只需5分钟，AI将为你量身定制专业推荐报告
        </p>

        <button class="btn-primary mx-auto mt-8 text-lg" @click="handleStartAssessment">
          立即开始测评
        </button>

        <div class="mt-12 flex flex-wrap items-center justify-center gap-8">
          <div class="flex items-center gap-2 text-sm text-warm-400">
            <svg class="h-5 w-5 text-warm-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z" />
            </svg>
            <span>数据安全</span>
          </div>
          <div class="flex items-center gap-2 text-sm text-warm-400">
            <svg class="h-5 w-5 text-warm-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M4.26 10.147a60.436 60.436 0 00-.491 6.347A48.627 48.627 0 0112 20.904a48.627 48.627 0 018.232-4.41 60.46 60.46 0 00-.491-6.347m-15.482 0a50.57 50.57 0 00-2.658-.813A59.905 59.905 0 0112 3.493a59.902 59.902 0 0110.399 5.84c-.896.248-1.783.52-2.658.814m-15.482 0A50.697 50.697 0 0112 13.489a50.702 50.702 0 017.74-3.342M6.75 15a.75.75 0 100-1.5.75.75 0 000 1.5zm0 0v-3.675A55.378 55.378 0 0112 8.443m-7.007 11.55A5.981 5.981 0 006.75 15.75v-1.5" />
            </svg>
            <span>权威认证</span>
          </div>
          <div class="flex items-center gap-2 text-sm text-warm-400">
            <svg class="h-5 w-5 text-warm-500" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 002.625.372 9.337 9.337 0 004.121-.952 4.125 4.125 0 00-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 018.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0111.964-3.07M12 6.375a3.375 3.375 0 11-6.75 0 3.375 3.375 0 016.75 0zm8.25 2.25a2.625 2.625 0 11-5.25 0 2.625 2.625 0 015.25 0z" />
            </svg>
            <span>已有 10,000+ 考生完成测评</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================
         7. 页脚
         ============================================================ -->
    <footer class="border-t border-warm-200 bg-warm-100/50 px-6 py-10">
      <div class="mx-auto max-w-6xl">
        <div class="flex flex-col items-center justify-between gap-4 md:flex-row">
          <p class="text-sm text-warm-400">
            &copy; 2024 专业推荐. All rights reserved.
          </p>
          <div class="flex items-center gap-6">
            <a href="#privacy" class="text-sm text-warm-400 transition-colors duration-300 hover:text-warm-600">
              隐私政策
            </a>
            <a href="#contact" class="text-sm text-warm-400 transition-colors duration-300 hover:text-warm-600">
              联系我们
            </a>
            <a href="#terms" class="text-sm text-warm-400 transition-colors duration-300 hover:text-warm-600">
              使用条款
            </a>
          </div>
        </div>
      </div>
    </footer>
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
  width: 8px;
}

::-webkit-scrollbar-track {
  background: transparent;
}

::-webkit-scrollbar-thumb {
  background: rgba(140, 115, 71, 0.15);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: rgba(140, 115, 71, 0.25);
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
