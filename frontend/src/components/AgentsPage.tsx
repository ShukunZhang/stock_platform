import { useState } from 'react'
import type { AgentDef, AgentStatus } from '../types'

const STATUS_COLOR: Record<AgentStatus, string> = {
  running: '#00e676',
  idle: '#5a6175',
  error: '#ff4d6a',
  paused: '#f5a623',
  processing: '#00d4ff',
  completed: '#00e676',
}

const STATUS_BG: Record<AgentStatus, string> = {
  running: 'rgba(0,230,118,0.1)',
  idle: 'rgba(90,97,117,0.12)',
  error: 'rgba(255,77,106,0.1)',
  paused: 'rgba(245,166,35,0.1)',
  processing: 'rgba(0,212,255,0.1)',
  completed: 'rgba(0,230,118,0.1)',
}

export default function AgentsPage({ agents }: { agents: AgentDef[] }) {
  const [expanded, setExpanded] = useState<string | null>(null)
  const running = agents.filter((a) => a.status === 'running' || a.status === 'processing').length
  const errors = agents.filter((a) => a.status === 'error').length

  return (
    <div className="flex-1 overflow-y-auto p-6" style={{ color: '#8892a4' }}>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-sm font-semibold mono tracking-wider" style={{ color: '#5a6175' }}>
            AGENT FLEET
          </h2>
          <p className="text-xs mt-0.5" style={{ color: '#3a4155' }}>
            Specialist boxes · click a card for activity log
          </p>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'TOTAL', val: agents.length, color: '#8892a4' },
          { label: 'ACTIVE', val: running, color: '#00e676' },
          { label: 'ERRORS', val: errors, color: errors > 0 ? '#ff4d6a' : '#5a6175' },
          { label: 'ENGINE', val: 'LG', color: '#00d4ff' },
        ].map((s) => (
          <div
            key={s.label}
            className="rounded-lg p-4"
            style={{ background: '#0e1018', border: '1px solid rgba(255,255,255,0.06)' }}
          >
            <p className="text-[10px] mono tracking-widest mb-1" style={{ color: '#3a4155' }}>
              {s.label}
            </p>
            <p className="text-xl font-bold mono" style={{ color: s.color }}>
              {s.val}
            </p>
          </div>
        ))}
      </div>

      {/* Responsive agent boxes: 1 → 2 → 3 columns */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
        {agents.map((agent) => {
          const pct =
            agent.tasksTotal > 0 ? Math.round((agent.tasksDone / agent.tasksTotal) * 100) : 0
          const isOpen = expanded === agent.id
          return (
            <div
              key={agent.id}
              className="rounded-lg overflow-hidden transition-all flex flex-col min-h-[160px]"
              style={{
                background: '#0e1018',
                border: `1px solid ${
                  isOpen ? 'rgba(0,230,118,0.25)' : 'rgba(255,255,255,0.06)'
                }`,
              }}
            >
              <button
                type="button"
                className="w-full text-left p-4 flex-1 hover:bg-white/[0.02] transition-all"
                onClick={() => setExpanded(isOpen ? null : agent.id)}
              >
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="flex items-center gap-2 min-w-0">
                    <span
                      className="w-2 h-2 rounded-full shrink-0 mt-1"
                      style={{
                        background: STATUS_COLOR[agent.status],
                        boxShadow:
                          agent.status === 'running' || agent.status === 'processing'
                            ? `0 0 6px ${STATUS_COLOR[agent.status]}`
                            : 'none',
                      }}
                    />
                    <span className="text-sm font-semibold mono truncate" style={{ color: '#e8eaf0' }}>
                      {agent.name}
                    </span>
                  </div>
                  <span
                    className="text-[10px] mono px-1.5 py-0.5 rounded shrink-0"
                    style={{
                      background: STATUS_BG[agent.status],
                      color: STATUS_COLOR[agent.status],
                    }}
                  >
                    {agent.status.toUpperCase()}
                  </span>
                </div>

                <p className="text-xs mb-3 line-clamp-2" style={{ color: '#5a6175', minHeight: 32 }}>
                  {agent.role}
                </p>

                <p className="text-[10px] mono mb-2 truncate" style={{ color: '#3a4155' }}>
                  {agent.model}
                </p>

                <div className="mb-2">
                  <div className="flex justify-between text-[10px] mono mb-1" style={{ color: '#3a4155' }}>
                    <span>Tasks</span>
                    <span>
                      {agent.tasksDone}/{agent.tasksTotal || '—'}
                    </span>
                  </div>
                  <div className="h-1 rounded-full overflow-hidden" style={{ background: 'rgba(255,255,255,0.06)' }}>
                    <div
                      className="h-full rounded-full transition-all"
                      style={{ width: `${pct}%`, background: STATUS_COLOR[agent.status] }}
                    />
                  </div>
                </div>

                <p className="text-[11px] leading-relaxed line-clamp-2" style={{ color: '#8892a4' }}>
                  {agent.lastAction}
                </p>
              </button>

              {isOpen && (
                <div className="px-4 pb-4" style={{ borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                  <p className="text-[10px] mono mt-3 mb-2" style={{ color: '#3a4155' }}>
                    ACTIVITY LOG
                  </p>
                  <div
                    className="rounded p-3 space-y-1.5 font-mono text-[11px] overflow-y-auto max-h-28"
                    style={{
                      background: '#07080d',
                      border: '1px solid rgba(255,255,255,0.05)',
                    }}
                  >
                    {agent.log.slice(0, 8).map((line, i) => (
                      <p key={i} style={{ color: i === 0 ? '#8892a4' : '#3a4155' }}>
                        {line}
                      </p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
