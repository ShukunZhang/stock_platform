import type { Msg } from '../types'

export function ChatMsg({ msg }: { msg: Msg }) {
  const isUser = msg.role === 'user'
  const isSystem = msg.role === 'system'
  return (
    <div className={`flex gap-3 slide-up ${isUser ? 'flex-row-reverse' : ''}`}>
      <div
        className="shrink-0 w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold mono"
        style={{
          background: isUser
            ? 'rgba(0,212,255,0.15)'
            : isSystem
              ? 'rgba(245,166,35,0.12)'
              : 'rgba(0,230,118,0.12)',
          border: `1px solid ${
            isUser
              ? 'rgba(0,212,255,0.3)'
              : isSystem
                ? 'rgba(245,166,35,0.25)'
                : 'rgba(0,230,118,0.25)'
          }`,
          color: isUser ? '#00d4ff' : isSystem ? '#f5a623' : '#00e676',
        }}
      >
        {isUser ? 'YOU' : isSystem ? 'SYS' : 'AI'}
      </div>
      <div className={`max-w-[78%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        <div
          className="px-4 py-3 rounded-lg text-sm leading-relaxed"
          style={{
            background: isUser ? 'rgba(0,212,255,0.08)' : 'rgba(255,255,255,0.04)',
            border: `1px solid ${isUser ? 'rgba(0,212,255,0.18)' : 'rgba(255,255,255,0.07)'}`,
            color: isUser ? '#b8f0ff' : '#d8dce8',
            whiteSpace: 'pre-wrap',
          }}
        >
          {msg.thinking ? (
            <span className="text-[#5a6175]">
              Analyzing<span className="cursor-blink">▊</span>
            </span>
          ) : (
            <AgentText text={msg.text} />
          )}
        </div>
        <span className="text-[10px] mono" style={{ color: '#3a4155' }}>
          {msg.ts}
        </span>
      </div>
    </div>
  )
}

function AgentText({ text }: { text: string }) {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`|\n)/g)
  return (
    <>
      {parts.map((p, i) => {
        if (p.startsWith('**') && p.endsWith('**'))
          return (
            <strong key={i} style={{ color: '#e8eaf0', fontWeight: 600 }}>
              {p.slice(2, -2)}
            </strong>
          )
        if (p.startsWith('`') && p.endsWith('`'))
          return (
            <code
              key={i}
              className="mono text-[12px] px-1 rounded"
              style={{ background: 'rgba(0,230,118,0.1)', color: '#00e676' }}
            >
              {p.slice(1, -1)}
            </code>
          )
        if (p === '\n') return <br key={i} />
        return <span key={i}>{p}</span>
      })}
    </>
  )
}
