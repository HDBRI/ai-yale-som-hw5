// After a run: one card per agent that worked the ticket, plus the Boss's postcard to the customer.
import { AGENTS, Creature, isRole } from '../agents'
import type { TicketSummary } from '../types'

function countTools(tools: string[]) {
  const m = new Map<string, number>()
  tools.forEach(t => m.set(t, (m.get(t) ?? 0) + 1))
  return [...m.entries()]
}

export function ShiftReport({ summary }: { summary: TicketSummary | null }) {
  if (!summary || !summary.run_id) {
    return <div className="report empty">No shift report yet. Run the team on this ticket to get one.</div>
  }
  const boss = summary.boss_report
  return (
    <div className="report">
      <div className="report-head">
        <h3>Shift report</h3>
        <span className="muted">run {summary.run_id}</span>
      </div>
      {boss && (
        <div className="report-boss">
          <b>The Boss’s call:</b> {boss.summary}
          {boss.next_steps?.length > 0 && <ul>{boss.next_steps.map((s, i) => <li key={i}>{s}</li>)}</ul>}
        </div>
      )}
      <div className="report-grid">
        {summary.agents.filter(a => isRole(a.agent)).map(a => {
          const look = AGENTS[a.agent]
          return (
            <div key={a.agent} className="report-card" style={{ ['--agent' as string]: look.color }}>
              <div className="report-card-head">
                <Creature role={a.agent} size={36} mood="done" />
                <div><b>{look.name}</b><div className="muted small">{look.title}</div></div>
                {a.status && <span className={`pill st-${a.status}`}>{a.status.replace('_', ' ')}</span>}
              </div>
              <p>{a.summary ?? 'Still working…'}</p>
              <div className="chips">
                {countTools(a.tools).map(([t, n]) => <span key={t} className="chip tool">{t}{n > 1 ? ` ×${n}` : ''}</span>)}
                {a.delegated_to.map((r, i) => <span key={`d${i}`} className="chip pass">✈ {isRole(r) ? AGENTS[r].name : r}</span>)}
                {a.blocked.map((t, i) => <span key={`b${i}`} className="chip blocked">⛔ {t}</span>)}
              </div>
            </div>
          )
        })}
      </div>
      {boss?.customer_message && (
        <div className="postcard">
          <div className="postcard-stamp"><img src="/som/som-logo.jpg" alt="" /></div>
          <div className="postcard-label">Draft reply to the customer</div>
          <div className="postcard-body">{boss.customer_message}</div>
        </div>
      )}
      {boss && boss.facts?.length > 0 && (
        <details className="facts">
          <summary>Receipts: {boss.facts.length} facts the team used (each from an MCP tool)</summary>
          <table><tbody>{boss.facts.map((f, i) => <tr key={i}><td><code>{f.tool}</code></td><td>{f.field}</td><td>{f.value}</td></tr>)}</tbody></table>
        </details>
      )}
    </div>
  )
}
