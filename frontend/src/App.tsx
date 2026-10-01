import { useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import {
  ArrowUp, BookOpenText, Check, ChevronDown, Clock3, Copy, Database,
  ExternalLink, FileSearch2, GitBranch, Info, Menu, MessageSquareText,
  Plus, ShieldCheck, Sparkles, X,
} from 'lucide-react'

type Method = 'rag' | 'graph_rag'
type Mode = 'compare' | Method
type Citation = { article_id: string; label: string; url: string }
type Evidence = {
  id: string; text: string; title: string; article_number: number | null; clause: string | null;
  page_start: number; source_url: string
}
type GraphEdge = { from: string; to: string; relation: string; evidence_article_ids: string[]; evidence_url: string }
type RetrievalTrace = {
  method: string; top_k: number; seed_ids?: string[]; matched_topics?: string[];
  matched_documents?: string[]; relation_evidence_ids?: string[];
  candidate_count?: number; traversed_edges?: GraphEdge[];
  candidates: { id: string; score: number }[]
}
type MethodResult = {
  answer: string | null; citations: Citation[]; evidence: Evidence[];
  retrieval_trace: RetrievalTrace; retrieved_article_ids: string[];
  latency_ms: number; api_calls: number;
  token_usage: { input: number | null; output: number | null; thoughts: number | null; total: number | null } | null;
  error: string | null; provider: string; model: string | null
}
type ChatResponse = { question: string; mode: Mode; retrieve_only: boolean; results: Partial<Record<Method, MethodResult>> }
type Message = { id: string; role: 'user' | 'assistant'; content?: string; response?: ChatResponse; error?: string }
type Thread = { id: string; title: string; updatedAt: number; messages: Message[] }
type Suggestion = { id: string; question: string; category: string }
type Health = { ready: boolean; index_error?: string | null; key_configured: boolean; model: string; corpus_documents: number; corpus_chunks: number; ocr_documents: number; validity: string }

const STORAGE_KEY = 'haui-quy-che-ai-threads-v1'
const MODE_LABEL: Record<Mode, string> = {
  compare: 'So sánh hai phương pháp', rag: 'RAG vector', graph_rag: 'GraphRAG',
}

function loadThreads(): Thread[] {
  try {
    const parsed = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') as Thread[]
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function formatTime(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${Math.round(ms)} ms`
}

function readableError(error: string): string {
  if (/503|UNAVAILABLE/i.test(error)) return 'Gemini đang tạm quá tải (503). Vui lòng thử lại sau.'
  if (/429|RESOURCE_EXHAUSTED|quota/i.test(error)) return 'Gemini đã chạm hạn mức (429). Vui lòng thử lại khi hạn mức được khôi phục.'
  return error
}

function ResultPanel({ result, method }: { result: MethodResult; method: Method }) {
  const [copied, setCopied] = useState(false)
  const graph = method === 'graph_rag'
  const citedIds = new Set(result.citations.map(item => item.article_id))
  const copyAnswer = async () => {
    if (!result.answer) return
    await navigator.clipboard.writeText(result.answer)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1800)
  }

  return (
    <section className={`result-panel ${graph ? 'graph-panel' : 'vector-panel'}`} aria-label={`Kết quả ${graph ? 'GraphRAG' : 'RAG vector'}`}>
      <div className="result-header">
        <div className={`method-mark ${graph ? 'graph-mark' : 'vector-mark'}`}>
          {graph ? <GitBranch size={18} strokeWidth={2} /> : <FileSearch2 size={18} strokeWidth={2} />}
        </div>
        <div className="result-heading">
          <h3>{graph ? 'GraphRAG' : 'RAG vector'}</h3>
          <span>{graph ? 'Đồ thị văn bản & quan hệ' : 'Tìm kiếm ngữ nghĩa'}</span>
        </div>
        {result.answer && <button className="icon-button copy-button" onClick={copyAnswer} aria-label="Sao chép câu trả lời" title="Sao chép câu trả lời">{copied ? <Check size={17} /> : <Copy size={17} />}</button>}
      </div>

      <div className="result-body">
        {result.error && <div className="inline-alert" role="alert"><Info size={16} />{readableError(result.error)}</div>}
        {result.answer ? (
          <div className="answer-markdown"><ReactMarkdown>{result.answer}</ReactMarkdown></div>
        ) : (
          <p className="no-answer">Chưa có câu trả lời đã xác minh. Bạn vẫn có thể xem các đoạn được truy xuất bên dưới.</p>
        )}
      </div>

      <div className="result-stats" aria-label="Thông số lượt chạy">
        <span><Clock3 size={14} />{formatTime(result.latency_ms)}</span>
        <span><Sparkles size={14} />{result.api_calls} lượt Gemini</span>
        <span><Database size={14} />{result.token_usage?.total != null ? `${result.token_usage.total.toLocaleString('vi-VN')} token` : 'Chưa có token'}</span>
      </div>

      <div className="result-section">
        <div className="section-heading"><span>Nguồn được dẫn</span><small>{result.citations.length}</small></div>
        {result.citations.length ? (
          <div className="citation-list">
            {result.citations.map(item => (
              <a key={item.article_id} className="citation-link" href={item.url} target="_blank" rel="noreferrer">
                <BookOpenText size={15} aria-hidden="true" />
                <span>{item.label}</span>
                <ExternalLink size={14} aria-hidden="true" />
              </a>
            ))}
          </div>
        ) : <p className="muted-small">Câu trả lời không có trích dẫn điều khoản.</p>}
      </div>

      <details className="evidence-disclosure">
        <summary><span><BookOpenText size={16} /> Đoạn gốc đã truy xuất ({result.evidence.length})</span><ChevronDown size={16} /></summary>
        <div className="evidence-list">
          {result.evidence.map(item => (
            <article key={item.id} className="evidence-card">
              <div className="evidence-meta">
                <code>{item.id}</code>
                {citedIds.has(item.id) && <span className="used-badge">Đã dẫn</span>}
                <a href={`${item.source_url}#page=${item.page_start}`} target="_blank" rel="noreferrer">Trang {item.page_start} <ExternalLink size={12} /></a>
              </div>
              <p>{item.text}</p>
            </article>
          ))}
        </div>
      </details>

      <details className="trace-disclosure">
        <summary><span><GitBranch size={16} /> Cách tìm chứng cứ</span><ChevronDown size={16} /></summary>
        <div className="trace-content">
          <p><strong>Phương pháp:</strong> {graph ? 'Truy xuất theo quan hệ pháp lý, chủ đề và kết hợp từ khóa với vector' : 'So khớp cosine trên vector đa ngôn ngữ'}</p>
          {graph && <>
            <p><strong>Chủ đề khớp:</strong> {result.retrieval_trace.matched_topics?.map(s => s.replace('Topic:', '')).join(', ') || 'Không có'}</p>
            <p><strong>Văn bản nhận diện:</strong> {result.retrieval_trace.matched_documents?.map(s => s.replace('Document:', '')).join(', ') || 'Không có'}</p>
            <p><strong>Đoạn ứng viên:</strong> {result.retrieval_trace.candidate_count ?? 0}; <strong>cạnh mở rộng:</strong> {result.retrieval_trace.traversed_edges?.length ?? 0}</p>
            {!!result.retrieval_trace.traversed_edges?.length && <ul>{result.retrieval_trace.traversed_edges.slice(0, 8).map((edge, index) =>
              <li key={`${edge.from}-${edge.to}-${index}`}>{edge.from.replace('Document:', '')} → {edge.to.replace('Document:', '')} ({edge.relation}){' '}
                <a href={edge.evidence_url} target="_blank" rel="noreferrer">Xem chứng cứ <ExternalLink size={12} /></a></li>
            )}</ul>}
          </>}
          <ol>{result.retrieval_trace.candidates.map(item => <li key={item.id}><code>{item.id}</code><span>{item.score.toFixed(3)}</span></li>)}</ol>
        </div>
      </details>
    </section>
  )
}

