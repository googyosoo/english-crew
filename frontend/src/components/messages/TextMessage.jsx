import React from 'react';

export default function TextMessage({ message }) {
  const isUser = message.type === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end my-3">
        <div className="max-w-[80%] bg-white border border-slate-200 shadow-sm rounded-card p-4 text-slate-800">
          <div className="flex items-center justify-between mb-1 text-xs text-slate-500">
            <span className="font-semibold text-slate-700">{message.sender || '교사'}</span>
            <span>{message.time}</span>
          </div>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{message.content}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-3 my-3">
      <div className="w-8 h-8 rounded-full bg-indigo-100 border border-indigo-200 flex items-center justify-center shrink-0 text-sm">
        {message.botId === 'coordinator' ? '🎯' : '🤖'}
      </div>
      <div className="flex-1 max-w-[85%]">
        <div className="flex items-center gap-2 mb-1 text-xs text-slate-500">
          <span className="font-semibold text-slate-800">{message.sender}</span>
          <span>{message.time}</span>
        </div>
        <div className="bg-white border border-slate-200 shadow-sm rounded-card p-4 text-slate-800 text-sm leading-relaxed whitespace-pre-wrap">
          {message.content}
        </div>
      </div>
    </div>
  );
}
