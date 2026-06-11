<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue';

// ============================================================
// 测评流程状态
// ============================================================

/** 当前步骤索引 (0-4) */
const currentStep = ref(0);

/** 测评是否完成 */
const isComplete = ref(false);

/** 用户输入 */
const userInput = ref('');

/** 输入框焦点 */
const inputFocused = ref(false);

/** 用户选择的答案 */
const userAnswers = ref<Record<number, string>>({});

/** 消息容器引用 */
const messagesRef = ref<HTMLElement | null>(null);

/** 总步骤数 */
const TOTAL_STEPS = 5;

// ============================================================
// 测评步骤配置
// ============================================================

interface StepConfig {
  question: string;
  options: string[];
  icon: string;
}

const steps: StepConfig[] = [
  {
    question: '你好！我是你的AI志愿顾问。让我先了解一下你的基本情况~',
    options: ['我是理科生', '我是文科生', '我是综合型学生'],
    icon: '',
  },
  {
    question: '你平时最喜欢做什么类型的活动呢？',
    options: ['探索未知领域', '动手实践创造', '与人交流协作', '独立思考分析'],
    icon: '💭',
  },
  {
    question: '你对以下哪个领域最感兴趣？',
    options: ['科技与创新', '人文与艺术', '商业与经济', '自然与生命科学'],
    icon: '',
  },
  {
    question: '你理想中的未来工作状态是什么样的？',
    options: ['稳定且有规律', '充满挑战与变化', '自由灵活', '能影响他人'],
    icon: '',
  },
  {
    question: '最后，你更看重大学期间的什么体验？',
    options: ['学术研究能力', '实践操作能力', '人际交往能力', '创新思维能力'],
    icon: '',
  },
];

// ============================================================
// 推荐结果数据
// ============================================================

interface MajorResult {
  name: string;
  match: number;
  icon: string;
  description: string;
  universities: string[];
}

const majorResults: MajorResult[] = [
  {
    name: '计算机科学与技术',
    match: 95,
    icon: '💻',
    description: '结合你的理科基础和创新能力，这个专业将为你提供广阔的发展空间',
    universities: ['清华大学', '北京大学', '浙江大学'],
  },
  {
    name: '人工智能',
    match: 88,
    icon: '',
    description: 'AI是未来趋势，你的分析能力和探索精神非常适合这个方向',
    universities: ['上海交通大学', '复旦大学', '南京大学'],
  },
  {
    name: '数据科学与大数据技术',
    match: 82,
    icon: '',
    description: '数据时代的核心专业，你将掌握从数据中提取价值的能力',
    universities: ['武汉大学', '华中科技大学', '中山大学'],
  },
];

// ============================================================
// 计算属性
// ============================================================

/** 当前步骤的进度百分比 */
const progressPercent = computed(() => {
  if (isComplete.value) return 100;
  return Math.round(((currentStep.value + 1) / TOTAL_STEPS) * 100);
});

/** 当前步骤配置 */
const currentStepConfig = computed(() => steps[currentStep.value]);

// ============================================================
// 核心方法
// ============================================================

/** 选择选项 */
const selectOption = (option: string) => {
  userAnswers.value[currentStep.value] = option;
  
  // 自动进入下一步
  if (currentStep.value < TOTAL_STEPS - 1) {
    currentStep.value++;
  } else {
    // 最后一步，显示结果
    showResults();
  }
  
  // 滚动到底部
  nextTick(() => {
    scrollToBottom();
  });
};

/** 显示结果 */
const showResults = () => {
  isComplete.value = true;
  
  // 滚动到底部
  nextTick(() => {
    scrollToBottom();
  });
};

/** 滚动到底部 */
const scrollToBottom = () => {
  if (messagesRef.value) {
    messagesRef.value.scrollTo({
      top: messagesRef.value.scrollHeight,
      behavior: 'smooth',
    });
  }
};

/** 返回上一页 */
const goBack = () => {
  if (window.history.length > 1) {
    window.history.back();
  } else {
    window.location.href = '/';
  }
};

/** 重置测评 */
const resetAssessment = () => {
  currentStep.value = 0;
  isComplete.value = false;
  userAnswers.value = {};
  userInput.value = '';
  
  // 滚动到底部
  nextTick(() => {
    scrollToBottom();
  });
};

// ============================================================
// 生命周期
// ============================================================

onMounted(() => {
  // 自动滚动到底部
  nextTick(() => {
    scrollToBottom();
  });
});
</script>

