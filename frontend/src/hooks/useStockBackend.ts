import { useCallback, useEffect, useMemo, useState } from 'react'
import { useI18n } from '../i18n'
import { backend } from '../services/backend'
import type {
  AgentDef,
  ConnectionStatus,
  FinalRecommendation,
  Msg,
  SelfDrivingStatus,
  Stock,
  UserProfile,
} from '../types'

let msgId = 0

function nowTs() {
  return new Date().toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

const BASE_AGENTS: AgentDef[] = [
  {
    id: 'orchestrator',
    name: 'Orchestrator',
    role: 'Routes work and synthesizes the final call',
    model: 'deepseek-chat',
    status: 'idle',
    tasksTotal: 0,
    tasksDone: 0,
    lastAction: 'Waiting for query',
    latency: 0,
    tokens: 0,
    uptime: 'session',
    log: ['Ready'],
  },
  {
    id: 'market_data',
    name: 'Market Data',
    role: 'Live quotes, volume, and price history',
    model: 'fmp/alpha-vantage',
    status: 'idle',
    tasksTotal: 0,
    tasksDone: 0,
    lastAction: 'Idle',
    latency: 0,
    tokens: 0,
    uptime: 'session',
    log: ['Ready'],
  },
  {
    id: 'fundamentals',
    name: 'Fundamentals',
    role: 'Valuation, margins, and financial health',
    model: 'fmp/alpha-vantage',
    status: 'idle',
    tasksTotal: 0,
    tasksDone: 0,
    lastAction: 'Idle',
    latency: 0,
    tokens: 0,
    uptime: 'session',
    log: ['Ready'],
  },
  {
    id: 'technical',
    name: 'Technical',
    role: 'SMA/EMA/RSI and trend structure',
    model: 'derived',
    status: 'idle',
    tasksTotal: 0,
    tasksDone: 0,
    lastAction: 'Idle',
    latency: 0,
    tokens: 0,
    uptime: 'session',
    log: ['Ready'],
  },
  {
    id: 'sentiment',
    name: 'Sentiment',
    role: 'News tone and catalyst awareness',
    model: 'deepseek-chat',
    status: 'idle',
    tasksTotal: 0,
    tasksDone: 0,
    lastAction: 'Idle',
    latency: 0,
    tokens: 0,
    uptime: 'session',
    log: ['Ready'],
  },
  {
    id: 'risk',
    name: 'Risk',
    role: 'Drawdown, sizing, and downside checks',
    model: 'deepseek-chat',
    status: 'idle',
    tasksTotal: 0,
    tasksDone: 0,
    lastAction: 'Idle',
    latency: 0,
    tokens: 0,
    uptime: 'session',
    log: ['Ready'],
  },
  {
    id: 'verifier',
    name: 'Verifier',
    role: 'Rubric check before finalizing',
    model: 'deepseek-chat',
    status: 'idle',
    tasksTotal: 0,
    tasksDone: 0,
    lastAction: 'Idle',
    latency: 0,
    tokens: 0,
    uptime: 'session',
    log: ['Ready'],
  },
  {
    id: 'self_driving',
    name: 'Self-Driving',
    role: 'Interval price tracking loop',
    model: 'event-loop',
    status: 'idle',
    tasksTotal: 0,
    tasksDone: 0,
    lastAction: 'Disabled',
    latency: 0,
    tokens: 0,
    uptime: 'session',
    log: ['Waiting for enable'],
  },
]

const KNOWN_AGENTS = new Set(BASE_AGENTS.map((a) => a.id))

function quoteToStock(q: {
  ticker?: string
  symbol?: string
  name?: string
  price?: number
  change?: number
  pct?: number
  change_percent?: number
  vol?: string
  mktcap?: string
}): Stock {
  const ticker = String(q.ticker || q.symbol || '').toUpperCase()
  const price = Number(q.price || 0)
  const pct = Number(q.pct ?? q.change_percent ?? 0)
  const change = Number(q.change ?? (price * pct) / 100)
  const sparkBase = price || 100
  return {
    ticker,
    name: q.name || `${ticker}`,
    price,
    change,
    pct,
    vol: q.vol || '—',
    mktcap: q.mktcap || '—',
    spark: Array.from({ length: 8 }, (_, i) =>
      Number((sparkBase * (0.96 + i * 0.008 + ((i % 3) - 1) * 0.004)).toFixed(2)),
    ),
  }
}

export function useStockBackend() {
  const { t, locale } = useI18n()
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('disconnected')
  const [messages, setMessages] = useState<Msg[]>([
    {
      id: ++msgId,
      role: 'agent',
      text: t.chat.welcome,
      ts: nowTs(),
    },
  ])
  const [thinking, setThinking] = useState(false)

  useEffect(() => {
    setMessages((prev) => {
      if (prev.length !== 1 || prev[0].role !== 'agent' || prev[0].thinking) return prev
      return [{ ...prev[0], text: t.chat.welcome }]
    })
  }, [locale, t.chat.welcome])
  const [selfDriving, setSelfDriving] = useState<SelfDrivingStatus | null>(null)
  const [recommendation, setRecommendation] = useState<FinalRecommendation | null>(null)
  const [agents, setAgents] = useState<AgentDef[]>(BASE_AGENTS)
  const [engineLabel, setEngineLabel] = useState('langgraph')
  const [profile, setProfile] = useState<UserProfile | null>(null)
  const [stocks, setStocks] = useState<Stock[]>([])

  const patchAgent = useCallback((id: string, patch: Partial<AgentDef> & { appendLog?: string }) => {
    const agentId = KNOWN_AGENTS.has(id) ? id : 'orchestrator'
    setAgents((prev) =>
      prev.map((a) => {
        if (a.id !== agentId) return a
        const next = { ...a, ...patch }
        const logLine = patch.appendLog || patch.lastAction
        if (logLine) {
          next.log = [`${nowTs()} → ${logLine}`, ...a.log].slice(0, 20)
        }
        return next
      }),
    )
  }, [])

  const refreshQuotes = useCallback(async (symbols?: string[]) => {
    const data = await backend.fetchQuotes(symbols)
    const next = (data.items || []).map(quoteToStock).filter((s) => s.ticker)
    if (next.length) setStocks(next)
    return next
  }, [])

  const loadProfile = useCallback(async () => {
    const p = await backend.fetchProfile()
    setProfile(p)
    if (p.chat_history?.length) {
      const restored: Msg[] = p.chat_history
        .map((m, idx) => ({
          id: idx + 1,
          role: (m.role as Msg['role']) || 'agent',
          text: String(m.text || ''),
          ts: String(m.ts || nowTs()),
        }))
        .filter((m) => m.text)
      if (restored.length) {
        msgId = restored.length
        setMessages(restored)
      }
    }
    await refreshQuotes(p.watchlist)
    return p
  }, [refreshQuotes])

  // Keep the socket lifecycle independent of self-driving / profile state.
  // Including selfDriving in deps was reconnecting on every status update.
  useEffect(() => {
    backend.connect()
    return () => {
      backend.disconnect()
    }
  }, [])

  useEffect(() => {
    const offStatus = backend.onStatus(setConnectionStatus)

    const offAny = backend.onAny((message) => {
      const type = message.type
      const data = message.data || {}

      if (type === 'connection_established') {
        if (data.self_driving) setSelfDriving(data.self_driving as SelfDrivingStatus)
        if (typeof data.engine === 'string') setEngineLabel(data.engine)
        patchAgent('orchestrator', {
          lastAction: message.message || 'Backend connected',
          status: 'idle',
        })
      }

      if (type === 'self_driving_status' && message.data) {
        const status = message.data as unknown as SelfDrivingStatus
        setSelfDriving(status)
        patchAgent('self_driving', {
          status: status.enabled ? (status.running ? 'running' : 'paused') : 'idle',
          lastAction: status.enabled
            ? `Tracking ${status.symbols.join(', ')} every ${status.interval_minutes}m`
            : 'Disabled',
          tasksDone: status.tick_count,
          tasksTotal: Math.max(status.tick_count, 1),
        })
      }

      if (type === 'self_driving_tick') {
        patchAgent('self_driving', {
          status: 'running',
          lastAction: message.message || 'Tick received',
          tasksDone: Number((data.tick_count as number) || 0),
        })
        void refreshQuotes(selfDriving?.symbols)
      }

      if (type === 'query_started' || type === 'status_update' || type === 'query_analysis') {
        patchAgent('orchestrator', {
          status: 'processing',
          lastAction: message.message || String(data.message || 'Query started'),
        })
      }

      if (type === 'agent_status') {
        const name = String(data.agent_name || 'orchestrator')
        const status = String(data.status || 'processing')
        const detail = String(data.message || data.error || status)
        patchAgent(name, {
          status:
            status === 'completed'
              ? 'completed'
              : status === 'error'
                ? 'error'
                : status === 'idle'
                  ? 'idle'
                  : status === 'paused'
                    ? 'paused'
                    : 'processing',
          lastAction: detail,
          appendLog: data.error ? `ERROR: ${data.error}` : detail,
          tasksDone: status === 'completed' ? 1 : 0,
          tasksTotal: 1,
        })
      }

      if (type === 'final_recommendation' && message.data) {
        const rec = message.data as unknown as FinalRecommendation
        setRecommendation(rec)
        setThinking(false)
        const mocked = Boolean(rec.mocked)
        const agentMsg: Msg = {
          id: ++msgId,
          role: 'agent',
          text: [
            mocked ? '**[MOCK]** Fallback / mock result' : null,
            `**Recommendation:** ${String(rec.recommendation || 'hold').toUpperCase()}`,
            `**Confidence:** ${Math.round(Number(rec.confidence || 0) * 100)}%`,
            '',
            rec.rationale || '',
            rec.riskAssessment ? `\n**Risk:** ${rec.riskAssessment}` : '',
            mocked && rec.mock_reason ? `\n**Mock reason:** ${rec.mock_reason}` : '',
          ]
            .filter(Boolean)
            .join('\n'),
          ts: nowTs(),
        }
        setMessages((prev) => {
          const withoutThinking = prev.filter((m) => !m.thinking)
          return [...withoutThinking, agentMsg]
        })
        void backend.appendChat([
          {
            role: agentMsg.role,
            text: agentMsg.text,
            ts: agentMsg.ts,
          },
        ]).catch(() => undefined)
        patchAgent('orchestrator', {
          status: mocked ? 'error' : 'completed',
          lastAction: mocked
            ? `[MOCK] Recommendation: ${rec.recommendation}`
            : `Recommendation: ${rec.recommendation}`,
          tasksDone: 1,
          tasksTotal: 1,
        })
        patchAgent('verifier', {
          status: rec.verified ? 'completed' : 'idle',
          lastAction: rec.verified
            ? 'Passed verification'
            : mocked
              ? '[MOCK] Verification skipped/failed'
              : 'Finalized without pass',
        })
      }

      if (type === 'query_completed') {
        setThinking(false)
        setMessages((prev) => prev.filter((m) => !m.thinking))
      }

      if (type === 'error') {
        setThinking(false)
        setMessages((prev) => prev.filter((m) => !m.thinking))
        patchAgent('orchestrator', {
          status: 'error',
          lastAction: message.message || 'Backend error',
          appendLog: `ERROR: ${message.message || 'Backend error'}`,
        })
      }
    })

    void backend
      .fetchStatus()
      .then((status) => {
        if (typeof status.engine === 'string') setEngineLabel(status.engine)
        if (status.self_driving) setSelfDriving(status.self_driving as SelfDrivingStatus)
      })
      .catch(() => {
        patchAgent('orchestrator', { status: 'error', lastAction: 'Backend offline at boot' })
      })

    void loadProfile().catch(() => undefined)

    const timer = window.setInterval(() => {
      void refreshQuotes().catch(() => undefined)
    }, 60_000)

    return () => {
      offStatus()
      offAny()
      window.clearInterval(timer)
    }
  }, [loadProfile, patchAgent, refreshQuotes])

  const sendQuery = useCallback(
    (query: string) => {
      const text = query.trim()
      if (!text) return
      setRecommendation(null)
      const userMsg: Msg = { id: ++msgId, role: 'user', text, ts: nowTs() }
      setMessages((prev) => [
        ...prev,
        userMsg,
        { id: ++msgId, role: 'agent', text: '', ts: nowTs(), thinking: true },
      ])
      void backend.appendChat([{ role: 'user', text, ts: userMsg.ts }]).catch(() => undefined)
      setThinking(true)
      patchAgent('orchestrator', {
        status: 'processing',
        lastAction: `Analyzing: ${text}`,
        tasksTotal: 1,
        tasksDone: 0,
      })
      try {
        backend.sendQuery(text)
      } catch (err) {
        setThinking(false)
        setMessages((prev) => prev.filter((m) => !m.thinking))
        patchAgent('orchestrator', {
          status: 'error',
          lastAction: err instanceof Error ? err.message : String(err),
          appendLog: `ERROR: ${err instanceof Error ? err.message : String(err)}`,
        })
      }
    },
    [patchAgent],
  )

  const updateSelfDriving = useCallback(
    async (patch: {
      enabled?: boolean
      symbols?: string[]
      interval_minutes?: number
      analyze_on_tick?: boolean
    }) => {
      try {
        backend.updateSelfDriving(patch)
      } catch {
        const status = await backend.postSelfDriving(patch)
        setSelfDriving(status)
      }
    },
    [],
  )

  const forceTick = useCallback(async () => {
    patchAgent('self_driving', { status: 'processing', lastAction: 'Forced tick requested' })
    const result = await backend.forceTick()
    await refreshQuotes()
    return result
  }, [patchAgent, refreshQuotes])

  const saveProfile = useCallback(
    async (patch: {
      display_name?: string
      watchlist?: string[]
      agent_strategies?: Record<string, string>
    }) => {
      const saved = await backend.saveProfile(patch)
      setProfile(saved)
      if (patch.watchlist) await refreshQuotes(patch.watchlist)
    },
    [refreshQuotes],
  )

  const connected = connectionStatus === 'connected'

  return useMemo(
    () => ({
      connectionStatus,
      connected,
      apiUrl: backend.apiBase,
      wsUrl: backend.websocketUrl,
      messages,
      thinking,
      selfDriving,
      recommendation,
      agents,
      engineLabel,
      profile,
      stocks,
      setStocks,
      sendQuery,
      updateSelfDriving,
      forceTick,
      saveProfile,
      refreshQuotes,
      loadProfile,
      setMessages,
    }),
    [
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
      loadProfile,
    ],
  )
}
