import React from 'react';
import { AppLogoIcon, SettingsIcon, ChannelIcon, BookIcon } from './common/Icons';

export default function Sidebar({
  channels,
  bots,
  activeChannelId,
  onSelectChannel,
  health
}) {
  // Determine status display based on health
  const getStatusDisplay = () => {
    if (!health || health.status === 'error') {
      return {
        dotClass: 'bg-rose-500',
        text: '오프라인 · 백엔드 연결 대기',
      };
    }
    if (health.gemini === 'missing_key') {
      return {
        dotClass: 'bg-amber-500',
        text: 'API 키 필요 · backend/.env 설정',
      };
    }
    return {
      dotClass: 'bg-emerald-500 animate-pulse',
      text: `연결됨 · Gemini · ${health.model || 'gemini-2.5-flash'}`,
    };
  };

  const statusInfo = getStatusDisplay();

  return (
    <aside className="w-[240px] shrink-0 h-screen bg-white border-r border-slate-200 flex flex-col select-none">
      {/* App Header */}
      <div className="p-4 border-b border-slate-150 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center shadow-sm">
            <AppLogoIcon className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-slate-900 leading-tight tracking-tight">
              English Crew
            </h1>
            <p className="text-[11px] text-slate-500">나만의 영어 수업·평가 크루</p>
          </div>
        </div>
        <button
          type="button"
          className="p-1.5 text-slate-400 hover:text-slate-600 rounded-md hover:bg-slate-100 transition-colors"
          title="설정"
        >
          <SettingsIcon className="w-4 h-4" />
        </button>
      </div>

      {/* Main Navigation (Scrollable) */}
      <div className="flex-1 overflow-y-auto p-3 space-y-5">
        {/* Channels Section */}
        <div>
          <div className="px-2 mb-1.5 flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              채널
            </span>
          </div>
          <div className="space-y-0.5">
            {channels.map((ch) => {
              const isActive = ch.id === activeChannelId;
              return (
                <button
                  key={ch.id}
                  type="button"
                  onClick={() => onSelectChannel(ch.id)}
                  className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    isActive
                      ? 'bg-indigo-50 text-indigo-700 font-semibold'
                      : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                  }`}
                >
                  <div className="flex items-center gap-2 truncate">
                    {ch.type === 'all' ? (
                      <ChannelIcon className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-600' : 'text-slate-400'}`} />
                    ) : (
                      <BookIcon className={`w-3.5 h-3.5 ${isActive ? 'text-indigo-600' : 'text-slate-400'}`} />
                    )}
                    <span className="truncate">{ch.name}</span>
                  </div>
                  {ch.badge && (
                    <span className="px-1.5 py-0.5 text-[10px] rounded bg-indigo-100 text-indigo-700 font-medium">
                      {ch.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Team Members Section */}
        <div>
          <div className="px-2 mb-1.5 flex items-center justify-between">
            <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              팀원 5
            </span>
          </div>
          <div className="space-y-1">
            {bots.map((bot) => {
              const isEnabled = bot.enabled !== false;
              return (
                <div
                  key={bot.id}
                  className={`flex items-center justify-between px-2.5 py-2 rounded-lg text-xs transition-colors ${
                    isEnabled ? 'hover:bg-slate-50 text-slate-800' : 'opacity-40 text-slate-400'
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <span className="text-sm select-none shrink-0">{bot.avatar || '🤖'}</span>
                    <div className="min-w-0">
                      <div className="font-medium truncate">{bot.name}</div>
                      <div className="text-[10px] text-slate-400 truncate">{bot.role}</div>
                    </div>
                  </div>
                  <span className="px-1.5 py-0.5 text-[10px] font-medium bg-slate-100 text-slate-600 border border-slate-200 rounded">
                    {bot.provider || 'Gemini'}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Bottom Status Bar */}
      <div className="p-3 border-t border-slate-200 bg-slate-50/70 text-xs flex items-center gap-2 text-slate-600">
        <span className={`w-2 h-2 rounded-full shrink-0 ${statusInfo.dotClass}`} />
        <span className="truncate font-medium">{statusInfo.text}</span>
      </div>
    </aside>
  );
}
