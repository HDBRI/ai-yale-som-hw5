// Right column: the cash register (checking balance) and the sign-off tray (approvals).
import { useEffect, useRef, useState } from 'react'
import { AGENTS, Creature, isRole } from '../agents'
import type { ApprovalItem, Cash } from '../types'

const money = (n: number) => n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })

/** Rolls the number from its old value to the new one so a payment visibly "drains" the drawer. */
function useRolling(target: number | null, ms = 1400) {
  const [shown, setShown] = useState(target)
  const from = useRef(target)
  useEffect(() => {
    if (target == null) return
    const start = from.current ?? target
    if (start === target) { setShown(target); return }
    const t0 = performance.now()
    let raf = 0
    const tick = (t: number) => {
      const p = Math.min(1, (t - t0) / ms)
      const eased = 1 - Math.pow(1 - p, 3)
      setShown(start + (target - start) * eased)
      if (p < 1) raf = requestAnimationFrame(tick)
      else from.current = target
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [target, ms])
  return shown
}

export function CashRegister({ cash, lastChange }: { cash: Cash | null; lastChange: number | null }) {
  const shown = useRolling(cash?.balance ?? null)
  const low = cash != null && cash.balance < 500
  return (
    <div className={`register ${low ? 'low' : ''}`}>
      <div className="register-top"><span>CHECKING</span><span>{cash ? `as of ${cash.as_of}` : '—'}</span></div>
      <div className="register-display">{shown == null ? '----' : money(shown)}</div>
      {lastChange != null && lastChange !== 0 && (
        <div key={lastChange} className={`register-change ${lastChange < 0 ? 'down' : 'up'}`}>
          {lastChange < 0 ? '▼' : '▲'} {money(Math.abs(lastChange))}
        </div>
      )}
      <div className="register-foot">{low ? 'Below the $500 reserve' : 'Reserve floor $500'}</div>
    </div>
  )
}

const KIND_LABEL: Record<string, string> = {
  invoice_payment: 'Pay vendor invoice', rent_payment: 'Pay rent', purchase: 'Approve purchase',
  discount: 'Approve discount', other: 'Approve',
}

interface TrayProps {
  approvals: ApprovalItem[]
  approver: string
  setApprover: (s: string) => void
  onDecide: (id: string, ok: boolean) => Promise<void>
  busyId: string | null
}

export function SignOffTray({ approvals, approver, setApprover, onDecide, busyId }: TrayProps) {
  const pending = approvals.filter(a => a.status === 'pending')
  const done = approvals.filter(a => a.status !== 'pending').slice(-4).reverse()
  return (
    <div className="tray">
      <div className="tray-title">Sign-off tray <span className="count">{pending.length}</span></div>
      <label className="signer">
        <span>Signing as</span>
        <input value={approver} onChange={e => setApprover(e.target.value)} placeholder="Your name" />
      </label>
      {pending.length === 0 && <div className="tray-empty">Nothing waiting on you. Agents can only <i>prepare</i> payments, and they land here for your signature.</div>}
      {pending.map(a => {
        const role = isRole(a.prepared_by) ? a.prepared_by : null
        return (
          <div key={a.id} className={`cheque kind-${a.kind}`}>
            <div className="cheque-top">
              <span>{KIND_LABEL[a.kind] ?? a.kind}{a.ref_id != null ? ` #${a.ref_id}` : ''}</span>
              <span className="muted small">ticket {a.ticket_id}</span>
            </div>
            <div className="cheque-amount">{a.amount != null ? (a.kind === 'discount' ? `${a.amount}%` : money(a.amount)) : '—'}</div>
            <div className="cheque-reason">{a.reason}</div>
            <div className="cheque-by">
              {role && <Creature role={role} size={22} />} prepared by {role ? AGENTS[role].name : a.prepared_by}
            </div>
            <div className="cheque-actions">
              <button className="btn-approve" disabled={!approver.trim() || busyId === a.id} onClick={() => onDecide(a.id, true)}>
                {busyId === a.id ? 'Signing…' : '✍️ Approve'}
              </button>
              <button className="btn-reject" disabled={!approver.trim() || busyId === a.id} onClick={() => onDecide(a.id, false)}>Decline</button>
            </div>
            <div className="sigline">x ____________________ {approver || ''}</div>
          </div>
        )
      })}
      {done.length > 0 && (
        <div className="ledger">
          <div className="ledger-title">Recent sign-offs</div>
          {done.map(a => (
            <div key={a.id + a.decided_at} className={`ledger-row ${a.status}`}>
              <span>{a.status === 'approved' ? '✔' : a.status === 'rejected' ? '✕' : '!'}</span>
              <span>{KIND_LABEL[a.kind]} {a.ref_id ?? ''}</span>
              <span>{a.amount != null && a.kind !== 'discount' ? money(a.amount) : ''}</span>
              <span className="muted small">{a.decided_by}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
