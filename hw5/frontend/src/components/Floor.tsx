// Centre: the five agent desks (who is doing what right now) and the live wire feed.
import { useEffect, useRef } from 'react'
import { AGENTS, Creature, ROLE_ORDER, isRole } from '../agents'
import { type Activity, TOOL_WORDS, delegationTarget, shortResult } from '../activity'
import type { AgentEvent, Role } from '../types'

export function Desks({ activity, involved, running }: { activity: Record<Role, Activity>; involved: Set<Role>; running: boolean }) {
  return (
    <div className="desks">
      {ROLE_ORDER.map(role => {
        const a = activity[role]
        const look = AGENTS[role]
        const benched = involved.size > 0 && !involved.has(role)
        return (
          <div key={role} className={`desk mood-${a.mood} ${benched ? 'benched' : ''}`}
               style={{ ['--agent' as string]: look.color, ['--glow' as string]: look.glow }}>
            <div className="desk-lamp" />
            <Creature role={role} size={58} mood={a.mood} />
            <div className="desk-name">{look.name}</div>
            <div className="desk-title">{look.title}</div>
            <div className="desk-line" title={a.line}>{benched ? (running ? 'Standing by' : 'Not needed on this ticket') : a.line}</div>
          </div>
        )
      })}
    </div>
  )
}

function Avatar({ role }: { role: string }) {
  return isRole(role) ? <Creature role={role} size={34} /> : <div className="human-avatar">✍️</div>
}

function EventRow({ e }: { e: AgentEvent }) {
  const role = isRole(e.agent) ? e.agent : null
  const color = role ? AGENTS[role].color : '#f5eef2'
  const name = role ? AGENTS[role].name : e.agent.replace('human:', '')
  const time = new Date(e.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })

  if (e.event === 'delegation' || e.event === 'delegation_refused') {
    const to = delegationTarget(e)
    const task = e.said?.replace(/^→ [a-z_]+: /, '') ?? ''
    return (
      <div className={`wire-baton ${e.event === 'delegation_refused' ? 'refused' : ''}`}>
        <Avatar role={e.agent} /><span className="baton-arrow">✈</span>{to && <Avatar role={to} />}
        <div className="baton-text">
          <b style={{ color }}>{name}</b> → <b style={{ color: to ? AGENTS[to].color : undefined }}>{to ? AGENTS[to].name : '?'}</b>
          <div className="baton-task">“{task}”</div>
        </div>
        <span className="wire-time">{time}</span>
      </div>
    )
  }
  if (e.event === 'mcp_tool_call' || e.event === 'mcp_tool_blocked') {
    const tool = e.tools[0]
    return (
      <div className={`wire-tool ${e.event === 'mcp_tool_blocked' ? 'blocked' : ''}`} style={{ ['--agent' as string]: color }}>
        <span className="tool-dot" />
        <code>{tool}</code>
        <span className="tool-args">{e.args ? Object.values(e.args).filter(v => typeof v !== 'object').join(', ') : ''}</span>
        <span className="tool-res">{e.event === 'mcp_tool_blocked' ? `⛔ ${e.said}` : shortResult(e.result)}</span>
      </div>
    )
  }
  if (e.event === 'final_output') {
    return (
      <div className="wire-signoff" style={{ ['--agent' as string]: color }}>
        <Avatar role={e.agent} />
        <div><b style={{ color }}>{name} signs off</b> <span className={`pill st-${e.status}`}>{e.status?.replace('_', ' ')}</span>
          <div className="signoff-text">{e.said}</div></div>
      </div>
    )
  }
  if (e.event === 'approval_prepared') {
    return <div className="wire-note">🧾 <b style={{ color }}>{name}</b> left a cheque in the sign-off tray: {e.said}</div>
  }
  if (e.event.startsWith('human_') || e.event === 'db_reset') {
    return <div className="wire-human">✍️ <b>{name}</b> {e.said}</div>
  }
  if (e.event === 'error') {
    return <div className="wire-note err">⚠️ <b style={{ color }}>{name}</b>: {e.said}</div>
  }
  if (e.event === 'run_start') {
    return <div className="wire-note" style={{ color }}>🕯 {name} clocks in{e.chain.length ? ` (asked by ${AGENTS[e.chain[e.chain.length - 1] as Role]?.name ?? 'desk'})` : ''}</div>
  }
  if (e.event === 'model_response') {
    const tools = e.tools.filter(Boolean)
    if (!e.said && !tools.length) return null
    return (
      <div className="wire-bubble" style={{ ['--agent' as string]: color }}>
        <Avatar role={e.agent} />
        <div className="bubble">
          <div className="bubble-head"><b style={{ color }}>{name}</b> <span className="voice">{role ? AGENTS[role].voice : ''}</span><span className="wire-time">{time}</span></div>
          {e.said && <div className="bubble-text">{e.said}</div>}
          {tools.length > 0 && (
            <div className="chips">{tools.map((t, i) => <span key={i} className="chip">{TOOL_WORDS[t] ?? t}</span>)}</div>
          )}
        </div>
      </div>
    )
  }
  return null
}

export function LiveWire({ events, running }: { events: AgentEvent[]; running: boolean }) {
  const box = useRef<HTMLDivElement>(null)
  // Follow the newest message inside the feed only (never scroll the whole page).
  useEffect(() => { const el = box.current; if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' }) }, [events.length])
  return (
    <div className="wire">
      <div className="wire-title">
        <span className={`onair ${running ? 'live' : ''}`}>{running ? 'ON AIR' : 'OFF AIR'}</span>
        The live wire
      </div>
      <div className="wire-scroll" ref={box}>
        {events.length === 0 && <div className="wire-empty">Quiet desk. Pick a ticket and wake the team. Their chatter shows up here.</div>}
        {events.map((e, i) => <EventRow key={`${e.ts}-${i}`} e={e} />)}
      </div>
    </div>
  )
}
