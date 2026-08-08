import { useEffect, useState } from 'react'
import type { SelfDrivingStatus } from '../types'

type Props = {
  status: SelfDrivingStatus | null
  connected: boolean
  onUpdate: (patch: {
    enabled?: boolean
    symbols?: string[]
    interval_minutes?: number
    analyze_on_tick?: boolean
  }) => Promise<void> | void
  onForceTick: () => Promise<void>
}

function Toggle({ on, onClick }: { on: boolean; onClick: () => void }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className="w-10 h-5 rounded-full relative transition-all"
      style={{
        background: on ? 'rgba(0,230,118,0.3)' : 'rgba(255,255,255,0.08)',
        border: `1px solid ${on ? '#00e676' : 'rgba(255,255,255,0.12)'}`,
      }}
    >
      <span
        className="absolute top-0.5 w-4 h-4 rounded-full transition-all"
        style={{ left: on ? 20 : 2, background: on ? '#00e676' : '#5a6175' }}
      />
    </button>
  )
}

export default function SelfDrivePanel({ status, connected, onUpdate, onForceTick }: Props) {
  const [symbolsText, setSymbolsText] = useState('AAPL, MSFT')
  const [intervalMinutes, setIntervalMinutes] = useState(5)
  const [analyzeOnTick, setAnalyzeOnTick] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!status) return
    setSymbolsText((status.symbols || []).join(', '))
    setIntervalMinutes(status.interval_minutes || 5)
    setAnalyzeOnTick(Boolean(status.analyze_on_tick))
  }, [status])

  const enabled = Boolean(status?.enabled)

  async function run(action: () => Promise<void> | void) {
    setBusy(true)
    setError(null)
    try {
      await action()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  function parseSymbols(): string[] {
    return symbolsText
      .split(/[,\s]+/)
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean)
  }

  return (
    <div className="flex-1 overflow-y-auto p-6" style={{ color: '#8892a4' }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-sm font-semibold mono tracking-wider" style={{ color: '#5a6175' }}>
            SELF-DRIVING LOOP
          </h2>
          <p className="text-xs mt-0.5" style={{ color: '#3a4155' }}>
            Event-driven price tracking via LangGraph backend
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[10px] mono" style={{ color: connected ? '#00e676' : '#ff4d6a' }}>
            {connected ? 'BACKEND ONLINE' : 'BACKEND OFFLINE'}
          </span>
          <Toggle
            on={enabled}
            onClick={() => {
              void run(() => onUpdate({ enabled: !enabled }))
            }}
          />
        </div>
      </div>

      <div
        className="rounded-lg p-5 max-w-xl space-y-4"
        style={{ background: '#0e1018', border: '1px solid rgba(255,255,255,0.06)' }}
      >
        <div>
          <label className="text-[10px] mono tracking-widest block mb-2" style={{ color: '#3a4155' }}>
            SYMBOLS
          </label>
          <input
            value={symbolsText}
            onChange={(e) => setSymbolsText(e.target.value.toUpperCase())}
            placeholder="AAPL, MSFT, NVDA"
            className="w-full bg-transparent outline-none mono text-sm px-3 py-2 rounded"
            style={{
              color: '#e8eaf0',
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(255,255,255,0.02)',
            }}
          />
        </div>

        <div>
          <label className="text-[10px] mono tracking-widest block mb-2" style={{ color: '#3a4155' }}>
            INTERVAL (MINUTES)
          </label>
          <input
            type="number"
            min={1}
            max={1440}
            value={intervalMinutes}
            onChange={(e) => setIntervalMinutes(Number(e.target.value))}
            className="w-full bg-transparent outline-none mono text-sm px-3 py-2 rounded"
            style={{
              color: '#e8eaf0',
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(255,255,255,0.02)',
            }}
          />
        </div>

        <div className="flex items-center justify-between">
          <span className="text-sm">Run LangGraph analysis on each tick</span>
          <Toggle on={analyzeOnTick} onClick={() => setAnalyzeOnTick((v) => !v)} />
        </div>

        <div className="flex gap-2 pt-2">
          <button
            type="button"
            disabled={busy || !connected}
            onClick={() =>
              void run(() =>
                onUpdate({
                  symbols: parseSymbols(),
                  interval_minutes: Math.max(1, intervalMinutes || 5),
                  analyze_on_tick: analyzeOnTick,
                }),
              )
            }
            className="flex-1 py-2.5 rounded text-[11px] mono font-semibold transition-all hover:opacity-80 disabled:opacity-40"
            style={{
              background: 'rgba(0,230,118,0.1)',
              border: '1px solid rgba(0,230,118,0.25)',
              color: '#00e676',
            }}
          >
            SAVE SETTINGS
          </button>
          <button
            type="button"
            disabled={busy || !connected}
            onClick={() => void run(() => onForceTick())}
            className="px-4 py-2.5 rounded text-[11px] mono font-semibold transition-all hover:opacity-80 disabled:opacity-40"
            style={{
              background: 'rgba(0,212,255,0.08)',
              border: '1px solid rgba(0,212,255,0.2)',
              color: '#00d4ff',
            }}
          >
            TICK NOW
          </button>
        </div>

        {error ? (
          <p className="text-xs mono" style={{ color: '#ff4d6a' }}>
            {error}
          </p>
        ) : null}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6 max-w-3xl">
        {[
          { label: 'STATUS', val: enabled ? (status?.running ? 'RUNNING' : 'ENABLED') : 'OFF', color: enabled ? '#00e676' : '#5a6175' },
          { label: 'TICKS', val: String(status?.tick_count ?? 0), color: '#00d4ff' },
          { label: 'LAST TICK', val: status?.last_tick_at ? new Date(status.last_tick_at).toLocaleTimeString() : '—', color: '#8892a4' },
          { label: 'NEXT TICK', val: status?.next_tick_at ? new Date(status.next_tick_at).toLocaleTimeString() : '—', color: '#8892a4' },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-lg p-4"
            style={{ background: '#0e1018', border: '1px solid rgba(255,255,255,0.06)' }}
          >
            <p className="text-[10px] mono tracking-widest mb-1" style={{ color: '#3a4155' }}>
              {s.label}
            </p>
            <p className="text-sm font-bold mono" style={{ color: s.color }}>
              {s.val}
            </p>
          </div>
        ))}
      </div>

      {status?.last_error ? (
        <p className="mt-4 text-xs mono" style={{ color: '#ff4d6a' }}>
          Last error: {status.last_error}
        </p>
      ) : null}

      {status?.last_prices && Object.keys(status.last_prices).length > 0 ? (
        <div className="mt-6 max-w-3xl">
          <p className="text-[10px] mono tracking-widest mb-3" style={{ color: '#3a4155' }}>
            LAST PRICES
          </p>
          <div className="space-y-2">
            {Object.entries(status.last_prices).map(([symbol, raw]) => {
              let price = '—'
              try {
                const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
                const obj = parsed as { price?: number }
                if (typeof obj?.price === 'number') price = `$${obj.price.toFixed(2)}`
              } catch {
                price = String(raw).slice(0, 40)
              }
              return (
                <div
                  key={symbol}
                  className="flex items-center justify-between px-4 py-3 rounded"
                  style={{ background: '#0e1018', border: '1px solid rgba(255,255,255,0.06)' }}
                >
                  <span className="mono text-sm font-semibold" style={{ color: '#e8eaf0' }}>
                    {symbol}
                  </span>
                  <span className="mono text-sm" style={{ color: '#00e676' }}>
                    {price}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      ) : null}
    </div>
  )
}
