import React, { useState, useEffect, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import RightPanel from './components/RightPanel';
import {
  CHANNELS as MOCK_CHANNELS,
  BOTS as MOCK_BOTS,
  INITIAL_MESSAGES as MOCK_MESSAGES,
  CONTEXT_NOTES,
  ROUTINES,
  MOCK_DELIVERABLE_ENG1
} from './mocks/mockData';
import {
  fetchHealth,
  fetchChannels,
  fetchBots,
  fetchMessages,
  sendRequest,
  decideApproval,
  fetchTaskDeliverable,
  subscribeToRequestEvents
} from './api/client';

export default function App() {
  const [channels, setChannels] = useState(MOCK_CHANNELS);
  const [bots, setBots] = useState(MOCK_BOTS);
  const [activeChannelId, setActiveChannelId] = useState('eng1');
  const [messagesMap, setMessagesMap] = useState(MOCK_MESSAGES);
  const [health, setHealth] = useState({ status: 'ok', gemini: 'missing_key', model: 'gemini-2.5-flash' });
  const [activeDeliverable, setActiveDeliverable] = useState(MOCK_DELIVERABLE_ENG1);
  const [statusMessage, setStatusMessage] = useState('');

  // Track active SSE cleanup
  const sseCleanupRef = useRef(null);

  // 1. Initial Load: Health, Channels, Bots
  useEffect(() => {
    let isMounted = true;

    async function loadInitialData() {
      try {
        const h = await fetchHealth();
        if (isMounted) setHealth(h);

        const chs = await fetchChannels();
        if (isMounted && chs && chs.length > 0) {
          // Merge API channels with mock attributes (desc, badge)
          const mergedChannels = chs.map((apiCh) => {
            const mock = MOCK_CHANNELS.find((m) => m.id === apiCh.id);
            return {
              ...apiCh,
              desc: mock?.desc || '',
              badge: mock?.badge || (apiCh.type === 'all' ? '전원' : null)
            };
          });
          setChannels(mergedChannels);
        }

        const bts = await fetchBots();
        if (isMounted && bts && bts.length > 0) {
          const mergedBots = bts.map((apiBot) => {
            const mock = MOCK_BOTS.find((m) => m.id === apiBot.id);
            return {
              ...apiBot,
              avatar: mock?.avatar || '🤖',
              provider: 'Gemini'
            };
          });
          setBots(mergedBots);
        }
      } catch (err) {
        console.warn('Backend offline or init error, using mocks:', err);
      }
    }

    loadInitialData();

    // Health poll every 10 seconds
    const interval = setInterval(async () => {
      const h = await fetchHealth();
      if (isMounted) setHealth(h);
    }, 10000);

    return () => {
      isMounted = false;
      clearInterval(interval);
      if (sseCleanupRef.current) sseCleanupRef.current();
    };
  }, []);

  // 2. Load Channel Messages when switching channels
  const loadChannelMessages = async (channelId) => {
    try {
      const dbMsgs = await fetchMessages(channelId);
      if (dbMsgs && dbMsgs.length > 0) {
        // Format DB messages
        const formatted = dbMsgs.map((m) => ({
          ...m,
          sender: m.sender === 'teacher' ? '교사' : m.sender === 'coordinator' ? '코디봇' : m.sender,
          time: m.created_at ? m.created_at.slice(11, 16) : ''
        }));
        setMessagesMap((prev) => ({
          ...prev,
          [channelId]: formatted
        }));
      }
    } catch (e) {
      console.warn(`Failed to fetch messages for ${channelId}:`, e);
    }
  };

  useEffect(() => {
    loadChannelMessages(activeChannelId);
  }, [activeChannelId]);

  const activeChannel = channels.find((c) => c.id === activeChannelId) || channels[0];
  const activeMessages = messagesMap[activeChannelId] || [];
  const activeContext = CONTEXT_NOTES[activeChannelId] || null;

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
                    t.id === data.task_id ? { ...t, status: data.status, output_path: data.output_path } : t
                  );
                  return { ...m, metadata: { ...m.metadata, tasks: updatedTasks } };
                }
                return m;
              })
            };
          });
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

  // 5. Select deliverable to view in RightPanel
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
      console.warn('Failed to fetch deliverable content, showing basic info:', e);
      setActiveDeliverable({
        title: taskItem.title || '산출물',
        bot: taskItem.bot || '평가봇',
        status: taskItem.status,
        output_path: taskItem.output_path,
        content: taskItem.deliverable || '산출물 내용을 불러올 수 없습니다.'
      });
    }
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#f8f9fa] text-slate-800 font-sans">
      {/* 1. Left Sidebar: 240px */}
      <Sidebar
        channels={channels}
        bots={bots}
        activeChannelId={activeChannelId}
        onSelectChannel={handleSelectChannel}
        health={health}
      />

      {/* 2. Center Chat Area: Variable Width */}
      <ChatArea
        channel={activeChannel}
        messages={activeMessages}
        onSendMessage={handleSendMessage}
        onApprovalDecision={handleApprovalDecision}
        onSelectDeliverable={handleSelectDeliverable}
        statusMessage={statusMessage}
      />

      {/* 3. Right Side Panel: 320px */}
      <RightPanel
        channel={activeChannel}
        contextNote={activeContext}
        routines={ROUTINES}
        deliverable={activeDeliverable}
      />
    </div>
  );
}
