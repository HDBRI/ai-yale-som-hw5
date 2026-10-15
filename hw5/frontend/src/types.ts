export type Role = 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: string
  notes: string | null
  created_at: string
  state: 'open' | 'resolved'
  running: boolean
}

export interface AgentEvent {
  ts: string
  run_id: string
  ticket_id: number | null
  agent: string
  chain: string[]
  step: number | null
  event: string
  said: string | null
  tools: string[]
  args: Record<string, unknown> | null
  result: unknown
  status: string | null
}

export interface ApprovalItem {
  id: string
  kind: 'invoice_payment' | 'rent_payment' | 'purchase' | 'discount' | 'other'
  ref_id: number | null
  amount: number | null
  reason: string
  ticket_id: number | null
  prepared_by: string
  run_id: string
  created_at: string
  status: 'pending' | 'approved' | 'rejected' | 'failed'
  decided_by: string | null
  decided_at: string | null
  result: Record<string, unknown> | null
}

export interface Fact { tool: string; field: string; value: string }

export interface Report {
  agent: Role
  ticket_ids: number[]
  status: string
  summary: string
  facts: Fact[]
  actions_taken: string[]
  approvals_needed: { kind: string; ref_id: number | null; amount: number | null; reason: string }[]
  customer_message: string | null
  next_steps: string[]
}

export interface RunInfo {
  run_id: string
  ticket_id: number
  status: 'running' | 'finished' | 'failed'
  report: Report | null
  error?: string
  ticket_status?: string | null
}

export interface AgentSummary {
  agent: Role
  status: string | null
  summary: string | null
  tools: string[]
  delegated_to: string[]
  blocked: string[]
}

export interface TicketSummary {
  ticket_id: number
  run_id: string | null
  agents: AgentSummary[]
  boss_report: Report | null
}

export interface Cash { account: string; balance: number; as_of: string; date_today: string }
