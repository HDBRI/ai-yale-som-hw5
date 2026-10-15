// Every call goes to the FastAPI backend in HW5/backend/main.py.
import type { AgentEvent, ApprovalItem, Cash, RunInfo, Ticket, TicketSummary } from './types'

export const API_URL = (import.meta.env.VITE_API_URL as string | undefined) ?? 'http://localhost:8000'

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) },
  })
  const body = await res.json().catch(() => ({}))
  if (!res.ok) {
    const detail = (body as { detail?: unknown }).detail
    const msg = typeof detail === 'string' ? detail : (detail as { error?: string })?.error ?? res.statusText
    throw new Error(msg)
  }
  return body as T
}

export const api = {
  health: () => call<{ ok: boolean; model: string; running_tickets: number[] }>('/api/health'),
  tickets: () => call<{ date_today: string; tickets: Ticket[] }>('/api/tickets'),
  runTicket: (id: number, dryRun: boolean) =>
    call<RunInfo>(`/api/tickets/${id}/run?wait=false`, { method: 'POST', body: JSON.stringify({ dry_run: dryRun }) }),
  run: (runId: string) => call<RunInfo>(`/api/runs/${runId}`),
  events: (q: { runId?: string; ticketId?: number; limit?: number }) => {
    const p = new URLSearchParams({ limit: String(q.limit ?? 300) })
    if (q.runId) p.set('run_id', q.runId)
    if (q.ticketId != null) p.set('ticket_id', String(q.ticketId))
    return call<{ events: AgentEvent[] }>(`/api/events?${p}`)
  },
  summary: (id: number) => call<TicketSummary>(`/api/tickets/${id}/summary`),
  approvals: (status = 'all') => call<{ approvals: ApprovalItem[] }>(`/api/approvals?status=${status}`),
  approve: (id: string, decidedBy: string) =>
    call<{ summary: string; ticket_status: string | null }>(`/api/approvals/${id}/approve`, {
      method: 'POST', body: JSON.stringify({ decided_by: decidedBy }),
    }),
  reject: (id: string, decidedBy: string, note?: string) =>
    call<{ summary: string; ticket_status: string | null }>(`/api/approvals/${id}/reject`, {
      method: 'POST', body: JSON.stringify({ decided_by: decidedBy, note }),
    }),
  cash: () => call<Cash>('/api/cash'),
  reset: () => call<{ ok: boolean; checking: number }>('/api/reset', { method: 'POST' }),
}