function App() {
  const [threads, setThreads] = useState<Thread[]>(loadThreads)
  const [activeId, setActiveId] = useState<string | null>(() => loadThreads()[0]?.id ?? null)
  const [mode, setMode] = useState<Mode>('compare')
  const [retrieveOnly, setRetrieveOnly] = useState(false)
  const [health, setHealth] = useState<Health | null>(null)
  const [healthError, setHealthError] = useState(false)
  const [apiLimited, setApiLimited] = useState(false)
  const [apiUnavailable, setApiUnavailable] = useState(false)
  const [suggestions, setSuggestions] = useState<Suggestion[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const activeThread = threads.find(thread => thread.id === activeId)

  useEffect(() => {
    Promise.all([
      fetch('/api/health').then(response => response.ok ? response.json() as Promise<Health> : Promise.reject()),
      fetch('/api/suggestions').then(response => response.ok ? response.json() as Promise<Suggestion[]> : Promise.reject()),
    ]).then(([status, items]) => {
      setHealth(status)
      setSuggestions(items)
      if (!status.key_configured) setRetrieveOnly(true)
    }).catch(() => setHealthError(true))
  }, [])

  useEffect(() => {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(threads.slice(0, 12))) } catch { /* Bộ nhớ trình duyệt đầy: phiên hiện tại vẫn hoạt động. */ }
  }, [threads])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [activeThread?.messages.length, busy])

  const newChat = () => {
    setActiveId(null)
    setDraft('')
    setSidebarOpen(false)
    window.setTimeout(() => inputRef.current?.focus(), 0)
  }

  const send = async (raw: string) => {
    const question = raw.trim()
    if (!question || busy || !health?.ready) return
    const threadId = activeId ?? crypto.randomUUID()
    const userMessage: Message = { id: crypto.randomUUID(), role: 'user', content: question }
    setThreads(current => {
      const existing = current.find(item => item.id === threadId)
      if (existing) return current.map(item => item.id === threadId ? { ...item, updatedAt: Date.now(), messages: [...item.messages, userMessage] } : item)
      return [{ id: threadId, title: question.slice(0, 55), updatedAt: Date.now(), messages: [userMessage] }, ...current]
    })
    setActiveId(threadId)
    setDraft('')
    setBusy(true)
    try {
      const reply = await fetch('/api/chat', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, mode, retrieve_only: retrieveOnly }),
      })
      if (!reply.ok) {
        const body = await reply.json().catch(() => ({})) as { detail?: string }
        throw new Error(body.detail || `Máy chủ trả lỗi ${reply.status}`)
      }
      const response = await reply.json() as ChatResponse
      setApiUnavailable(Object.values(response.results).some(item => /503|UNAVAILABLE/i.test(item?.error || '')))
      if (Object.values(response.results).some(item => /429|resource_exhausted|quota/i.test(item?.error || ''))) {
        setApiLimited(true)
        setRetrieveOnly(true)
      }
      setThreads(current => current.map(item => item.id === threadId ? { ...item, updatedAt: Date.now(), messages: [...item.messages, { id: crypto.randomUUID(), role: 'assistant', response }] } : item))
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Không kết nối được máy chủ'
      setThreads(current => current.map(item => item.id === threadId ? { ...item, messages: [...item.messages, { id: crypto.randomUUID(), role: 'assistant', error: message }] } : item))
    } finally {
      setBusy(false)
      window.setTimeout(() => inputRef.current?.focus(), 0)
    }
  }

  return (
    <div className="app-shell">
      {sidebarOpen && <button className="sidebar-scrim" aria-label="Đóng menu" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`} aria-label="Thanh điều hướng">
        <div className="sidebar-top">
          <div className="brand"><div className="brand-icon"><BookOpenText size={21} /></div><div><strong>QUY CHẾ AI</strong><small>HaUI · Trợ lý học tập</small></div></div>
          <button className="sidebar-close icon-button" onClick={() => setSidebarOpen(false)} aria-label="Đóng menu"><X size={19} /></button>
        </div>
        <button className="new-chat" onClick={newChat}><Plus size={18} /> Cuộc trò chuyện mới</button>
        <div className="sidebar-section-title">GẦN ĐÂY</div>
        <nav className="thread-list" aria-label="Lịch sử trò chuyện">
          {threads.length ? threads.map(thread => (
            <button key={thread.id} className={`thread-item ${activeId === thread.id ? 'active' : ''}`} onClick={() => { setActiveId(thread.id); setSidebarOpen(false) }} title={thread.title}>
              <MessageSquareText size={17} /><span>{thread.title}</span>
            </button>
          )) : <p className="empty-history">Các câu hỏi của bạn sẽ xuất hiện ở đây.</p>}
        </nav>
        <div className="sidebar-bottom">
          <div className="corpus-card"><div className="corpus-card-top"><Database size={17} /><span>NGUỒN DỮ LIỆU</span></div><strong>{health?.corpus_documents ?? '—'} văn bản · {health?.corpus_chunks ?? '—'} đoạn</strong><small>{health?.ocr_documents ?? '—'} bản OCR cần đối chiếu khi trích dẫn</small></div>
          <div className="sidebar-note"><ShieldCheck size={16} /><span>Trích dẫn mở trực tiếp PDF HaUI. Hiệu lực hiện hành chưa xác minh.</span></div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="topbar-left">
            <button className="mobile-menu icon-button" onClick={() => setSidebarOpen(true)} aria-label="Mở menu"><Menu size={21} /></button>
            <div className="header-title"><span className="header-eyebrow">KHÔNG GIAN NGHIÊN CỨU</span><strong>Hỏi đáp quy chế đào tạo</strong></div>
          </div>
          <div className="topbar-right">
            <div className={`service-status ${healthError || (health && !health.ready) || apiLimited || apiUnavailable ? 'status-error' : ''}`} title={healthError ? 'Không kết nối được backend' : health && !health.ready ? 'Nguồn dữ liệu chưa sẵn sàng, vui lòng thử lại sau.' : apiLimited ? 'Gemini vừa trả lỗi hạn mức; đã chuyển sang chỉ truy xuất' : apiUnavailable ? 'Gemini vừa trả lỗi quá tải 503' : health?.key_configured ? `Đã cấu hình key; model ${health.model}. Tình trạng dịch vụ được kiểm tra khi gửi câu hỏi.` : 'Chế độ truy xuất'}>
              <i /> <span>{healthError ? 'Mất kết nối' : health && !health.ready ? 'Dữ liệu chưa sẵn sàng' : apiLimited ? 'Đã chạm hạn mức' : apiUnavailable ? 'Gemini tạm quá tải' : health?.key_configured ? 'Đã cấu hình key' : 'Chỉ truy xuất'}</span>
            </div>
            <div className="topbar-avatar" aria-label="HaUI">H</div>
          </div>
        </header>

        <div className="workspace">
          <div className="workspace-toolbar">
            <div className="toolbar-label"><span className="live-dot" /> {activeThread ? 'Cuộc trò chuyện' : 'Bắt đầu khám phá'} <span className="toolbar-divider" /> <span>{MODE_LABEL[mode]}</span></div>
            <div className="toolbar-context"><BookOpenText size={15} /> Corpus HaUI <span>·</span> Hiệu lực chưa xác minh</div>
          </div>

          <div className="conversation-scroll">
            {!activeThread ? (
              <div className="welcome">
                <div className="welcome-symbol"><BookOpenText size={31} strokeWidth={1.7} /></div>
                <div className="welcome-overline">QUY CHẾ AI · HaUI</div>
                <h1>Hỏi quy chế.<br /><em>Xem tận nguồn.</em></h1>
                <p>Đặt câu hỏi về học phần, điểm số hoặc tốt nghiệp. Mỗi câu trả lời đi kèm điều khoản gốc để bạn tự kiểm tra.</p>
                <div className="suggestion-heading"><span>Câu hỏi gợi ý</span><div /></div>
                <div className="suggestion-grid">
                  {suggestions.slice(0, 4).map((item, index) => (
                    <button key={item.id} className="suggestion-card" onClick={() => send(item.question)} disabled={!health?.ready || busy}>
                      <span className="suggestion-icon">{index % 2 === 0 ? <BookOpenText size={18} /> : <GitBranch size={18} />}</span>
                      <span>{item.question}</span>
                      <ArrowUp size={16} className="suggestion-arrow" />
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="messages">
                {activeThread.messages.map(message => message.role === 'user' ? (
                  <div key={message.id} className="user-message"><div className="user-avatar">B</div><div className="user-bubble">{message.content}</div></div>
                ) : (
                  <div key={message.id} className="assistant-message">
                    <div className="assistant-heading"><div className="assistant-avatar"><BookOpenText size={18} /></div><div><strong>Quy Chế AI</strong><small>{message.response?.retrieve_only ? 'Kết quả truy xuất' : 'Câu trả lời dựa trên tài liệu'}</small></div></div>
                    {message.error && <div className="request-error" role="alert">{message.error}</div>}
                    {message.response && <div className={`result-grid ${message.response.mode === 'compare' ? 'two-results' : ''}`}>
                      {(['rag', 'graph_rag'] as Method[]).filter(method => message.response?.results[method]).map(method => <ResultPanel key={method} method={method} result={message.response!.results[method]!} />)}
                    </div>}
                  </div>
                ))}
                {busy && <div className="assistant-message loading-message"><div className="assistant-heading"><div className="assistant-avatar"><BookOpenText size={18} /></div><div><strong>Quy Chế AI</strong><small>Đang đối chiếu điều khoản...</small></div></div><div className="loading-card"><span /><span /><span /><p>Đang tìm chứng cứ và soạn câu trả lời</p></div></div>}
                <div ref={bottomRef} />
              </div>
            )}
          </div>

          <div className="composer-wrap">
            <div className="composer-controls">
              <div className="mode-switch" role="group" aria-label="Phương pháp truy xuất">
                {(['compare', 'rag', 'graph_rag'] as Mode[]).map(item => <button key={item} className={mode === item ? 'selected' : ''} onClick={() => setMode(item)} aria-pressed={mode === item}>{item === 'compare' ? 'So sánh' : item === 'rag' ? 'RAG vector' : 'GraphRAG'}</button>)}
              </div>
              <label className="retrieve-toggle"><input type="checkbox" checked={retrieveOnly} onChange={event => setRetrieveOnly(event.target.checked)} /><span className="switch-track" /> Chỉ truy xuất</label>
            </div>
            <form className="composer" onSubmit={event => { event.preventDefault(); send(draft) }}>
              <textarea ref={inputRef} value={draft} onChange={event => setDraft(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); send(draft) } }} placeholder="Hỏi về quy chế đào tạo HaUI..." rows={2} maxLength={2000} aria-label="Nhập câu hỏi" disabled={busy} />
              <button className="send-button" type="submit" aria-label="Gửi câu hỏi" disabled={busy || !draft.trim() || !health?.ready}><ArrowUp size={21} /></button>
            </form>
            <div className="composer-footer"><span><Info size={13} /> Chỉ sử dụng tài liệu trong corpus; kiểm tra PDF trước khi áp dụng.</span><span>Enter để gửi · Shift + Enter xuống dòng</span></div>
          </div>
        </div>
      </main>
    </div>
  )
}

export default App
