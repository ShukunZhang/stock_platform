import type { BackendMessage, ConnectionStatus, SelfDrivingStatus } from '../types'

const DEFAULT_WS = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'
const DEFAULT_API = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/** Keepalive under Render/Cloudflare idle proxies (often ~55–100s). */
const CLIENT_PING_MS = 25_000

type MessageHandler = (message: BackendMessage) => void
type StatusHandler = (status: ConnectionStatus) => void

export class BackendClient {
  private ws: WebSocket | null = null
  private handlers = new Map<string, Set<MessageHandler>>()
  private anyHandlers = new Set<MessageHandler>()
  private statusHandlers = new Set<StatusHandler>()
  private reconnectAttempts = 0
  private shouldReconnect = true
  private reconnectTimer: number | null = null
  private pingTimer: number | null = null
  private generation = 0

  constructor(
    private wsUrl: string = DEFAULT_WS,
    private apiUrl: string = DEFAULT_API,
  ) {}

  get apiBase(): string {
    return this.apiUrl
  }

  get websocketUrl(): string {
    return this.wsUrl
  }

  connect(): void {
    this.shouldReconnect = true
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return
    }

    this.clearReconnectTimer()
    this.stopPing()

    const generation = ++this.generation
    this.emitStatus('connecting')
    const ws = new WebSocket(this.wsUrl)
    this.ws = ws

    ws.onopen = () => {
      if (generation !== this.generation || this.ws !== ws) return
      this.reconnectAttempts = 0
      this.emitStatus('connected')
      this.startPing()
      this.requestSelfDrivingStatus()
    }

    ws.onmessage = (event) => {
      if (generation !== this.generation || this.ws !== ws) return
      try {
        const message = JSON.parse(event.data as string) as BackendMessage
        if (message.type === 'ping') {
          this.sendQuiet({ type: 'pong' })
          return
        }
        if (message.type === 'pong') return
        this.dispatch(message)
      } catch {
        // ignore malformed frames
      }
    }

    ws.onerror = () => {
      // Wait for onclose to update status / reconnect — onerror alone is noisy.
    }

    ws.onclose = () => {
      if (generation !== this.generation) return
      if (this.ws === ws) this.ws = null
      this.stopPing()
      this.emitStatus('disconnected')
      if (!this.shouldReconnect) return
      const delay = Math.min(10_000, 1000 * 2 ** this.reconnectAttempts)
      this.reconnectAttempts += 1
      this.clearReconnectTimer()
      this.reconnectTimer = window.setTimeout(() => {
        this.reconnectTimer = null
        this.connect()
      }, delay)
    }
  }

  disconnect(): void {
    this.shouldReconnect = false
    this.generation += 1
    this.clearReconnectTimer()
    this.stopPing()
    const ws = this.ws
    this.ws = null
    if (ws && ws.readyState < WebSocket.CLOSING) {
      ws.close()
    }
    this.emitStatus('disconnected')
  }

  on(type: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(type)) this.handlers.set(type, new Set())
    this.handlers.get(type)!.add(handler)
    return () => this.handlers.get(type)?.delete(handler)
  }

  onAny(handler: MessageHandler): () => void {
    this.anyHandlers.add(handler)
    return () => this.anyHandlers.delete(handler)
  }

  onStatus(handler: StatusHandler): () => void {
    this.statusHandlers.add(handler)
    return () => this.statusHandlers.delete(handler)
  }

  send(payload: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not connected')
    }
    this.ws.send(JSON.stringify({ ...payload, timestamp: new Date().toISOString() }))
  }

  sendQuery(query: string): void {
    this.send({ type: 'stock_query', content: query })
  }

  updateSelfDriving(data: {
    enabled?: boolean
    symbols?: string[]
    interval_minutes?: number
    analyze_on_tick?: boolean
  }): void {
    this.send({ type: 'self_driving_update', data })
  }

  requestSelfDrivingStatus(): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return
    this.sendQuiet({ type: 'self_driving_status' })
  }

  requestPortfolio(): void {
    this.send({ type: 'portfolio_request' })
  }

  async fetchStatus(): Promise<Record<string, unknown>> {
    const res = await fetch(`${this.apiUrl}/api/status`)
    if (!res.ok) throw new Error(`Status failed: ${res.status}`)
    return res.json()
  }

  async fetchSelfDriving(): Promise<SelfDrivingStatus> {
    const res = await fetch(`${this.apiUrl}/api/self-driving`)
    if (!res.ok) throw new Error(`Self-driving status failed: ${res.status}`)
    return res.json()
  }

  async postSelfDriving(body: {
    enabled?: boolean
    symbols?: string[]
    interval_minutes?: number
    analyze_on_tick?: boolean
  }): Promise<SelfDrivingStatus> {
    const res = await fetch(`${this.apiUrl}/api/self-driving`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) throw new Error(`Self-driving update failed: ${res.status}`)
    return res.json()
  }

  async forceTick(): Promise<Record<string, unknown>> {
    const res = await fetch(`${this.apiUrl}/api/self-driving/tick`, { method: 'POST' })
    if (!res.ok) throw new Error(`Force tick failed: ${res.status}`)
    return res.json()
  }

  async fetchProfile(userId = 'default'): Promise<import('../types').UserProfile> {
    const res = await fetch(`${this.apiUrl}/api/profile?user_id=${encodeURIComponent(userId)}`)
    if (!res.ok) throw new Error(`Profile failed: ${res.status}`)
    return res.json()
  }

  async saveProfile(
    patch: {
      display_name?: string
      watchlist?: string[]
      chat_history?: Array<Record<string, unknown>>
      agent_strategies?: Record<string, string>
    },
    userId = 'default',
  ): Promise<import('../types').UserProfile> {
    const res = await fetch(`${this.apiUrl}/api/profile?user_id=${encodeURIComponent(userId)}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(patch),
    })
    if (!res.ok) throw new Error(`Save profile failed: ${res.status}`)
    return res.json()
  }

  async appendChat(messages: Array<Record<string, unknown>>, userId = 'default') {
    const res = await fetch(`${this.apiUrl}/api/profile/chat?user_id=${encodeURIComponent(userId)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages }),
    })
    if (!res.ok) throw new Error(`Append chat failed: ${res.status}`)
    return res.json()
  }

  async fetchQuotes(symbols?: string[]): Promise<{
    items: import('../types').QuoteItem[]
    quotes: Record<string, import('../types').QuoteItem>
  }> {
    const qs = symbols?.length ? `?symbols=${encodeURIComponent(symbols.join(','))}` : ''
    const res = await fetch(`${this.apiUrl}/api/quotes${qs}`)
    if (!res.ok) throw new Error(`Quotes failed: ${res.status}`)
    return res.json()
  }

  private sendQuiet(payload: Record<string, unknown>): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) return
    this.ws.send(JSON.stringify({ ...payload, timestamp: new Date().toISOString() }))
  }

  private startPing(): void {
    this.stopPing()
    this.pingTimer = window.setInterval(() => {
      this.sendQuiet({ type: 'ping' })
    }, CLIENT_PING_MS)
  }

  private stopPing(): void {
    if (this.pingTimer !== null) {
      window.clearInterval(this.pingTimer)
      this.pingTimer = null
    }
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }

  private dispatch(message: BackendMessage): void {
    this.anyHandlers.forEach((h) => h(message))
    const set = this.handlers.get(message.type)
    set?.forEach((h) => h(message))
  }

  private emitStatus(status: ConnectionStatus): void {
    this.statusHandlers.forEach((h) => h(status))
  }
}

export const backend = new BackendClient()
