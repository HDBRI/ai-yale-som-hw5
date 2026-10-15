// The five agents as Labubu-style desk creatures. Same body, different colour,
// accessory and "voice", so you can tell who is talking at a glance.
import type { Role } from './types'

export interface AgentLook {
  role: Role
  name: string
  title: string
  color: string
  glow: string
  voice: string // how their bubbles read
  verb: string  // what they do while working
}

export const AGENTS: Record<Role, AgentLook> = {
  boss:             { role: 'boss', name: 'Boss', title: 'Runs the desk', color: '#ff4fa3', glow: 'rgba(255,79,163,.55)', voice: 'decides', verb: 'triaging' },
  inventory:        { role: 'inventory', name: 'Inventory', title: 'Counts every hoodie', color: '#c9a0ff', glow: 'rgba(201,160,255,.5)', voice: 'counts', verb: 'counting stock' },
  accounting:       { role: 'accounting', name: 'Accounting', title: 'Guards the cash', color: '#ffd166', glow: 'rgba(255,209,102,.5)', voice: 'tallies', verb: 'crunching numbers' },
  facilities:       { role: 'facilities', name: 'Facilities', title: 'Keeps the keys', color: '#8fd3ff', glow: 'rgba(143,211,255,.5)', voice: 'checks', verb: 'checking the lease' },
  customer_service: { role: 'customer_service', name: 'Customer Service', title: 'Talks to customers', color: '#ff9ccb', glow: 'rgba(255,156,203,.5)', voice: 'writes', verb: 'drafting a reply' },
}

export const ROLE_ORDER: Role[] = ['boss', 'inventory', 'accounting', 'facilities', 'customer_service']

export function isRole(x: string): x is Role {
  return x in AGENTS
}

function Accessory({ role }: { role: Role }) {
  switch (role) {
    case 'boss': // crown
      return <path d="M20 9 L25 1 L32 8 L39 1 L44 9 L42 15 L22 15 Z" fill="#ffd166" stroke="#0b0b0d" strokeWidth="1.2" />
    case 'inventory': // little box
      return (<g><rect x="45" y="52" width="15" height="13" rx="2" fill="#d9a66b" stroke="#0b0b0d" strokeWidth="1.2" />
        <path d="M45 57 H60 M52.5 52 V57" stroke="#0b0b0d" strokeWidth="1.1" /></g>)
    case 'accounting': // gold coin + monocle
      return (<g><circle cx="39" cy="42" r="6" fill="none" stroke="#ffd166" strokeWidth="1.6" />
        <circle cx="54" cy="60" r="7" fill="#ffd166" stroke="#0b0b0d" strokeWidth="1.2" />
        <text x="54" y="64" fontSize="9" textAnchor="middle" fontWeight="800" fill="#0b0b0d">$</text></g>)
    case 'facilities': // key
      return (<g transform="translate(46 50) rotate(25)"><circle cx="4" cy="4" r="4" fill="none" stroke="#ffd166" strokeWidth="2" />
        <path d="M8 4 H18 M14 4 V8 M17 4 V7" stroke="#ffd166" strokeWidth="2" /></g>)
    case 'customer_service': // heart
      return <path d="M54 66 C44 59 46 51 51 52 C53 52.5 54 54 54 55 C54 54 55 52.5 57 52 C62 51 64 59 54 66 Z" fill="#ff4fa3" stroke="#0b0b0d" strokeWidth="1" />
  }
}

export function Creature({ role, size = 64, mood = 'idle' }: { role: Role; size?: number; mood?: 'idle' | 'working' | 'talking' | 'done' }) {
  const c = AGENTS[role].color
  return (
    <svg className={`creature mood-${mood}`} width={size} height={size * 1.125} viewBox="0 0 64 72" aria-label={AGENTS[role].name}>
      <path d="M17 26 C10 6 14 -2 21 3 C25 7 25 17 25 24 Z" fill={c} />
      <path d="M47 26 C54 6 50 -2 43 3 C39 7 39 17 39 24 Z" fill={c} />
      <path d="M19 22 C17 10 19 6 21 7 C23 9 23 16 23 22 Z" fill="#ffd1e6" />
      <path d="M45 22 C47 10 45 6 43 7 C41 9 41 16 41 22 Z" fill="#ffd1e6" />
      <ellipse cx="32" cy="44" rx="22" ry="24" fill={c} />
      <ellipse cx="32" cy="46" rx="15" ry="14" fill="#ffe7f1" />
      <g className="eyes">
        <circle cx="25" cy="42" r="3.4" fill="#0b0b0d" /><circle cx="39" cy="42" r="3.4" fill="#0b0b0d" />
        <circle cx="26" cy="41" r="1.1" fill="#fff" /><circle cx="40" cy="41" r="1.1" fill="#fff" />
      </g>
      {mood === 'done'
        ? <path d="M24 51 Q32 57 40 51" stroke="#0b0b0d" strokeWidth="2.4" fill="none" strokeLinecap="round" />
        : (<g className="mouth"><path d="M23 51 Q32 58 41 51" fill="#0b0b0d" />
            <path d="M25 52 l2 3 l2 -3 l2 3 l2 -3 l2 3 l2 -3 l2 3" stroke="#fff" strokeWidth="1.2" fill="none" /></g>)}
      <Accessory role={role} />
    </svg>
  )
}
