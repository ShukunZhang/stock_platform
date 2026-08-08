import { useEffect, useState } from 'react'
import type { UserProfile } from '../types'

type Props = {
  profile: UserProfile | null
  connected: boolean
  onSave: (patch: {
    display_name?: string
    watchlist?: string[]
    agent_strategies?: Record<string, string>
  }) => Promise<void>
}

const STRATEGY_LABELS: Record<string, string> = {
  orchestrator: 'Orchestrator',
  market_data: 'Market Data',
  fundamentals: 'Fundamentals',
  technical: 'Technical',
  sentiment: 'Sentiment',
  risk: 'Risk',
  verifier: 'Verifier',
}

export default function ProfilePanel({ profile, connected, onSave }: Props) {
  const [displayName, setDisplayName] = useState('Trader')
  const [watchlistText, setWatchlistText] = useState('AAPL, MSFT, NVDA')
  const [strategies, setStrategies] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    if (!profile) return
    setDisplayName(profile.display_name || 'Trader')
    setWatchlistText((profile.watchlist || []).join(', '))
    setStrategies({ ...(profile.agent_strategies || {}) })
  }, [profile])

  async function save() {
    setBusy(true)
    setMsg(null)
    try {
      const watchlist = watchlistText
        .split(/[,\s]+/)
        .map((s) => s.trim().toUpperCase())
        .filter(Boolean)
      await onSave({
        display_name: displayName,
        watchlist,
        agent_strategies: strategies,
      })
      setMsg('Profile saved')
    } catch (err) {
      setMsg(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto p-6" style={{ color: '#8892a4' }}>
      <div className="mb-6">
        <h2 className="text-sm font-semibold mono tracking-wider" style={{ color: '#5a6175' }}>
          USER PROFILE
        </h2>
        <p className="text-xs mt-0.5" style={{ color: '#3a4155' }}>
          Chat history, watchlist, and per-agent strategies
        </p>
      </div>

      <div
        className="rounded-lg p-5 max-w-2xl space-y-4"
        style={{ background: '#0e1018', border: '1px solid rgba(255,255,255,0.06)' }}
      >
        <div>
          <label className="text-[10px] mono tracking-widest block mb-2" style={{ color: '#3a4155' }}>
            DISPLAY NAME
          </label>
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="w-full bg-transparent outline-none mono text-sm px-3 py-2 rounded"
            style={{ color: '#e8eaf0', border: '1px solid rgba(255,255,255,0.1)' }}
          />
        </div>

        <div>
          <label className="text-[10px] mono tracking-widest block mb-2" style={{ color: '#3a4155' }}>
            WATCHLIST
          </label>
          <input
            value={watchlistText}
            onChange={(e) => setWatchlistText(e.target.value.toUpperCase())}
            placeholder="AAPL, MSFT, NVDA"
            className="w-full bg-transparent outline-none mono text-sm px-3 py-2 rounded"
            style={{ color: '#e8eaf0', border: '1px solid rgba(255,255,255,0.1)' }}
          />
        </div>

        <div>
          <p className="text-[10px] mono tracking-widest mb-3" style={{ color: '#3a4155' }}>
            AGENT STRATEGIES
          </p>
          <div className="space-y-3">
            {Object.keys(STRATEGY_LABELS).map((key) => (
              <div key={key}>
                <label className="text-xs mono block mb-1" style={{ color: '#8892a4' }}>
                  {STRATEGY_LABELS[key]}
                </label>
                <textarea
                  rows={2}
                  value={strategies[key] || ''}
                  onChange={(e) => setStrategies((prev) => ({ ...prev, [key]: e.target.value }))}
                  className="w-full bg-transparent outline-none text-xs px-3 py-2 rounded resize-y"
                  style={{
                    color: '#d8dce8',
                    border: '1px solid rgba(255,255,255,0.1)',
                    fontFamily: "'JetBrains Mono', monospace",
                  }}
                />
              </div>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            type="button"
            disabled={busy || !connected}
            onClick={() => void save()}
            className="px-4 py-2 rounded text-[11px] mono font-semibold disabled:opacity-40"
            style={{
              background: 'rgba(0,230,118,0.1)',
              border: '1px solid rgba(0,230,118,0.25)',
              color: '#00e676',
            }}
          >
            SAVE PROFILE
          </button>
          <span className="text-[11px] mono" style={{ color: '#5a6175' }}>
            Chat messages: {profile?.chat_history?.length ?? 0}
          </span>
          {msg ? (
            <span className="text-[11px] mono" style={{ color: msg === 'Profile saved' ? '#00e676' : '#ff4d6a' }}>
              {msg}
            </span>
          ) : null}
        </div>
      </div>
    </div>
  )
}
