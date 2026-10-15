import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { activityByAgent } from './activity'
import { AGENTS, isRole } from './agents'
import { API_URL, api } from './api'
import { Desks, LiveWire } from './components/Floor'
import { CashRegister, SignOffTray } from './components/Register'
import { ShiftReport } from './components/ShiftReport'
import { TicketSpike } from './components/TicketSpike'
import type { AgentEvent, ApprovalItem, Cash, Role, Ticket, TicketSummary } from './types'

const POLL_MS = 1200

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [dateToday, setDateToday] = useState('')
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])        // newest first, from the API
  const [summary, setSummary] = useState<TicketSummary | null>(null)
  const [approvals, setApprovals] = useState<ApprovalItem[]>([])
  const [cash, setCash] = useState<Cash | null>(null)
  const [lastChange, setLastChange] = useState<number | null>(null)
  const [activeRun, setActiveRun] = useState<{ runId: string; ticketId: number } | null>(null)
  const [approver, setApprover] = useState(() => localStorage.getItem('desk-approver') ?? '')
  const [busyId, setBusyId] = useState<string | null>(null)
  const [dryRun, setDryRun] = useState(false)
  const [online, setOnline] = useState<boolean | null>(null)
  const [toast, setToast] = useState<{ text: string; tone: 'ok' | 'err' | 'info' } | null>(null)
  const prevBalance = useRef<number | null>(null)

  useEffect(() => { localStorage.setItem('desk-approver', approver) }, [approver])
  useEffect(() => { if (!toast) return; const t = setTimeout(() => setToast(null), 5200); return () => clearTimeout(t) }, [toast])

  const refreshDesk = useCallback(async () => {
    try {
      const [t, a, c] = await Promise.all([api.tickets(), api.approvals('all'), api.cash()])
      setTickets(t.tickets); setDateToday(t.date_today); setApprovals(a.approvals)
      if (prevBalance.current != null && prevBalance.current !== c.balance) setLastChange(c.balance - prevBalance.current)
      prevBalance.current = c.balance
      setCash(c); setOnline(true)
      setSelectedId(id => id ?? t.tickets.find(x => x.state === 'open')?.id ?? t.tickets[0]?.id ?? null)
    } catch {
      setOnline(false)
    }
  }, [])

  const refreshTicket = useCallback(async (id: number) => {
    const [ev, s] = await Promise.all([api.events({ ticketId: id, limit: 400 }), api.summary(id)])
    setEvents(ev.events); setSummary(s)
  }, [])

  useEffect(() => { refreshDesk() }, [refreshDesk])
  useEffect(() => { if (selectedId != null) refreshTicket(selectedId).catch(() => setOnline(false)) }, [selectedId, refreshTicket])

  // While the team is working: poll the event stream and the run until it finishes.
  useEffect(() => {
    if (!activeRun) return
    let stopped = false
    const iv = setInterval(async () => {
      try {
        if (selectedId === activeRun.ticketId) {
          const ev = await api.events({ ticketId: activeRun.ticketId, limit: 400 })
          if (!stopped) setEvents(ev.events)
        }
        const run = await api.run(activeRun.runId)
        if (run.status !== 'running' && !stopped) {
          stopped = true
          setActiveRun(null)
          await refreshDesk()
          if (selectedId === activeRun.ticketId) await refreshTicket(activeRun.ticketId)
          if (run.status === 'failed') setToast({ text: `Run failed: ${run.error}`, tone: 'err' })
          else if (run.ticket_status === 'resolved') setToast({ text: `Ticket #${run.ticket_id} resolved. The team signed off.`, tone: 'ok' })
          else if (run.ticket_status === 'waiting') setToast({ text: `Ticket #${run.ticket_id}: the team is done and waiting on your signature.`, tone: 'info' })
          else setToast({ text: `Ticket #${run.ticket_id}: run finished (${run.report?.status ?? 'no report'}).`, tone: 'info' })
        }
      } catch (err) {
        // The backend restarted and forgot this run: stop waiting and show what is there.
        if (!stopped && (err as Error).message.startsWith('No run')) {
          stopped = true
          setActiveRun(null)
          await refreshDesk()
          setToast({ text: 'The backend restarted during the run, so it stopped. Wake the team again.', tone: 'err' })
        }
      }
    }, POLL_MS)
    return () => { stopped = true; clearInterval(iv) }
  }, [activeRun, selectedId, refreshDesk, refreshTicket])

  const selected = tickets.find(t => t.id === selectedId) ?? null
  const running = activeRun != null && activeRun.ticketId === selectedId

  // Only the latest run on this ticket (plus anything after it, like a human signing) drives the desks.
  const latestRunEvents = useMemo(() => {
    const oldest = [...events].reverse()
    const lastStart = [...oldest].reverse().find(e => e.event === 'run_start' && e.chain.length === 0 && isRole(e.agent))
    return lastStart ? oldest.filter(e => e.ts >= lastStart.ts) : oldest
  }, [events])
  const activity = useMemo(() => activityByAgent(latestRunEvents), [latestRunEvents])
  // Agents that actually clocked in on the latest run; the rest are greyed out as "not needed".
  const involved = useMemo(() => new Set(
    latestRunEvents.filter(e => e.event === 'run_start').map(e => e.agent).filter(isRole) as Role[],
  ), [latestRunEvents])

  async function wakeTeam() {
    if (!selected) return
    try {
      const run = await api.runTicket(selected.id, dryRun)
      setActiveRun({ runId: run.run_id, ticketId: selected.id })
      setSummary(null)
      setTickets(ts => ts.map(t => t.id === selected.id ? { ...t, running: true } : t))
      setToast({ text: `${AGENTS.boss.name} picked up ticket #${selected.id}${dryRun ? ' (practice run, no writes)' : ''}.`, tone: 'info' })
    } catch (err) {
      setToast({ text: (err as Error).message, tone: 'err' })
    }
  }

  async function decide(id: string, ok: boolean) {
    setBusyId(id)
    try {
      const r = ok ? await api.approve(id, approver.trim()) : await api.reject(id, approver.trim())
      setToast({ text: r.summary + (r.ticket_status === 'resolved' ? ' Ticket resolved.' : ''), tone: 'ok' })
    } catch (err) {
      setToast({ text: `Not paid: ${(err as Error).message}`, tone: 'err' })
    } finally {
      setBusyId(null)
      await refreshDesk()
      if (selectedId != null) await refreshTicket(selectedId)
    }
  }

  async function freshShift() {
    if (!confirm('Start a fresh shift? This restores the original database (cash back to the start, tickets reopened) and clears the sign-off tray. The audit trail is kept.')) return
    try {
      await api.reset()
      setLastChange(null); prevBalance.current = null
      await refreshDesk()
      if (selectedId != null) await refreshTicket(selectedId)
      setToast({ text: 'Fresh shift: the database is back to its original values.', tone: 'ok' })
    } catch (err) { setToast({ text: (err as Error).message, tone: 'err' }) }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="logo-chip"><img src="/som/som-logo.jpg" alt="Yale School of Management" /></div>
        <div className="brand">
          <h1>Campus Customs <span>Night Desk</span></h1>
          <div className="sub">Chapel Street, New Haven · shop date <b>{dateToday || '…'}</b> · five agents on shift</div>
        </div>
        <div className="top-actions">
          <span className={`conn ${online ? 'on' : online === false ? 'off' : ''}`} title={API_URL}>
            {online ? 'backend live' : online === false ? `can't reach ${API_URL}` : 'connecting…'}
          </span>
          <label className="practice"><input type="checkbox" checked={dryRun} onChange={e => setDryRun(e.target.checked)} /> practice run</label>
          <button className="btn-ghost" onClick={freshShift} disabled={activeRun != null}>↺ Fresh shift</button>
        </div>
      </header>

      <div className="layout">
        <TicketSpike tickets={tickets} selectedId={selectedId} approvals={approvals} onSelect={setSelectedId} />

        <main className="floor">
          {selected && (
            <section className="ticket-hero">
              <div>
                <div className="hero-kicker">Ticket #{selected.id} · {selected.type.replace('_', ' ')}</div>
                <h2>{selected.subject}</h2>
                <div className="hero-notes">{selected.notes?.split('\n')[0]}</div>
                <div className="hero-meta">from <b>{selected.requester}</b> · status <span className={`pill st-${selected.status}`}>{selected.status.replace('_', ' ')}</span></div>
              </div>
              <button className={`wake ${running ? 'busy' : ''}`} onClick={wakeTeam} disabled={activeRun != null}>
                {running ? <>Team working<span className="dots" /></> : selected.state === 'resolved' ? 'Run the team again' : 'Wake the team ✦'}
              </button>
            </section>
          )}
          <Desks activity={activity} involved={involved} running={running} />
          <LiveWire events={latestRunEvents} running={running} />
          <ShiftReport summary={running ? null : summary} />
        </main>

        <aside className="till">
          <CashRegister cash={cash} lastChange={lastChange} />
          <SignOffTray approvals={approvals} approver={approver} setApprover={setApprover} onDecide={decide} busyId={busyId} />
          <div className="evans"><img src="/som/evans-front.jpg" alt="Evans Hall, Yale SOM" /><span>Powered by Yale SOM night owls</span></div>
        </aside>
      </div>

      {toast && <div className={`toast ${toast.tone}`}>{toast.text}</div>}
    </div>
  )
}
