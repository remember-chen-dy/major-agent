import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { api } from '../api';

export const useAuthStore = defineStore('auth', () => {
  const userId = ref<string>('');
  const deviceId = ref<string>('');
  const isAuthenticated = ref(false);

  const isLoggedIn = computed(() => isAuthenticated.value && !!userId.value);

  /** 简单的 UUID 格式校验 */
  const isValidUUID = (val: string): boolean =>
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(val);

  /** 从 localStorage 恢复登录态（不调 API） */
  const loadFromStorage = () => {
    const storedDeviceId = localStorage.getItem('deviceId');
    const storedUserId = localStorage.getItem('userId');

    if (storedDeviceId) {
      deviceId.value = storedDeviceId;
    } else {
      deviceId.value = `device_${Date.now()}_${Math.random().toString(36).substring(2, 15)}`;
      localStorage.setItem('deviceId', deviceId.value);
    }
    
    if (storedUserId && isValidUUID(storedUserId)) {
      userId.value = storedUserId;
      isAuthenticated.value = true;
    } else {
      // 清除无效的旧 userId（如 "320113"）
      if (storedUserId) {
        console.warn('[auth] 清除无效的 userId:', storedUserId);
        localStorage.removeItem('userId');
      }
      userId.value = '';
      isAuthenticated.value = false;
    }
  };

  /**
   * 登录：如果 localStorage 中已有 userId 则跳过 API 调用，
   * 否则调用后端 /api/auth/login 获取 userId。
   */
  const login = async () => {
    // 每次都从 localStorage 恢复状态（清理无效数据）
    loadFromStorage();

    // 如果已有有效 userId，直接跳过登录 API
    if (userId.value && isAuthenticated.value) {
      console.log('[auth] 已有登录态，跳过登录 API, userId =', userId.value);
      return { user_id: userId.value };
    }

    try {
      // api.login 返回的已经是解析后的 JSON，即 { user_id, device_id }
      const data = await api.login(deviceId.value);

      // 校验 API 返回值
      if (!data.user_id || !isValidUUID(data.user_id)) {
        console.error('[auth] API 返回无效的 user_id:', data.user_id);
        throw new Error('登录失败：服务器返回了无效的用户ID');
      }

      userId.value = data.user_id;
      isAuthenticated.value = true;

      localStorage.setItem('userId', data.user_id);
      localStorage.setItem('deviceId', deviceId.value);

      console.log('[auth] 登录成功, userId =', data.user_id);
      return data;
    } catch (error) {
      console.error('[auth] 登录失败:', error);
      throw error;
    }
  };

  const logout = () => {
    userId.value = '';
    isAuthenticated.value = false;
    localStorage.removeItem('userId');
  };

  return {
    userId,
    deviceId,
    isAuthenticated,
    isLoggedIn,
    loadFromStorage,
    login,
    logout,
  };
});
