// Turns the raw event stream into "what is each agent doing right now".
import { AGENTS, isRole } from './agents'
import type { AgentEvent, Role } from './types'

export type Mood = 'idle' | 'working' | 'talking' | 'done'
export interface Activity { mood: Mood; line: string; ts: string | null }

export const TOOL_WORDS: Record<string, string> = {
  check_stock: 'checking the shelf',
  get_sku_stock_all_sizes: 'scanning every size',
  get_rent_due: 'reading the lease',
  get_sku_pricing: 'pulling cost & list price',
  list_open_tickets: 'reading the queue',
  list_tickets: 'reading the queue',
  get_ticket: 'reading the ticket',
  get_invoice: 'opening the invoice',
  get_cash_position: 'counting the cash drawer',
  list_vendors: 'flipping the vendor rolodex',
  list_payments: 'checking past payments',
  update_ticket: 'writing on the ticket',
  adjust_inventory: 'moving stock',
  record_payment: 'trying to pay',
  delegate: 'handing off',
}

export function delegationTarget(e: AgentEvent): Role | null {
  const m = e.said?.match(/^→ ([a-z_]+):/)
  return m && isRole(m[1]) ? m[1] : null
}

export function activityByAgent(eventsOldestFirst: AgentEvent[]): Record<Role, Activity> {
  const out = Object.fromEntries(
    Object.keys(AGENTS).map(r => [r, { mood: 'idle', line: 'At the desk', ts: null }]),
  ) as Record<Role, Activity>
  for (const e of eventsOldestFirst) {
    if (!isRole(e.agent)) continue
    const a = out[e.agent]
    a.ts = e.ts
    switch (e.event) {
      case 'run_start':
        a.mood = 'working'; a.line = e.chain.length ? `Picked up a task from ${AGENTS[e.chain[e.chain.length - 1] as Role]?.name ?? 'the desk'}` : 'Reading the ticket'
        break
      case 'model_response': {
        const tool = e.tools.find(t => t !== 'delegate') ?? e.tools[0]
        if (e.said) { a.mood = 'talking'; a.line = e.said }
        else if (tool) { a.mood = 'working'; a.line = `${TOOL_WORDS[tool] ?? tool}…` }
        break
      }
      case 'mcp_tool_call':
        a.mood = 'working'; a.line = `${TOOL_WORDS[e.tools[0]] ?? e.tools[0]} ✓`
        break
      case 'mcp_tool_blocked':
        a.mood = 'working'; a.line = `Blocked: ${e.said ?? e.tools[0]}`
        break
      case 'delegation': {
        const to = delegationTarget(e)
        a.mood = 'working'; a.line = `Waiting on ${to ? AGENTS[to].name : 'a teammate'}…`
        break
      }
      case 'final_output':
      case 'run_end':
        a.mood = 'done'; a.line = e.said ?? 'Done'
        break
      case 'error':
        a.mood = 'done'; a.line = `Hit a problem: ${e.said ?? ''}`
        break
    }
  }
  return out
}

export function shortResult(result: unknown): string {
  if (result == null || typeof result !== 'object') return ''
  const r = result as Record<string, unknown>
  if (r.ok === false || r.found === false) return `✗ ${String(r.error ?? 'not found')}`
  const keep = ['qty_on_hand', 'shortfall', 'total_on_hand', 'monthly_rent', 'next_due', 'days_until_due',
    'unit_cost', 'list_price', 'max_discount_pct_before_loss', 'amount', 'status', 'days_past_due',
    'total_cash', 'cash_after_all_bills', 'status_after', 'balance_after', 'count']
  const parts = keep.filter(k => k in r).slice(0, 4).map(k => `${k.replace(/_/g, ' ')}: ${String(r[k])}`)
  return parts.join(' · ')
}
