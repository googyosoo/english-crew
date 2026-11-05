import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatArea from './components/ChatArea';
import RightPanel from './components/RightPanel';
import {
  CHANNELS,
  BOTS,
  INITIAL_MESSAGES,
  CONTEXT_NOTES,
  ROUTINES,
  MOCK_DELIVERABLE_ENG1
} from './mocks/mockData';

export default function App() {
  const [activeChannelId, setActiveChannelId] = useState('eng1');
  const [messagesMap, setMessagesMap] = useState(INITIAL_MESSAGES);

  const activeChannel =
    CHANNELS.find((c) => c.id === activeChannelId) || CHANNELS[0];
  const activeMessages = messagesMap[activeChannelId] || [];
  const activeContext = CONTEXT_NOTES[activeChannelId] || null;

  // Active deliverable: show mock deliverable for eng1, null for others by default
  const activeDeliverable =
    activeChannelId === 'eng1' ? MOCK_DELIVERABLE_ENG1 : null;

  const handleSelectChannel = (channelId) => {
    setActiveChannelId(channelId);
  };

  const handleSendMessage = (text) => {
    const now = new Date();
    const hours = now.getHours();
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const timeStr = `${hours >= 12 ? '오후' : '오전'} ${hours % 12 || 12}:${minutes}`;

    const newMsg = {
      id: `user-${Date.now()}`,
      type: 'user',
      sender: '교사',
      time: timeStr,
      content: text
    };

    setMessagesMap((prev) => ({
      ...prev,
      [activeChannelId]: [...(prev[activeChannelId] || []), newMsg]
    }));
  };

  const handleApprovalStatusChange = (messageId, status) => {
    setMessagesMap((prev) => {
      const channelMsgs = prev[activeChannelId] || [];
      const updated = channelMsgs.map((m) =>
        m.id === messageId ? { ...m, status } : m
      );
      return {
        ...prev,
        [activeChannelId]: updated
      };
    });
  };

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-[#f8f9fa] text-slate-800 font-sans">
      {/* 1. Left Sidebar: 240px */}
      <Sidebar
        channels={CHANNELS}
        bots={BOTS}
        activeChannelId={activeChannelId}
        onSelectChannel={handleSelectChannel}
      />

      {/* 2. Center Chat Area: Variable Width */}
      <ChatArea
        channel={activeChannel}
        messages={activeMessages}
        onSendMessage={handleSendMessage}
        onApprovalStatusChange={handleApprovalStatusChange}
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
