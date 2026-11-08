import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import RightPanel from './components/RightPanel';
import {
  fetchHealth,
  fetchChannels,
  fetchBots,
  fetchMessages,
  sendRequest,
  decideApproval,
  fetchTaskDeliverable,
  subscribeToRequestEvents,
  fetchApiKeyStatus,
  saveApiKey
} from './api/client';

export default function App() {
  // Phase 3 Rule 1: Remove all mock initial states
  const [channels, setChannels] = useState([]);
  const [bots, setBots] = useState([]);
  const [activeChannelId, setActiveChannelId] = useState('eng1');
  const [messagesMap, setMessagesMap] = useState({});
  const [health, setHealth] = useState({ status: 'ok', gemini: 'missing_key', model: 'gemini-2.5-flash' });
  const [backendOffline, setBackendOffline] = useState(false);

  const [activeDeliverable, setActiveDeliverable] = useState(null);
  const [activeWorkspaceDir, setActiveWorkspaceDir] = useState(null);
  const [statusMessage, setStatusMessage] = useState('');

  // Phase 4-3: API Key Setup Modal
  const [keyModalOpen, setKeyModalOpen] = useState(false);
  const [inputKey, setInputKey] = useState('');
  const [keySaveMsg, setKeySaveMsg] = useState('');
  const [isSavingKey, setIsSavingKey] = useState(false);
  const [maskedKey, setMaskedKey] = useState('');

  // Track active SSE cleanup
  const sseCleanupRef = useRef(null);

  // 1. Initial Load: Health, Channels, Bots, API Key status from backend API only
  useEffect(() => {
    let isMounted = true;

    async function loadInitialData() {
      try {
        const h = await fetchHealth();
        if (isMounted) {
          setHealth(h);
          setBackendOffline(h.status === 'error');
        }

        // Check if API key is configured
        try {
          const keyStatus = await fetchApiKeyStatus();
          if (isMounted) {
            setMaskedKey(keyStatus.masked_key || '');
            if (!keyStatus.configured) {
              setKeyModalOpen(true);
            }
          }
        } catch (e) {
          console.warn('Failed to check API key status:', e);
        }

        const chs = await fetchChannels();
        if (isMounted && chs && chs.length > 0) {
          const formattedChannels = chs.map((apiCh) => ({
            ...apiCh,
            desc: apiCh.desc || (apiCh.type === 'all' ? '전체 교무 협의 및 교과 융합 협업 채널' : `${apiCh.name} 수업·평가 설계 및 학생 관찰 기록 채널`),
            badge: apiCh.type === 'all' ? '전원' : null
          }));
          setChannels(formattedChannels);
          if (!activeChannelId && formattedChannels[0]) {
            setActiveChannelId(formattedChannels[0].id);
          }
        }

        const bts = await fetchBots();
        if (isMounted && bts && bts.length > 0) {
          const avatarMap = {
            coordinator: '🎯',
            curriculum: '📐',
            lesson: '💡',
            assessment: '📝',
            record: '📋'
          };
          const formattedBots = bts.map((apiBot) => ({
            ...apiBot,
            avatar: avatarMap[apiBot.id] || '🤖',
            provider: 'Gemini'
          }));
          setBots(formattedBots);
        }
        setBackendOffline(false);
      } catch (err) {
        console.warn('Backend offline or init error:', err);
        if (isMounted) {
          setBackendOffline(true);
        }
      }
    }

    loadInitialData();

    // Health poll every 10 seconds
    const interval = setInterval(async () => {
      const h = await fetchHealth();
      if (isMounted) {
        setHealth(h);
        setBackendOffline(h.status === 'error');
      }
    }, 10000);

    return () => {
      isMounted = false;
      clearInterval(interval);
      if (sseCleanupRef.current) sseCleanupRef.current();
    };
  }, []);

  // 2. Load Channel Messages when switching channels
  const loadChannelMessages = async (channelId) => {
    if (!channelId) return;
    try {
      const dbMsgs = await fetchMessages(channelId);
      if (dbMsgs && dbMsgs.length > 0) {
        const formatted = dbMsgs.map((m) => ({
          ...m,
          sender: m.sender === 'teacher' ? '교사' : m.sender === 'coordinator' ? '코디봇' : m.sender,
          time: m.created_at ? m.created_at.slice(11, 16) : ''
        }));
        setMessagesMap((prev) => ({
          ...prev,
          [channelId]: formatted
        }));

        // Extract latest workspace_dir from recent messages
        let foundWorkspaceDir = null;
        let latestDoneTask = null;

        for (let i = formatted.length - 1; i >= 0; i--) {
          const m = formatted[i];
          if (!foundWorkspaceDir && m.metadata?.workspace_dir) {
            foundWorkspaceDir = m.metadata.workspace_dir;
          }
          if (!latestDoneTask && m.metadata?.tasks) {
            const done = m.metadata.tasks.find((t) => t.status === 'done');
            if (done) latestDoneTask = done;
          }
          if (foundWorkspaceDir && latestDoneTask) break;
        }

        if (foundWorkspaceDir) {
          setActiveWorkspaceDir(foundWorkspaceDir);
        }

        // Auto-load latest done deliverable from actual API
        if (latestDoneTask) {
          handleSelectDeliverable(latestDoneTask);
        }
      } else {
        setMessagesMap((prev) => ({
          ...prev,
          [channelId]: []
        }));
        setActiveWorkspaceDir(null);
      }
    } catch (e) {
      console.warn(`Failed to fetch messages for ${channelId}:`, e);
      setMessagesMap((prev) => ({
        ...prev,
        [channelId]: []
      }));
    }
  };

  useEffect(() => {
    if (activeChannelId) {
      loadChannelMessages(activeChannelId);
    }
  }, [activeChannelId]);

  const activeChannel = channels.find((c) => c.id === activeChannelId) || channels[0] || {
    id: 'eng1',
    name: '영어I',
    type: 'course',
    course_code: 'ENG1',
    desc: '영어I 수업·평가 설계 및 학생 관찰 기록 채널'
  };

  const activeMessages = messagesMap[activeChannelId] || [];

  const handleSelectChannel = (channelId) => {
    setActiveChannelId(channelId);
    setStatusMessage('');
  };

  // Helper to append message to active channel
  const appendMessage = (msg) => {
    setMessagesMap((prev) => ({
      ...prev,
      [activeChannelId]: [...(prev[activeChannelId] || []), msg]
    }));
  };

  // Subscribe to SSE stream for a request
  const listenToRequestStream = (requestId) => {
    if (sseCleanupRef.current) {
      sseCleanupRef.current();
      sseCleanupRef.current = null;
    }

    const cleanup = subscribeToRequestEvents(
      requestId,
      (event) => {
        const { type, data } = event;
        if (type === 'status') {
          setStatusMessage(data.message || '');
        } else if (type === 'dispatch_created') {
          if (data.workspace_dir) {
            setActiveWorkspaceDir(data.workspace_dir);
          }
          appendMessage({
            id: data.message_id || `dispatch-${Date.now()}`,
            type: 'dispatch',
            sender: '코디봇',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            title: '과업 디스패치',
            content: '요청 분석 및 과업 분해 계획',
            metadata: {
              tasks: data.tasks,
              workspace_dir: data.workspace_dir
            }
          });
        } else if (type === 'task_update') {
          // Update status in dispatch message
          setMessagesMap((prev) => {
            const msgs = prev[activeChannelId] || [];
            return {
              ...prev,
              [activeChannelId]: msgs.map((m) => {
                if (m.type === 'dispatch' && m.metadata?.tasks) {
                  const updatedTasks = m.metadata.tasks.map((t) =>
                    t.id === data.task_id ? { ...t, status: data.status, output_path: data.output_path, check_info: data.check_info } : t
                  );
                  return { ...m, metadata: { ...m.metadata, tasks: updatedTasks } };
                }
                return m;
              })
            };
          });

          // If a task finished, load its deliverable
          if (data.status === 'done' && data.task_id) {
            handleSelectDeliverable({ id: data.task_id });
          }
        } else if (type === 'completed') {
          setStatusMessage('');
          // Refresh channel messages from DB to get canonical cards
          loadChannelMessages(activeChannelId);
        } else if (type === 'error') {
          setStatusMessage('');
          appendMessage({
            id: `err-${Date.now()}`,
            type: 'text',
            sender: '코디봇',
            time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            content: `⚠️ 작업 중 오류가 발생했습니다: ${data.message}`
          });
        }
      },
      (err) => {
        console.error('SSE connection error:', err);
        setStatusMessage('');
      }
    );

    sseCleanupRef.current = cleanup;
  };

  // 3. Send Message
  const handleSendMessage = async (text) => {
    const now = new Date();
    const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // 1. Optimistic teacher message
    const tempTeacherMsg = {
      id: `teacher-${Date.now()}`,
      type: 'user',
      sender: '교사',
      time: timeStr,
      content: text
    };
    appendMessage(tempTeacherMsg);

    // 2. Call backend
    setStatusMessage('요청을 접수하여 크루에게 전달하고 있습니다...');
    try {
      const res = await sendRequest(activeChannelId, text);
      const requestId = res.request_id;
      listenToRequestStream(requestId);
    } catch (err) {
      setStatusMessage('');
      appendMessage({
        id: `err-${Date.now()}`,
        type: 'text',
        sender: '코디봇',
        time: timeStr,
        content: `⚠️ 요청 전송 실패: ${err.message}`
      });
    }
  };

  // 4. Handle Approval Decision
  const handleApprovalDecision = async (approvalId, decision, reason) => {
    try {
      const result = await decideApproval(approvalId, decision, reason);

      // Refresh messages
      await loadChannelMessages(activeChannelId);

      // If rejected, a new redispatch request was created
      if (decision === 'rejected' && result.new_request_id) {
        setStatusMessage('반려 피드백을 반영하여 재디스패치를 진행하고 있습니다...');
        listenToRequestStream(result.new_request_id);
      }
    } catch (err) {
      console.error('Approval decision error:', err);
      throw err;
    }
  };

  // 5. Select deliverable to view in RightPanel via API
  const handleSelectDeliverable = async (taskItem) => {
    const taskId = taskItem.id || taskItem.task_id;
    if (!taskId) return;

    try {
      const del = await fetchTaskDeliverable(taskId);
      setActiveDeliverable({
        id: del.id,
        title: del.title,
        bot: taskItem.bot || taskItem.bot_id || '평가봇',
        status: del.status,
        output_path: del.output_path,
        content: del.content || '산출물 파일 내용이 비어 있습니다.'
      });
    } catch (e) {
      console.warn('Failed to fetch deliverable content from API:', e);
      setActiveDeliverable(null);
    }
  };

  // API Key Save Handler
  const handleSaveApiKey = async () => {
    if (!inputKey.trim()) {
      setKeySaveMsg('API 키를 입력해 주세요.');
      return;
    }
    setIsSavingKey(true);
    setKeySaveMsg('');
    try {
      const res = await saveApiKey(inputKey.trim());
      setMaskedKey(res.masked_key || '');
      setKeySaveMsg('API 키가 안전하게 저장되었습니다.');
      // Refresh health status
      const h = await fetchHealth();
      setHealth(h);
      setTimeout(() => {
        setKeyModalOpen(false);
        setKeySaveMsg('');
        setInputKey('');
      }, 1500);
    } catch (err) {
      setKeySaveMsg(`저장 실패: ${err.message}`);
    } finally {
      setIsSavingKey(false);
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#f8f9fa] text-slate-800 font-sans flex-col">
      {/* Backend Offline Banner */}
      {backendOffline && (
        <div className="w-full bg-rose-600 text-white text-xs font-semibold py-1.5 px-4 flex items-center justify-between shrink-0 shadow-sm z-50">
          <div className="flex items-center gap-2">
            <span>⚠️</span>
            <span>백엔드 연결 안 됨: FastAPI 로컬 서버(127.0.0.1:8765)에 연결할 수 없습니다. 서버 실행 상태를 확인해 주세요.</span>
          </div>
          <span className="text-[11px] opacity-80">오프라인 모드</span>
        </div>
      )}

      <div className="flex flex-1 min-h-0 w-full overflow-hidden">
        {/* 1. Left Sidebar: 240px */}
        <Sidebar
          channels={channels}
          bots={bots}
          activeChannelId={activeChannelId}
          onSelectChannel={handleSelectChannel}
          health={health}
          onOpenKeyModal={() => setKeyModalOpen(true)}
        />

        {/* 2. Center Chat Area: Variable Width */}
        <ChatArea
          channel={activeChannel}
          messages={activeMessages}
          onSendMessage={handleSendMessage}
          onApprovalDecision={handleApprovalDecision}
          onSelectDeliverable={handleSelectDeliverable}
          onRetryRequest={handleSendMessage}
          statusMessage={statusMessage}
        />

        {/* 3. Right Side Panel: 320px */}
        <RightPanel
          channel={activeChannel}
          channels={channels}
          deliverable={activeDeliverable}
          workspaceDir={activeWorkspaceDir}
        />
      </div>

      {/* Gemini API Key Modal (Phase 4-3) */}
      {keyModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-md w-full p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-150">
              <div className="flex items-center gap-2">
                <span className="text-xl">🔑</span>
                <div>
                  <h3 className="text-sm font-bold text-slate-900">Google Gemini API 키 설정</h3>
                  <p className="text-[11px] text-slate-500">영어 수업 에이전트 크루를 구동하기 위한 API 키</p>
                </div>
              </div>
              {health.gemini !== 'missing_key' && (
                <button
                  type="button"
                  onClick={() => setKeyModalOpen(false)}
                  className="text-slate-400 hover:text-slate-600 text-sm font-bold"
                >
                  ✕
                </button>
              )}
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  API Key (Google AI Studio)
                </label>
                <input
                  type="password"
                  value={inputKey}
                  onChange={(e) => setInputKey(e.target.value)}
                  placeholder={maskedKey ? `현재 키: ${maskedKey}` : "AIzaSy..."}
                  className="w-full text-xs p-2.5 border border-slate-300 rounded-lg focus:outline-none focus:border-indigo-500 font-mono"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  입력된 키는 사용자 컴퓨터 로컬에만 안전하게 암호화/저장되며, 외부 서버나 로그에 일절 전송되지 않습니다.
                </p>
              </div>

              {keySaveMsg && (
                <div className={`text-xs p-2 rounded border font-medium ${
                  keySaveMsg.includes('실패') || keySaveMsg.includes('입력')
                    ? 'bg-rose-50 border-rose-200 text-rose-600'
                    : 'bg-emerald-50 border-emerald-200 text-emerald-600'
                }`}>
                  {keySaveMsg}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-150">
              {health.gemini !== 'missing_key' && (
                <button
                  type="button"
                  onClick={() => setKeyModalOpen(false)}
                  className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
                >
                  취소
                </button>
              )}
              <button
                type="button"
                onClick={handleSaveApiKey}
                disabled={isSavingKey}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm disabled:opacity-50"
              >
                {isSavingKey ? '저장 중...' : 'API 키 저장 및 활성화'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
