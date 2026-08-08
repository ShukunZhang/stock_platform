export type ConnectionStatus = 'connected' | 'disconnected' | 'connecting'

export type Msg = {
  id: number
  role: 'user' | 'agent' | 'system'
  text: string
  ts: string
  thinking?: boolean
}

export type Stock = {
  ticker: string
  name: string
  price: number
  change: number
  pct: number
  vol: string
  mktcap: string
  spark: number[]
}

export type Tab = 'chat' | 'watchlist' | 'agents' | 'settings' | 'selfdrive' | 'profile'

export type AgentStatus = 'running' | 'idle' | 'error' | 'paused' | 'processing' | 'completed'

export type AgentDef = {
  id: string
  name: string
  role: string
  model: string
  status: AgentStatus
  tasksTotal: number
  tasksDone: number
  lastAction: string
  latency: number
  tokens: number
  uptime: string
  log: string[]
}

export type UserProfile = {
  user_id: string
  display_name: string
  watchlist: string[]
  chat_history: Array<Record<string, unknown>>
  agent_strategies: Record<string, string>
  created_at?: string
  updated_at?: string
}

export type QuoteItem = {
  ticker: string
  symbol?: string
  name?: string
  price: number
  change?: number
  pct?: number
  change_percent?: number
  vol?: string
  mktcap?: string
  mock?: boolean
  provider?: string
}

export type SelfDrivingStatus = {
  enabled: boolean
  symbols: string[]
  interval_minutes: number
  analyze_on_tick: boolean
  running: boolean
  last_tick_at: string | null
  next_tick_at: string | null
  last_prices: Record<string, unknown>
  tick_count: number
  last_error: string | null
}

export type FinalRecommendation = {
  recommendation: 'buy' | 'sell' | 'hold'
  confidence: number
  rationale: string
  keyFactors?: string[]
  riskAssessment?: string
  symbols?: string[]
  verified?: boolean
  mode?: string
  mocked?: boolean
  mock_tag?: string | null
  mock_reason?: string
}

export type BackendMessage = {
  type: string
  data?: Record<string, unknown>
  message?: string
  timestamp?: string
}
