import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  ArtifactIcon,
  ContextIcon,
  RoutineIcon,
  ShieldIcon,
  FolderIcon,
  CheckIcon
} from './common/Icons';
import {
  fetchChannelContext,
  saveChannelContext,
  getExportUrl,
  fetchExportDir,
  saveExportDir
} from '../api/client';

const BOT_NAMES = {
  coordinator: '코디봇',
  assessment: '평가봇',
  curriculum: '교육과정봇',
  lesson: '수업봇',
  record: '기록봇'
};

export default function RightPanel({
  channel,
  contextNote,
  deliverable,
  workspaceDir
}) {
  const [activeTab, setActiveTab] = useState('deliverable');

  // Phase 4 Export & Settings state
  const [exportMenuOpen, setExportMenuOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [exportDir, setExportDir] = useState('');
  const [isSavingDir, setIsSavingDir] = useState(false);
  const [dirSaveMsg, setDirSaveMsg] = useState('');

  // Load export directory setting
  useEffect(() => {
    fetchExportDir()
      .then(data => {
        if (data?.export_dir) setExportDir(data.export_dir);
      })
      .catch(e => console.warn('Failed to load export dir:', e));
  }, []);

  const handleExport = (format) => {
    const reqId = deliverable?.request_id || deliverable?.requestId || 'req_latest';
    const url = getExportUrl(reqId, format);
    window.open(url, '_blank');
    setExportMenuOpen(false);
  };

  const handleSaveExportDir = async () => {
    if (!exportDir.trim()) return;
    setIsSavingDir(true);
    setDirSaveMsg('');
    try {
      await saveExportDir(exportDir.trim());
      setDirSaveMsg('저장되었습니다.');
      setTimeout(() => {
        setDirSaveMsg('');
        setSettingsOpen(false);
      }, 1500);
    } catch (err) {
      setDirSaveMsg(`오류: ${err.message}`);
    } finally {
      setIsSavingDir(false);
    }
  };

  // Load real context notes from backend
  const loadContextNotes = async () => {
    if (!channel?.id) return;
    try {
      const notes = await fetchChannelContext(channel.id);
      setChannelNotes(notes || []);
      // Find body for selectedUnit
      const foundBody = notes.find(n => n.kind === '본문' && n.unit === selectedUnit);
      setBodyText(foundBody ? foundBody.content : '');
    } catch (e) {
      console.warn('Failed to load channel context:', e);
    }
  };

  useEffect(() => {
    loadContextNotes();
  }, [channel?.id, selectedUnit]);

  const handleSaveBody = async () => {
    if (!channel?.id || !bodyText.trim()) return;
    setIsSavingBody(true);
    setBodySaveMessage('');
    try {
      await saveChannelContext(channel.id, {
        course_code: channel.course_code || 'COMMON',
        unit: selectedUnit,
        kind: '본문',
        content: bodyText.trim()
      });
      setBodySaveMessage('본문이 저장되었습니다.');
      await loadContextNotes();
      setTimeout(() => setBodySaveMessage(''), 3000);
    } catch (err) {
      setBodySaveMessage(`저장 실패: ${err.message}`);
    } finally {
      setIsSavingBody(false);
    }
  };

  const lessonRecords = channelNotes.filter(n => n.kind === '차시기록');
  const progressNotes = channelNotes.filter(n => n.kind === '진도');

  const workspacePath = workspaceDir || channel?.workspace_dir || (
    channel?.type === 'all' || channel?.id === 'general'
      ? 'data/workspaces/_공통/'
      : `data/workspaces/${(channel?.name || '').replace(/\s+/g, '_')}/${selectedUnit}`
  );

  return (
    <aside className="w-[320px] shrink-0 h-screen bg-white border-l border-slate-200 flex flex-col select-none">
      {/* Tab Navigation */}
      <div className="flex border-b border-slate-200 bg-slate-50/60 p-1.5 gap-1 shrink-0 items-center">
        <button
          type="button"
          onClick={() => setActiveTab('deliverable')}
          className={`flex-1 py-1.5 px-2 text-xs font-semibold rounded-md transition-all flex items-center justify-center gap-1.5 ${
            activeTab === 'deliverable'
              ? 'bg-white text-indigo-700 shadow-sm border border-slate-200/80'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <ArtifactIcon className="w-3.5 h-3.5" />
          <span>산출물</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('context')}
          className={`flex-1 py-1.5 px-2 text-xs font-semibold rounded-md transition-all flex items-center justify-center gap-1.5 ${
            activeTab === 'context'
              ? 'bg-white text-indigo-700 shadow-sm border border-slate-200/80'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <ContextIcon className="w-3.5 h-3.5" />
          <span>수업 맥락</span>
        </button>
        <button
          type="button"
          onClick={() => setActiveTab('routine')}
          className={`flex-1 py-1.5 px-2 text-xs font-semibold rounded-md transition-all flex items-center justify-center gap-1.5 ${
            activeTab === 'routine'
              ? 'bg-white text-indigo-700 shadow-sm border border-slate-200/80'
              : 'text-slate-500 hover:text-slate-800'
          }`}
        >
          <RoutineIcon className="w-3.5 h-3.5" />
          <span>루틴</span>
        </button>
        <button
          type="button"
          onClick={() => setSettingsOpen(true)}
          title="설정 (내보내기 폴더 등)"
          className="p-1.5 text-slate-500 hover:text-slate-800 hover:bg-slate-200/60 rounded-md transition-colors"
        >
          <span className="text-xs">⚙️</span>
        </button>
      </div>

      {/* Tab Content Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Tab 1: 산출물 미리보기 */}
        {activeTab === 'deliverable' && (
          <div>
            {deliverable && deliverable.content ? (
              <div className="space-y-3">
                <div className="pb-2 border-b border-slate-150">
                  <div className="flex items-center justify-between relative">
                    <span className="text-[10px] font-semibold tracking-wider text-indigo-600 uppercase bg-indigo-50 px-2 py-0.5 rounded border border-indigo-200">
                      산출물 미리보기
                    </span>
                    <div className="relative">
                      <button
                        type="button"
                        onClick={() => setExportMenuOpen(!exportMenuOpen)}
                        className="px-2.5 py-1 text-[11px] font-semibold bg-indigo-600 hover:bg-indigo-700 text-white rounded shadow-sm flex items-center gap-1 transition-colors"
                      >
                        <span>내보내기</span>
                        <span className="text-[9px]">▾</span>
                      </button>

                      {exportMenuOpen && (
                        <div className="absolute right-0 mt-1 w-36 bg-white border border-slate-200 rounded-lg shadow-lg py-1 z-20">
                          <button
                            type="button"
                            onClick={() => handleExport('docx')}
                            className="w-full text-left px-3 py-1.5 text-xs text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 flex items-center gap-2"
                          >
                            <span>📄</span>
                            <span>Word (.docx)</span>
                          </button>
                          <button
                            type="button"
                            onClick={() => handleExport('md')}
                            className="w-full text-left px-3 py-1.5 text-xs text-slate-700 hover:bg-indigo-50 hover:text-indigo-600 flex items-center gap-2"
                          >
                            <span>📝</span>
                            <span>Markdown (.md)</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                  <h3 className="text-sm font-bold text-slate-900 mt-2">
                    {deliverable.title || '작업 산출물'}
                  </h3>
                  <div className="text-[11px] text-slate-500 mt-1 flex items-center gap-2">
                    <span>작성: @{BOT_NAMES[deliverable.bot] || BOT_NAMES[deliverable.bot_id] || deliverable.bot || deliverable.bot_id || '평가봇'}</span>
                    {deliverable.status && (
                      <>
                        <span>·</span>
                        <span className={`font-medium ${deliverable.status === 'done' ? 'text-emerald-600' : 'text-amber-600'}`}>
                          {deliverable.status === 'done' ? '완료' : deliverable.status}
                        </span>
                      </>
                    )}
                  </div>
                </div>

                {/* Formatted Content with ReactMarkdown */}
                <div className="bg-slate-50 p-3 rounded-card border border-slate-200 text-xs text-slate-700 leading-relaxed max-h-[520px] overflow-y-auto prose prose-sm prose-slate max-w-none">
                  <ReactMarkdown>
                    {deliverable.content}
                  </ReactMarkdown>
                </div>
              </div>
            ) : (
              <div className="h-64 flex flex-col items-center justify-center text-center p-6 border-2 border-dashed border-slate-200 rounded-card text-slate-400">
                <ArtifactIcon className="w-8 h-8 mb-2 text-slate-300" />
                <p className="text-xs font-medium text-slate-600">선택된 산출물이 없습니다</p>
                <p className="text-[11px] text-slate-400 mt-1">
                  작업 보고의 항목을 누르면 해당 마크다운 산출물이 여기에 렌더링됩니다.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: 수업 맥락 (Phase 3 실데이터 연동) */}
        {activeTab === 'context' && (
          <div className="space-y-3.5">
            <div className="flex items-center justify-between pb-2 border-b border-slate-200">
              <div>
                <span className="text-[10px] font-semibold text-slate-400 uppercase tracking-wider block">
                  과목 및 단원
                </span>
                <h3 className="text-sm font-bold text-slate-900">
                  {channel?.name || '영어I'}
                </h3>
              </div>
              <div className="flex items-center gap-1.5">
                <select
                  value={selectedUnit}
                  onChange={(e) => setSelectedUnit(e.target.value)}
                  className="text-xs bg-slate-50 border border-slate-200 rounded px-2 py-1 font-medium text-slate-700 focus:outline-none focus:border-indigo-500"
                >
                  <option value="1과">1과</option>
                  <option value="2과">2과</option>
                  <option value="3과">3과</option>
                  <option value="4과">4과</option>
                  <option value="5과">5과</option>
                </select>
              </div>
            </div>

            {/* 단원 본문 편집 카드 */}
            <div className="bg-slate-50 rounded-card p-3 border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-xs text-slate-800 flex items-center gap-1.5">
                  <span>📖</span>
                  <span>{selectedUnit} 본문 내용</span>
                </span>
                <button
                  type="button"
                  onClick={handleSaveBody}
                  disabled={isSavingBody || !bodyText.trim()}
                  className={`text-[11px] px-2.5 py-1 rounded font-semibold transition-all shadow-sm ${
                    bodyText.trim()
                      ? 'bg-indigo-600 hover:bg-indigo-700 text-white'
                      : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                  }`}
                >
                  {isSavingBody ? '저장 중...' : '본문 저장'}
                </button>
              </div>

              {bodySaveMessage && (
                <div className={`text-[10px] p-1.5 rounded font-medium ${
                  bodySaveMessage.includes('실패') ? 'bg-rose-50 text-rose-600' : 'bg-emerald-50 text-emerald-600'
                }`}>
                  {bodySaveMessage}
                </div>
              )}

              <textarea
                value={bodyText}
                onChange={(e) => setBodyText(e.target.value)}
                rows={6}
                placeholder={`${selectedUnit} 교과서 본문 텍스트를 여기에 붙여넣으세요. 평가봇·수업봇이 문항과 활동을 제작할 때 직접 참조합니다.`}
                className="w-full text-xs p-2.5 bg-white border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:border-indigo-500 leading-relaxed resize-none"
              />
            </div>

            {/* 진도 현황 */}
            <div className="bg-slate-50 rounded-card p-3 border border-slate-200 text-xs space-y-1">
              <span className="font-bold text-slate-700 block">진도 현황</span>
              <div className="text-slate-600 font-medium bg-white px-2.5 py-1.5 rounded border border-slate-200">
                {progressNotes[0]?.content || `${selectedUnit} 본문 분석 및 수행평가 진행 중`}
              </div>
            </div>

            {/* 차시기록 (결재 승인 시 자동 누적) */}
            <div className="bg-slate-50 rounded-card p-3 border border-slate-200 text-xs space-y-2">
              <span className="font-bold text-slate-700 block">차시기록 (확정 내역)</span>
              {lessonRecords.length > 0 ? (
                <div className="space-y-1.5 max-h-40 overflow-y-auto">
                  {lessonRecords.map((rec) => (
                    <div key={rec.id} className="bg-white p-2 rounded border border-slate-200 text-[11px] text-slate-600 leading-snug">
                      <span className="font-mono text-[10px] text-indigo-600 block mb-0.5">{rec.unit}</span>
                      {rec.content}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-[11px] text-slate-400 bg-white p-2.5 rounded border border-slate-200 text-center">
                  결재 승인된 작업이 차시기록으로 자동 누적됩니다.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tab 3: 루틴 (Phase 4 준비 중) */}
        {activeTab === 'routine' && (
          <div className="space-y-4">
            <div className="p-4 rounded-card bg-indigo-50/60 border border-indigo-150 text-center">
              <RoutineIcon className="w-8 h-8 mx-auto text-indigo-500 mb-2" />
              <h4 className="text-xs font-bold text-indigo-900">정기 자동화 루틴</h4>
              <span className="inline-block mt-1 px-2 py-0.5 text-[10px] font-semibold bg-indigo-100 text-indigo-700 rounded-full">
                Phase 4 지원 예정 (준비 중)
              </span>
              <p className="text-[11px] text-indigo-700/80 mt-2 leading-relaxed">
                지정된 주기(요일·시각)에 맞춰 주간 수능 문항 세트 출제, 학기말 세특 일괄 생성 등의 자동화 루틴이 제공될 예정입니다.
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Bottom Fixed Cards (2 cards) */}
      <div className="p-3 border-t border-slate-200 bg-slate-50/70 space-y-2 shrink-0">
        {/* Card 1: 학생 데이터 보호 */}
        <div className="p-2.5 rounded-card bg-white border border-slate-200 shadow-sm flex items-start gap-2.5">
          <div className="p-1.5 rounded-lg bg-emerald-50 text-emerald-600 shrink-0 border border-emerald-100">
            <ShieldIcon className="w-4 h-4" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-slate-900">학생 데이터 보호</span>
              <span className="text-[9px] bg-emerald-100 text-emerald-700 px-1 py-0.2 rounded font-semibold">
                안전
              </span>
            </div>
            <p className="text-[11px] text-slate-500 leading-tight mt-0.5">
              실명은 로컬에만 저장, AI에는 번호로 전송
            </p>
          </div>
        </div>

        {/* Card 2: 작업 폴더 */}
        <div className="p-2.5 rounded-card bg-white border border-slate-200 shadow-sm flex items-start gap-2.5">
          <div className="p-1.5 rounded-lg bg-indigo-50 text-indigo-600 shrink-0 border border-indigo-100">
            <FolderIcon className="w-4 h-4" />
          </div>
          <div className="min-w-0 flex-1">
            <span className="text-xs font-bold text-slate-900">작업 폴더</span>
            <p className="text-[11px] font-mono text-slate-600 truncate mt-0.5" title={workspacePath}>
              {workspacePath}
            </p>
          </div>
        </div>
      </div>

      {/* Settings Modal (내보내기 폴더 설정) */}
      {settingsOpen && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl border border-slate-200 max-w-md w-full p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-150">
              <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <span>⚙️</span>
                <span>환경 설정</span>
              </h3>
              <button
                type="button"
                onClick={() => setSettingsOpen(false)}
                className="text-slate-400 hover:text-slate-600 text-sm font-bold"
              >
                ✕
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  산출물 내보내기 폴더
                </label>
                <input
                  type="text"
                  value={exportDir}
                  onChange={(e) => setExportDir(e.target.value)}
                  placeholder="예: C:\Users\user\Documents"
                  className="w-full text-xs p-2 border border-slate-300 rounded-lg focus:outline-none focus:border-indigo-500 font-mono"
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  기본값은 사용자 문서(Documents) 폴더입니다.
                </p>
              </div>

              {dirSaveMsg && (
                <div className="text-xs font-medium text-emerald-600 bg-emerald-50 p-2 rounded border border-emerald-200">
                  {dirSaveMsg}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-150">
              <button
                type="button"
                onClick={() => setSettingsOpen(false)}
                className="px-3 py-1.5 text-xs text-slate-600 hover:bg-slate-100 rounded-lg"
              >
                닫기
              </button>
              <button
                type="button"
                onClick={handleSaveExportDir}
                disabled={isSavingDir}
                className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg shadow-sm disabled:opacity-50"
              >
                {isSavingDir ? '저장 중...' : '저장'}
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
