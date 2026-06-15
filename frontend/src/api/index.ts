const API_BASE = '';

// 获取设备 ID
const getDeviceId = (): string => {
  return localStorage.getItem('deviceId') || '';
};

// 通用请求函数
const request = async (
  url: string,
  options: RequestInit = {}
): Promise<any> => {
  const deviceId = getDeviceId();
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(deviceId && { 'X-Device-ID': deviceId }),
    ...options.headers,
  };

  const response = await fetch(`${API_BASE}${url}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => null);
    throw new Error(errorData?.detail || `HTTP ${response.status}`);
  }

  return response.json();
};

export const api = {
  // 认证相关
  login: (deviceId: string) =>
    request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ device_id: deviceId }),
    }),

  getCurrentUser: () => request('/api/users/me'),

  getUserSessions: (userId: string) =>
    request(`/api/users/${userId}/sessions`),

  // 会话相关
  createSession: (title?: string) =>
    request('/api/sessions', {
      method: 'POST',
      body: JSON.stringify({ title }),
    }),

  getSession: (sessionId: string) =>
    request(`/api/sessions/${sessionId}`),

  getSessionMessages: (sessionId: string) =>
    request(`/api/sessions/${sessionId}/messages`),

  deleteSession: (sessionId: string) =>
    request(`/api/sessions/${sessionId}`, {
      method: 'DELETE',
    }),

  saveCheckpoint: (sessionId: string, checkpointData: any) =>
    request(`/api/sessions/${sessionId}/checkpoint`, {
      method: 'PUT',
      body: JSON.stringify(checkpointData),
    }),

  submitSession: (sessionId: string, finalAnswers?: any) =>
    request(`/api/sessions/${sessionId}/submit`, {
      method: 'POST',
      body: JSON.stringify({ final_answers: finalAnswers }),
    }),

  getReportStatus: (sessionId: string) =>
    request(`/api/sessions/${sessionId}/report-status`),

  sendAssessmentAnswer: (sessionId: string, answer: any) =>
    request(`/api/assessment/chat/${sessionId}`, {
      method: 'POST',
      body: JSON.stringify({ answer }),
    }),

  getAssessmentResults: (sessionId: string) =>
    request(`/api/assessment/session/${sessionId}/results`),
};

export default api;
