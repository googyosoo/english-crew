import React, { useState, useRef, useEffect } from 'react';
import TextMessage from './messages/TextMessage';
import DispatchCard from './messages/DispatchCard';
import ApprovalCard from './messages/ApprovalCard';
import ReportCard from './messages/ReportCard';
import { ChannelIcon, BookIcon, MicIcon, SendIcon } from './common/Icons';

export default function ChatArea({
  channel,
  messages,
  onSendMessage,
  onApprovalStatusChange
}) {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    const trimmed = inputText.trim();
    if (!trimmed) return;
    onSendMessage(trimmed);
    setInputText('');
  };

  return (
    <main className="flex-1 min-w-0 h-screen flex flex-col bg-[#f8f9fa]">
      {/* Channel Header */}
      <header className="h-16 px-6 border-b border-slate-200 bg-white flex items-center justify-between shrink-0 shadow-sm">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-9 h-9 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0 border border-indigo-100">
            {channel.type === 'all' ? (
              <ChannelIcon className="w-5 h-5" />
            ) : (
              <BookIcon className="w-5 h-5" />
            )}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h2 className="text-base font-bold text-slate-900 truncate">
                {channel.name}
              </h2>
              {channel.badge && (
                <span className="px-2 py-0.5 text-xs font-semibold bg-indigo-100 text-indigo-700 rounded-full">
                  {channel.badge}
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 truncate">{channel.desc}</p>
          </div>
        </div>


      </header>

      {/* Messages Scroll Area */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-3">
        {messages.map((msg) => {
          switch (msg.type) {
            case 'dispatch':
              return <DispatchCard key={msg.id} message={msg} />;
            case 'approval':
              return (
                <ApprovalCard
                  key={msg.id}
                  message={msg}
                  onStatusChange={onApprovalStatusChange}
                />
              );
            case 'report':
              return <ReportCard key={msg.id} message={msg} />;
            case 'user':
            case 'bot_text':
            default:
              return <TextMessage key={msg.id} message={msg} />;
          }
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="p-4 bg-white border-t border-slate-200 shrink-0">
        <div className="max-w-4xl mx-auto border border-slate-200 rounded-card p-2.5 focus-within:border-indigo-500 focus-within:ring-1 focus-within:ring-indigo-500 bg-white transition-all shadow-sm">
          <textarea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={2}
            placeholder={`${channel.name} 채널에 맡길 일을 적어 주세요`}
            className="w-full resize-none text-sm text-slate-800 placeholder-slate-400 focus:outline-none bg-transparent"
          />
          <div className="flex items-center justify-between pt-2 border-t border-slate-100 text-xs text-slate-400">
            <span className="select-none">Enter 보내기 · Shift+Enter 줄바꿈</span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled
                className="p-1.5 text-slate-300 hover:text-slate-400 rounded cursor-not-allowed"
                title="음성 입력 (준비 중)"
              >
                <MicIcon className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={handleSubmit}
                disabled={!inputText.trim()}
                className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                  inputText.trim()
                    ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm'
                    : 'bg-slate-100 text-slate-400 cursor-not-allowed'
                }`}
              >
                <span>보내기</span>
                <SendIcon className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
