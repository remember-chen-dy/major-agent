import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { api } from '../api';

export const useSessionStore = defineStore('session', () => {
  // 状态
  const currentSessionId = ref<string>('');
  const sessions = ref<any[]>([]);
  const checkpointerState = ref<any>(null);
  const reportStatus = ref<string>('');
  const reportProgress = ref<number>(0);
  const reportUrl = ref<string>('');

  // 计算属性
  const currentSession = computed(() =>
    sessions.value.find(s => s.id === currentSessionId.value)
  );

  const isReportReady = computed(() => reportStatus.value === 'completed');
  const isReportFailed = computed(() => reportStatus.value === 'failed');

  // 从 localStorage 加载
  const loadFromStorage = () => {
    try {
      const stored = localStorage.getItem('sessionState');
      if (stored) {
        const data = JSON.parse(stored);
        currentSessionId.value = data.currentSessionId || '';
        sessions.value = data.sessions || [];
        checkpointerState.value = data.checkpointerState || null;
      }
    } catch (e) {
      console.error('加载会话状态失败:', e);
    }
  };

  // 保存到 localStorage
  const saveToStorage = () => {
    try {
      const data = {
        currentSessionId: currentSessionId.value,
        sessions: sessions.value,
        checkpointerState: checkpointerState.value,
      };
      localStorage.setItem('sessionState', JSON.stringify(data));
    } catch (e) {
      console.error('保存会话状态失败:', e);
    }
  };

  // 创建会话
  const createSession = async (title?: string) => {
    try {
      const data = await api.createSession(title);
      const newSession = {
        id: data.session_id,
        title: title || '志愿测评',
        created_at: new Date().toISOString(),
        messages: data.messages || [],
        isComplete: false,
        reportStatus: data.report_status || 'pending',
        reportProgress: data.report_progress || 0,
        reportUrl: data.report_url || '',
      };
      sessions.value = [newSession];
      currentSessionId.value = data.session_id;
      saveToStorage();
      console.log('[session] 创建会话成功, id =', data.session_id, '消息数:', newSession.messages.length);
      return data;
    } catch (error) {
      console.error('创建会话失败:', error);
      throw error;
    }
  };

  // 从服务端加载会话消息
  const loadSessionMessages = async (sessionId: string) => {
    try {
      const data = await api.getSessionMessages(sessionId);
      const session = sessions.value.find(s => s.id === sessionId);
      if (session) {
        session.messages = data.messages || [];
        session.isComplete = data.is_complete || false;
        session.reportStatus = data.report_status || session.reportStatus;
        session.reportProgress = data.report_progress ?? session.reportProgress;
        session.reportUrl = data.report_url || session.reportUrl;
        saveToStorage();
        console.log('[session] 加载会话消息成功, id =', sessionId, '消息数:', session.messages.length);
      }
      return data;
    } catch (error) {
      console.error('加载会话消息失败:', error);
      throw error;
    }
  };

  // 加载会话
  const loadSession = async (sessionId: string) => {
    try {
      const data = await api.getSession(sessionId);
      const session = {
        id: data.session_id,
        title: data.title,
        created_at: data.created_at,
        messages: data.messages || [],
        isComplete: data.is_complete || false,
        reportStatus: data.report_status || 'pending',
        reportProgress: data.report_progress || 0,
        reportUrl: data.report_url || '',
      };

      // 更新或添加会话
      const index = sessions.value.findIndex(s => s.id === sessionId);
      if (index >= 0) {
        sessions.value[index] = session;
      } else {
        sessions.value.unshift(session);
      }

      currentSessionId.value = sessionId;
      checkpointerState.value = data.checkpointer_state || null;
      saveToStorage();
      console.log('[session] 加载会话成功, id =', sessionId, '消息数:', session.messages.length);
      return data;
    } catch (error) {
      console.error('加载会话失败:', error);
      throw error;
    }
  };

  // 保存检查点
  const saveCheckpoint = async (sessionId: string, checkpointData: any) => {
    try {
      await api.saveCheckpoint(sessionId, checkpointData);
      checkpointerState.value = checkpointData;
      saveToStorage();
    } catch (error) {
      console.error('保存检查点失败:', error);
      throw error;
    }
  };

  // 提交会话
  const submitSession = async (sessionId: string, finalAnswers?: any) => {
    try {
      const data = await api.submitSession(sessionId, finalAnswers);
      const session = sessions.value.find(s => s.id === sessionId);
      if (session) {
        session.isComplete = true;
      }
      saveToStorage();
      return data;
    } catch (error) {
      console.error('提交会话失败:', error);
      throw error;
    }
  };

  // 轮询报告状态
  const pollReportStatus = async (sessionId: string) => {
    try {
      const data = await api.getReportStatus(sessionId);
      reportStatus.value = data.status;
      reportProgress.value = data.progress || 0;
      reportUrl.value = data.report_url || '';

      if (data.status === 'completed' && data.report_url) {
        return data;
      }
      return null;
    } catch (error) {
      console.error('获取报告状态失败:', error);
      throw error;
    }
  };

  // 清除当前会话
  const clearCurrentSession = () => {
    currentSessionId.value = '';
    sessions.value = [];
    checkpointerState.value = null;
    reportStatus.value = '';
    reportProgress.value = 0;
    reportUrl.value = '';
    saveToStorage();
  };

  const deleteSession = async (sessionId: string) => {
    await api.deleteSession(sessionId);
    sessions.value = sessions.value.filter(s => s.id !== sessionId);
    if (currentSessionId.value === sessionId) {
      clearCurrentSession();
    } else {
      saveToStorage();
    }
  };

  const restartAssessment = async (sessionId?: string) => {
    const targetId = sessionId || currentSessionId.value;
    if (targetId) {
      try {
        await api.deleteSession(targetId);
      } catch (error) {
        console.warn('删除旧会话失败，继续创建新会话:', error);
      }
    }
    clearCurrentSession();
    return createSession('志愿测评');
  };

  return {
    currentSessionId,
    sessions,
    checkpointerState,
    reportStatus,
    reportProgress,
    reportUrl,
    currentSession,
    isReportReady,
    isReportFailed,
    loadFromStorage,
    saveToStorage,
    createSession,
    loadSession,
    loadSessionMessages,
    saveCheckpoint,
    submitSession,
    pollReportStatus,
    clearCurrentSession,
    deleteSession,
    restartAssessment,
  };
});
