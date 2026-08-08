import { useEffect, useRef, useState } from 'react'
import { ChatMsg } from './components/ChatMsg'
import SelfDrivePanel from './components/SelfDrivePanel'
import AgentsPage from './components/AgentsPage'
import ProfilePanel from './components/ProfilePanel'
import { useStockBackend } from './hooks/useStockBackend'
import type { Stock, Tab } from './types'

const FALLBACK_STOCKS: Stock[] = [
  { ticker: 'AAPL', name: 'Apple Inc', price: 0, change: 0, pct: 0, vol: '—', mktcap: '—', spark: [1, 1, 1, 1, 1, 1, 1, 1] },
]

const INDICES = [
  { name: 'S&P 500', val: '—', pct: 'live', pos: true },
  { name: 'DATA', val: 'FMP/AV', pct: 'quotes', pos: true },
]

function Sparkline({ data, pos }: { data: number[]; pos: boolean }) {
  const w = 72
  const h = 28
  const min = Math.min(...data)
  const max = Math.max(...data)
  const range = max - min || 1
  const pts = data
    .map((v, i) => {
      const x = (i / (data.length - 1)) * w
      const y = h - ((v - min) / range) * h
      return `${x},${y}`
    })
    .join(' ')
  return (
    <svg width={w} height={h} className="overflow-visible">
      <polyline
        points={pts}
        fill="none"
        stroke={pos ? '#00e676' : '#ff4d6a'}
        strokeWidth="1.5"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  )
}

function MiniChart({ stock }: { stock: Stock }) {
  const bars = stock.spark
  const min = Math.min(...bars)
  const max = Math.max(...bars)
  const range = max - min || 1
  return (
    <div className="flex items-end gap-[2px] h-20">
      {bars.map((v, i) => {
        const h = ((v - min) / range) * 60 + 8
        const isLast = i === bars.length - 1
        return (
          <div
            key={i}
            className="w-6 rounded-sm transition-all"
            style={{
              height: h,
              background: isLast
                ? stock.pct >= 0
                  ? '#00e676'
                  : '#ff4d6a'
                : 'rgba(255,255,255,0.1)',
            }}
          />
        )
      })}
    </div>
  )
}

const QUICK = ['Analyze NVDA', 'Should I buy AAPL?', 'Technical analysis for TSLA', 'Compare MSFT vs GOOGL']