<template>
  <div class="min-h-screen bg-warm-gradient flex flex-col">
    <!-- ============================================================
         顶部导航栏
         ============================================================ -->
    <header class="sticky top-0 z-50 bg-warm-50/80 backdrop-blur-xl border-b border-warm-200">
      <div class="mx-auto max-w-3xl px-6 py-4 flex items-center justify-between">
        <button 
          @click="goBack"
          class="flex items-center gap-2 text-warm-600 hover:text-warm-800 transition-colors"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
          </svg>
          <span class="text-sm font-medium">返回</span>
        </button>
        
        <h1 class="text-lg font-bold text-warm-800">
          专业推荐测评
        </h1>
        
        <div class="w-16"></div>
      </div>
      
      <!-- 进度条 -->
      <div class="h-1 bg-warm-100">
        <div 
          class="h-full bg-gradient-to-r from-accent-blue to-accent-purple transition-all duration-500 ease-warm-out"
          :style="{ width: `${progressPercent}%` }"
        />
      </div>
    </header>

    <!-- ============================================================
         主内容区
         ============================================================ -->
    <main ref="messagesRef" class="flex-1 overflow-y-auto">
      <div class="mx-auto max-w-3xl px-6 py-8 space-y-8">
        <!-- ============================================================
             测评步骤卡片
             ============================================================ -->
        <div 
          v-for="(step, index) in steps.slice(0, currentStep + 1)" 
          :key="index"
          class="space-y-4 animate-fade-in-up"
          :class="{ 'opacity-50': index < currentStep }"
        >
          <!-- AI问题卡片 -->
          <div class="flex items-start gap-4">
            <div class="flex-shrink-0 w-12 h-12 rounded-2xl bg-gradient-to-br from-accent-blue/10 to-accent-purple/10 flex items-center justify-center text-xl">
              {{ step.icon }}
            </div>
            <div class="flex-1">
              <div class="bg-white/80 backdrop-blur-sm rounded-2xl rounded-tl-sm p-5 shadow-soft">
                <p class="text-warm-800 leading-relaxed">{{ step.question }}</p>
              </div>
              
              <!-- 用户已选择的答案 -->
              <div v-if="userAnswers[index]" class="mt-3 flex justify-end">
                <div class="bg-gradient-to-r from-accent-blue to-accent-purple text-white px-5 py-3 rounded-2xl rounded-tr-sm text-sm font-medium shadow-md">
                  {{ userAnswers[index] }}
                </div>
              </div>
            </div>
          </div>

          <!-- 选项按钮 (只在当前步骤显示) -->
          <div v-if="index === currentStep && !isComplete" class="ml-16 grid grid-cols-1 sm:grid-cols-2 gap-3">
            <button
              v-for="(option, optIndex) in step.options"
              :key="optIndex"
              @click="selectOption(option)"
              class="option-chip"
            >
              {{ option }}
            </button>
          </div>
        </div>

        <!-- ============================================================
             测评结果
             ============================================================ -->
        <div v-if="isComplete" class="space-y-6 animate-fade-in-up">
          <!-- 结果标题 -->
          <div class="text-center space-y-3">
            <div class="text-4xl mb-2">🎉</div>
            <h2 class="text-2xl font-bold text-warm-900">测评完成！</h2>
            <p class="text-warm-500">基于你的回答，为你推荐以下专业方向</p>
          </div>

          <!-- 专业推荐卡片 -->
          <div class="space-y-4">
            <div 
              v-for="(major, index) in majorResults" 
              :key="index"
              class="bg-white/80 backdrop-blur-sm rounded-2xl p-6 shadow-soft hover:shadow-card-hover transition-all duration-300 ease-warm-out cursor-pointer"
            >
              <div class="flex items-start gap-4">
                <!-- 专业图标 -->
                <div class="flex-shrink-0 w-14 h-14 rounded-2xl bg-gradient-to-br from-accent-blue/10 to-accent-purple/10 flex items-center justify-center text-2xl">
                  {{ major.icon }}
                </div>
                
                <!-- 专业信息 -->
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between mb-2">
                    <h3 class="text-lg font-bold text-warm-900">{{ major.name }}</h3>
                    <span class="text-sm font-bold text-accent-purple">{{ major.match }}% 匹配</span>
                  </div>
                  <p class="text-sm text-warm-500 mb-4">{{ major.description }}</p>
                  
                  <!-- 推荐院校 -->
                  <div class="flex flex-wrap gap-2">
                    <span 
                      v-for="(uni, uniIndex) in major.universities" 
                      :key="uniIndex"
                      class="px-3 py-1 text-xs bg-warm-50 text-warm-600 rounded-full border border-warm-100"
                    >
                      {{ uni }}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 操作按钮 -->
          <div class="flex flex-col sm:flex-row gap-3 pt-4">
            <button 
              @click="resetAssessment"
              class="flex-1 bg-white border-2 border-warm-200 text-warm-600 font-medium px-6 py-4 rounded-full hover:border-warm-300 hover:bg-warm-50 transition-all duration-300"
            >
              重新测评
            </button>
            <button class="flex-1 bg-gradient-to-r from-accent-blue to-accent-purple text-white font-medium px-6 py-4 rounded-full hover:shadow-lg transition-all duration-300">
              生成详细报告
            </button>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.animate-fade-in-up {
  animation: fadeInUp 0.5s ease-warm-out forwards;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 隐藏滚动条但保留滚动功能 */
main::-webkit-scrollbar {
  display: none;
}
main {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