export default function App() {
  const {
    connectionStatus,
    connected,
    messages,
    thinking,
    selfDriving,
    recommendation,
    agents,
    engineLabel,
    profile,
    stocks,
    sendQuery,
    updateSelfDriving,
    forceTick,
    saveProfile,
    refreshQuotes,
  } = useStockBackend()

  const [tab, setTab] = useState<Tab>('chat')
  const [addingTicker, setAddingTicker] = useState(false)
  const [tickerInput, setTickerInput] = useState('')
  const [input, setInput] = useState('')
  const [selected, setSelected] = useState<Stock>(FALLBACK_STOCKS[0])
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    if (!stocks.length) return
    setSelected((prev) => stocks.find((s) => s.ticker === prev.ticker) || stocks[0])
  }, [stocks])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function sendMessage() {
    const text = input.trim()
    if (!text || thinking) return
    setInput('')
    sendQuery(text)
  }

  function handleKey(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  function addStock() {
    const t = tickerInput.trim().toUpperCase()
    if (!t) {
      setAddingTicker(false)
      setTickerInput('')
      return
    }
    const current = profile?.watchlist?.length
      ? profile.watchlist
      : stocks.map((s) => s.ticker)
    if (current.includes(t)) {
      setAddingTicker(false)
      setTickerInput('')
      return
    }
    const nextList = [...current, t]
    void saveProfile({ watchlist: nextList }).then(() => refreshQuotes(nextList))
    setTickerInput('')
    setAddingTicker(false)
  }

  function removeStock(ticker: string) {
    const current = profile?.watchlist?.length
      ? profile.watchlist
      : stocks.map((s) => s.ticker)
    const nextList = current.filter((s) => s !== ticker.toUpperCase())
    if (!nextList.length) return
    void saveProfile({ watchlist: nextList }).then(() => refreshQuotes(nextList))
    if (selected.ticker === ticker && nextList[0]) {
      // selected will sync from stocks effect after refresh
    }
  }

  function analyzeSelected() {
    sendQuery(`Give me a comprehensive analysis of ${selected.ticker}`)
    setTab('chat')
  }

  const statusColor =
    connectionStatus === 'connected' ? '#00e676' : connectionStatus === 'connecting' ? '#f5a623' : '#ff4d6a'

  const displayStocks = stocks.length ? stocks : FALLBACK_STOCKS


  return (
    <div className="flex flex-col h-screen" style={{ background: '#07080d', color: '#e8eaf0', fontFamily: "'Inter', sans-serif" }}>
      <header style={{ background: '#0e1018', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center h-11 px-4 gap-6">
          <div className="flex items-center gap-2.5 shrink-0">
            <div
              className="w-6 h-6 rounded flex items-center justify-center"
              style={{ background: 'rgba(0,230,118,0.15)', border: '1px solid rgba(0,230,118,0.3)' }}
            >
              <span className="text-[10px] font-bold mono" style={{ color: '#00e676' }}>
                ◈
              </span>
            </div>
            <span className="text-sm font-semibold tracking-tight">StockAgent</span>
            <span
              className="text-[10px] mono px-1.5 py-0.5 rounded"
              style={{
                background: 'rgba(0,230,118,0.08)',
                color: '#00e676',
                border: '1px solid rgba(0,230,118,0.2)',
              }}
            >
              LANGGRAPH
            </span>
          </div>

          <div className="flex items-center gap-5 flex-1 overflow-x-auto">
            {INDICES.map((idx) => (
              <div key={idx.name} className="flex items-center gap-2 shrink-0">
                <span className="text-[11px] mono" style={{ color: '#3a4155' }}>
                  {idx.name}
                </span>
                <span className="text-[12px] font-medium mono">{idx.val}</span>
                <span className="text-[11px] mono font-medium" style={{ color: idx.pos ? '#00e676' : '#ff4d6a' }}>
                  {idx.pct}
                </span>
              </div>
            ))}
          </div>

          <div className="flex items-center gap-3 shrink-0">
            <button
              type="button"
              onClick={() => setTab('selfdrive')}
              className="text-[10px] mono px-2.5 py-1 rounded flex items-center gap-1.5 transition-all hover:opacity-80"
              style={{
                background: selfDriving?.enabled
                  ? 'rgba(0,212,255,0.12)'
                  : 'rgba(255,255,255,0.04)',
                border: `1px solid ${
                  selfDriving?.enabled ? 'rgba(0,212,255,0.35)' : 'rgba(255,255,255,0.12)'
                }`,
                color: selfDriving?.enabled ? '#00d4ff' : '#8892a4',
              }}
              title="Open Self-Driving controls"
            >
              <span
                className="w-1.5 h-1.5 rounded-full"
                style={{ background: selfDriving?.enabled ? '#00d4ff' : '#5a6175' }}
              />
              SELF-DRIVE · {selfDriving?.enabled ? `ON · ${selfDriving.interval_minutes}m` : 'OFF'}
            </button>
            <span className="w-1.5 h-1.5 rounded-full pulse-dot" style={{ background: statusColor }} />
            <span className="text-[11px] mono" style={{ color: '#5a6175' }}>
              {connectionStatus.toUpperCase()} · {engineLabel}
            </span>
          </div>
        </div>
      </header>

      <div className="flex flex-1 min-h-0">
        <aside
          className="w-[72px] flex flex-col items-center py-4 gap-2 shrink-0"
          style={{ background: '#0e1018', borderRight: '1px solid rgba(255,255,255,0.06)' }}
        >
          {(
            [
              { id: 'chat' as Tab, icon: '⌨', label: 'Chat' },
              { id: 'watchlist' as Tab, icon: '◉', label: 'Watch' },
              { id: 'selfdrive' as Tab, icon: '⟳', label: 'Drive' },
              { id: 'agents' as Tab, icon: '⬡', label: 'Agents' },
              { id: 'profile' as Tab, icon: '👤', label: 'Profile' },
              { id: 'settings' as Tab, icon: '⚙', label: 'Settings' },
            ] as const
          ).map((item) => (
            <button
              key={item.id}
              onClick={() => setTab(item.id)}
              title={item.label}
              className="w-[58px] py-2 rounded-lg flex flex-col items-center justify-center gap-1 transition-all relative"
              style={{
                background: tab === item.id ? 'rgba(0,230,118,0.1)' : 'transparent',
                color: tab === item.id ? '#00e676' : '#5a6175',
                border: `1px solid ${tab === item.id ? 'rgba(0,230,118,0.25)' : 'transparent'}`,
              }}
            >
              <span className="text-base leading-none">{item.icon}</span>
              <span className="text-[9px] mono tracking-wide">{item.label}</span>
              {item.id === 'selfdrive' && selfDriving?.enabled ? (
                <span
                  className="absolute top-1.5 right-1.5 w-1.5 h-1.5 rounded-full"
                  style={{ background: '#00d4ff', boxShadow: '0 0 6px #00d4ff' }}
                />
              ) : null}
            </button>
          ))}
        </aside>

        <div className="flex flex-1 min-w-0 min-h-0">
          {tab === 'chat' && (
            <div className="flex flex-1 min-w-0 min-h-0">
              <div className="flex flex-col flex-1 min-w-0 min-h-0">
                {/* Quick self-drive strip */}
                <div
                  className="px-5 py-2.5 flex items-center gap-3 shrink-0"
                  style={{
                    borderBottom: '1px solid rgba(255,255,255,0.06)',
                    background: 'rgba(0,212,255,0.03)',
                  }}
                >
                  <span className="text-[10px] mono tracking-widest" style={{ color: '#3a4155' }}>
                    SELF-DRIVE
                  </span>
                  <button
                    type="button"
                    disabled={!connected}
                    onClick={() => {
                      void updateSelfDriving({
                        enabled: !selfDriving?.enabled,
                        symbols: selfDriving?.symbols?.length
                          ? selfDriving.symbols
                          : [selected.ticker],
                        interval_minutes: selfDriving?.interval_minutes || 5,
                        analyze_on_tick: selfDriving?.analyze_on_tick ?? true,
                      })
                    }}
                    className="text-[10px] mono px-2.5 py-1 rounded font-semibold disabled:opacity-40"
                    style={{
                      background: selfDriving?.enabled
                        ? 'rgba(0,230,118,0.12)'
                        : 'rgba(255,255,255,0.05)',
                      border: `1px solid ${
                        selfDriving?.enabled ? 'rgba(0,230,118,0.35)' : 'rgba(255,255,255,0.12)'
                      }`,
                      color: selfDriving?.enabled ? '#00e676' : '#8892a4',
                    }}
                  >
                    {selfDriving?.enabled ? 'ON' : 'OFF'}
                  </button>
                  <span className="text-[11px] mono" style={{ color: '#5a6175' }}>
                    {selfDriving?.enabled
                      ? `${(selfDriving.symbols || []).join(', ') || selected.ticker} · every ${selfDriving.interval_minutes}m`
                      : `Flip ON to track ${selected.ticker}`}
                  </span>
                  <button
                    type="button"
                    onClick={() => setTab('selfdrive')}
                    className="ml-auto text-[10px] mono px-2 py-1 rounded"
                    style={{
                      color: '#00d4ff',
                      border: '1px solid rgba(0,212,255,0.25)',
                      background: 'rgba(0,212,255,0.06)',
                    }}
                  >
                    SETTINGS →
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto p-5 space-y-5">
                  {messages.map((m) => (
                    <ChatMsg key={m.id} msg={m} />
                  ))}
                  <div ref={bottomRef} />
                </div>

                {recommendation ? (
                  <div className="px-5 pb-2">
                    <div
                      className="rounded-lg px-3 py-2 text-xs mono flex items-center gap-3"
                      style={{
                        background: 'rgba(0,230,118,0.06)',
                        border: '1px solid rgba(0,230,118,0.2)',
                        color: '#8892a4',
                      }}
                    >
                      <span style={{ color: '#00e676' }}>
                        LAST: {recommendation.recommendation.toUpperCase()}
                      </span>
                      <span>{Math.round(recommendation.confidence * 100)}%</span>
                      {recommendation.verified ? <span style={{ color: '#00d4ff' }}>VERIFIED</span> : null}
                    </div>
                  </div>
                ) : null}

                <div className="px-5 pb-2 flex gap-2 flex-wrap">
                  {QUICK.map((q) => (
                    <button
                      key={q}
                      onClick={() => {
                        setInput(q)
                        inputRef.current?.focus()
                      }}
                      className="text-[11px] mono px-2.5 py-1 rounded transition-all hover:text-[#00e676]"
                      style={{ border: '1px solid rgba(255,255,255,0.08)', color: '#5a6175' }}
                    >
                      {q}
                    </button>
                  ))}
                </div>

                <div className="p-4 pt-2" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                  <div
                    className="flex gap-2 items-end rounded-lg p-3"
                    style={{ background: '#0e1018', border: '1px solid rgba(255,255,255,0.09)' }}
                  >
                    <span className="mono text-[11px] mb-1 shrink-0" style={{ color: '#3a4155' }}>
                      {'>'}
                    </span>
                    <textarea
                      ref={inputRef}
                      rows={1}
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      onKeyDown={handleKey}
                      placeholder={connected ? 'Ask LangGraph to analyze a stock…' : 'Backend offline — start API on :8000'}
                      className="flex-1 resize-none bg-transparent outline-none text-sm leading-relaxed placeholder-[#3a4155] mono"
                      style={{ color: '#d8dce8', fontFamily: "'JetBrains Mono', monospace", minHeight: 22, maxHeight: 120 }}
                    />
                    <button
                      onClick={sendMessage}
                      disabled={!input.trim() || thinking || !connected}
                      className="shrink-0 w-8 h-8 rounded flex items-center justify-center transition-all disabled:opacity-30"
                      style={{
                        background: 'rgba(0,230,118,0.15)',
                        border: '1px solid rgba(0,230,118,0.3)',
                        color: '#00e676',
                      }}
                    >
                      <span className="text-xs">↑</span>
                    </button>
                  </div>
                </div>
              </div>

              <div
                className="w-72 shrink-0 flex flex-col"
                style={{ borderLeft: '1px solid rgba(255,255,255,0.06)', background: '#0a0b10' }}
              >
                <div className="p-4 pb-3" style={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="text-xl font-bold mono">{selected.ticker}</p>
                      <p className="text-xs mt-0.5" style={{ color: '#5a6175' }}>
                        {selected.name}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xl font-bold mono">
                        {selected.price > 0 ? `$${selected.price.toFixed(2)}` : '…'}
                      </p>
                      <p className="text-xs mono font-medium" style={{ color: selected.pct >= 0 ? '#00e676' : '#ff4d6a' }}>
                        {selected.price > 0
                          ? `${selected.pct >= 0 ? '+' : ''}${selected.pct.toFixed(2)}%`
                          : 'loading'}
                      </p>
                    </div>
                  </div>
                  <div className="mt-4">
                    <MiniChart stock={selected} />
                  </div>
                </div>

                <div className="px-4 pb-4 flex gap-2 pt-4">
                  <button
                    onClick={analyzeSelected}
                    disabled={!connected || thinking}
                    className="flex-1 py-2 rounded text-xs mono font-semibold transition-all hover:opacity-80 disabled:opacity-40"
                    style={{
                      background: 'rgba(0,230,118,0.1)',
                      border: '1px solid rgba(0,230,118,0.25)',
                      color: '#00e676',
                    }}
                  >
                    ANALYZE
                  </button>
                  <button
                    onClick={() => {
                      void updateSelfDriving({
                        enabled: true,
                        symbols: [selected.ticker, ...(selfDriving?.symbols || []).filter((s) => s !== selected.ticker)].slice(0, 5),
                        interval_minutes: selfDriving?.interval_minutes || 5,
                        analyze_on_tick: true,
                      })
                      setTab('selfdrive')
                    }}
                    disabled={!connected}
                    className="flex-1 py-2 rounded text-xs mono font-semibold transition-all hover:opacity-80 disabled:opacity-40"
                    style={{
                      background: 'rgba(0,212,255,0.08)',
                      border: '1px solid rgba(0,212,255,0.2)',
                      color: '#00d4ff',
                    }}
                  >
                    TRACK
                  </button>
                </div>

                <div className="flex-1 overflow-y-auto" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                  <div className="flex items-center justify-between px-4 py-2">
                    <span className="text-[10px] mono tracking-widest" style={{ color: '#3a4155' }}>
                      TRACKING
                    </span>
                    <button
                      onClick={() => {
                        setAddingTicker(true)
                        setTickerInput('')
                      }}
                      className="w-5 h-5 rounded text-xs"
                      style={{
                        background: 'rgba(0,230,118,0.12)',
                        border: '1px solid rgba(0,230,118,0.25)',
                        color: '#00e676',
                      }}
                    >
                      +
                    </button>
                  </div>
                  {addingTicker && (
                    <div className="px-4 py-2.5 flex gap-2 items-center">
                      <input
                        autoFocus
                        value={tickerInput}
                        onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') addStock()
                          if (e.key === 'Escape') setAddingTicker(false)
                        }}
                        placeholder="TICKER"
                        maxLength={5}
                        className="flex-1 bg-transparent outline-none mono text-xs"
                        style={{ color: '#00e676' }}
                      />
                      <button onClick={addStock} className="text-[10px] mono" style={{ color: '#00e676' }}>
                        ADD
                      </button>
                    </div>
                  )}
                  {displayStocks.map((s) => (
                    <div
                      key={s.ticker}
                      className="w-full flex items-center gap-2 px-4 py-2.5"
                      style={{
                        background: selected.ticker === s.ticker ? 'rgba(0,230,118,0.04)' : 'transparent',
                        borderLeft: `2px solid ${selected.ticker === s.ticker ? '#00e676' : 'transparent'}`,
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => setSelected(s)}
                        className="flex-1 flex items-center gap-3 text-left min-w-0"
                      >
                        <div className="flex-1 min-w-0">
                          <p className="text-xs mono font-semibold" style={{ color: '#c8ccd8' }}>
                            {s.ticker}
                          </p>
                        </div>
                        <div className="shrink-0 text-right">
                          <p className="text-xs mono" style={{ color: '#8892a4' }}>
                            {s.price > 0 ? `$${s.price.toFixed(2)}` : '…'}
                          </p>
                          <p className="text-[10px] mono" style={{ color: s.pct >= 0 ? '#00e676' : '#ff4d6a' }}>
                            {s.price > 0 ? `${s.pct >= 0 ? '+' : ''}${s.pct.toFixed(2)}%` : ''}
                          </p>
                        </div>
                        <Sparkline data={s.spark} pos={s.pct >= 0} />
                      </button>
                      <button
                        type="button"
                        title="Remove from profile watchlist"
                        onClick={() => removeStock(s.ticker)}
                        className="text-[10px] mono px-1.5 py-1 rounded shrink-0"
                        style={{ color: '#ff4d6a', border: '1px solid rgba(255,77,106,0.25)' }}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {tab === 'watchlist' && (
            <div className="flex-1 overflow-y-auto p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-base font-semibold mono">WATCHLIST</h2>
                <div className="flex gap-2 items-center">
                  <button
                    onClick={() => {
                      void updateSelfDriving({
                        enabled: true,
                        symbols: displayStocks.map((s) => s.ticker).slice(0, 5),
                        interval_minutes: 5,
                        analyze_on_tick: true,
                      })
                      setTab('selfdrive')
                    }}
                    disabled={!connected}
                    className="text-[11px] mono px-3 py-1.5 rounded disabled:opacity-40"
                    style={{
                      background: 'rgba(0,212,255,0.08)',
                      border: '1px solid rgba(0,212,255,0.2)',
                      color: '#00d4ff',
                    }}
                  >
                    TRACK ALL
                  </button>
                  <button
                    onClick={() => {
                      setAddingTicker(true)
                      setTickerInput('')
                    }}
                    className="text-[11px] mono px-3 py-1.5 rounded"
                    style={{
                      background: 'rgba(0,230,118,0.1)',
                      border: '1px solid rgba(0,230,118,0.25)',
                      color: '#00e676',
                    }}
                  >
                    + ADD TICKER
                  </button>
                </div>
              </div>

              {addingTicker && (
                <div className="mb-4 flex gap-2 items-center max-w-md">
                  <input
                    autoFocus
                    value={tickerInput}
                    onChange={(e) => setTickerInput(e.target.value.toUpperCase())}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') addStock()
                      if (e.key === 'Escape') setAddingTicker(false)
                    }}
                    placeholder="TICKER"
                    maxLength={5}
                    className="flex-1 bg-transparent outline-none mono text-sm px-3 py-2 rounded"
                    style={{ color: '#00e676', border: '1px solid rgba(0,230,118,0.3)' }}
                  />
                  <button
                    onClick={addStock}
                    className="text-[11px] mono px-3 py-2 rounded"
                    style={{ color: '#00e676', border: '1px solid rgba(0,230,118,0.25)' }}
                  >
                    ADD
                  </button>
                </div>
              )}

              <div className="rounded-lg overflow-hidden" style={{ border: '1px solid rgba(255,255,255,0.07)' }}>
                {displayStocks.map((s, i) => (
                  <div
                    key={s.ticker}
                    className="grid grid-cols-[1fr_auto_auto_auto_auto] gap-4 px-4 py-3.5 items-center hover:bg-white/[0.02]"
                    style={{ borderBottom: i < displayStocks.length - 1 ? '1px solid rgba(255,255,255,0.04)' : 'none' }}
                  >
                    <button
                      type="button"
                      className="text-left"
                      onClick={() => {
                        setSelected(s)
                        setTab('chat')
                      }}
                    >
                      <p className="text-sm mono font-semibold">{s.ticker}</p>
                      <p className="text-xs" style={{ color: '#5a6175' }}>
                        {s.name}
                      </p>
                    </button>
                    <span className="text-sm mono">{s.price > 0 ? `$${s.price.toFixed(2)}` : '…'}</span>
                    <span className="text-sm mono" style={{ color: s.pct >= 0 ? '#00e676' : '#ff4d6a' }}>
                      {s.price > 0 ? `${s.pct >= 0 ? '+' : ''}${s.pct.toFixed(2)}%` : '—'}
                    </span>
                    <button
                      onClick={() => {
                        sendQuery(`Analyze ${s.ticker}`)
                        setTab('chat')
                      }}
                      className="text-[10px] mono px-2 py-1 rounded"
                      style={{ color: '#00e676', border: '1px solid rgba(0,230,118,0.25)' }}
                    >
                      ANALYZE
                    </button>
                    <button
                      onClick={() => removeStock(s.ticker)}
                      className="text-[10px] mono px-2 py-1 rounded"
                      style={{ color: '#ff4d6a', border: '1px solid rgba(255,77,106,0.25)' }}
                    >
                      REMOVE
                    </button>
                  </div>
                ))}
              </div>
              <p className="text-[11px] mono mt-3" style={{ color: '#3a4155' }}>
                Add/remove updates your profile watchlist automatically.
              </p>
            </div>
          )}

          {tab === 'selfdrive' && (
            <SelfDrivePanel
              status={selfDriving}
              connected={connected}
              onUpdate={updateSelfDriving}
              onForceTick={async () => {
                await forceTick()
              }}
            />
          )}

          {tab === 'profile' && (
            <ProfilePanel
              profile={profile}
              connected={connected}
              onSave={saveProfile}
            />
          )}

          {tab === 'agents' && <AgentsPage agents={agents} />}

          {tab === 'settings' && (
            <div className="flex-1 overflow-y-auto p-6" style={{ color: '#8892a4' }}>
              <h2 className="text-sm font-semibold mono tracking-wider mb-4" style={{ color: '#5a6175' }}>
                BACKEND SETTINGS
              </h2>
              <div
                className="rounded-lg p-5 max-w-lg space-y-3 text-sm"
                style={{ background: '#0e1018', border: '1px solid rgba(255,255,255,0.06)' }}
              >
                <p>
                  Engine: <span className="mono" style={{ color: '#00e676' }}>{engineLabel}</span>
                </p>
                <p>
                  Connection:{' '}
                  <span className="mono" style={{ color: statusColor }}>
                    {connectionStatus}
                  </span>
                </p>
                <p>
                  API: <span className="mono">http://localhost:8000</span>
                </p>
                <p>
                  WebSocket: <span className="mono">ws://localhost:8000/ws</span>
                </p>
                <p className="text-xs" style={{ color: '#5a6175' }}>
                  Start the LangGraph backend with <span className="mono">python start_backend.py</span> from the
                  stock_analysis project.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      <div
        className="flex items-center gap-4 px-4 h-7 text-[10px] mono shrink-0"
        style={{ background: '#0e1018', borderTop: '1px solid rgba(255,255,255,0.06)', color: '#3a4155' }}
      >
        <span className="flex items-center gap-1.5">
          <span className="w-1 h-1 rounded-full" style={{ background: statusColor }} />
          {connected ? 'Backend online' : 'Backend offline'}
        </span>
        <span>|</span>
        <span>Engine: {engineLabel}</span>
        <span>|</span>
        <span>Self-drive: {selfDriving?.enabled ? 'ON' : 'OFF'}</span>
        <div className="flex-1" />
        <span>
          NYSE · {new Date().toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
        </span>
      </div>
    </div>
  )
}
