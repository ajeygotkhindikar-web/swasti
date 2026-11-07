import { useEffect, useState, type ReactNode } from 'react'
import { NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import {
  Bell, Bot, CalendarCheck, ClipboardList, FileText, House, LayoutDashboard, LifeBuoy, Lightbulb, Lock, LogOut, Menu,
  Mic, Moon, Repeat, Settings, Stethoscope, Sun, User as UserIcon, X,
} from 'lucide-react'
import clsx from 'clsx'
import { Logo } from './Logo'
import { useAuth, type Role } from '../lib/auth'
import { api } from '../lib/api'
import { useTheme } from '../lib/hooks'

interface Item { to: string; label: string; icon: typeof House; roles: Role[] }
const ALL: Role[] = ['individual', 'coach', 'counselor', 'admin']
export const NAV: Item[] = [
  { to: '/', label: 'Home', icon: House, roles: ALL },
  { to: '/profile', label: 'My Profile', icon: UserIcon, roles: ALL },
  { to: '/assessment', label: 'Wellness Assessment', icon: ClipboardList, roles: ['individual'] },
  { to: '/interview', label: 'Interview Assessment', icon: Mic, roles: ['coach', 'counselor'] },
  { to: '/dashboard', label: '360° Wellness Dashboard', icon: LayoutDashboard, roles: ['individual'] },
  { to: '/agents', label: 'Wellness AI Agents', icon: Bot, roles: ALL },
  { to: '/recommendations', label: 'My Recommendations', icon: Lightbulb, roles: ['individual'] },
  { to: '/habits', label: 'Micro-Habits', icon: Repeat, roles: ['individual'] },
  { to: '/reviews', label: 'Quarterly Reviews', icon: CalendarCheck, roles: ['individual'] },
  { to: '/reports', label: 'Wellness Reports', icon: FileText, roles: ['individual', 'coach', 'counselor'] },
  { to: '/coach', label: 'Coach / Counsellor Portal', icon: Stethoscope, roles: ['coach', 'counselor'] },
  { to: '/admin', label: 'Administration', icon: Settings, roles: ['admin'] },
  { to: '/privacy', label: 'Privacy & Consent', icon: Lock, roles: ALL },
  { to: '/help', label: 'Help & Resources', icon: LifeBuoy, roles: ALL },
]
const MOBILE: Record<Role, string[]> = {
  individual: ['/', '/dashboard', '/assessment', '/habits'],
  coach: ['/', '/coach', '/interview', '/reports'],
  counselor: ['/', '/coach', '/interview', '/reports'],
  admin: ['/', '/admin', '/agents', '/help'],
}

function ThemeSwitch() {
  const [theme, setTheme] = useTheme()
  const opts = [['light', Sun], ['dark', Moon]] as const
  return (
    <div className="flex rounded-xl border border-line p-0.5" role="radiogroup" aria-label="Theme">
      {opts.map(([v, I]) => (
        <button key={v} role="radio" aria-checked={theme === v} aria-label={`${v} theme`} onClick={() => setTheme(v)}
          className={clsx('grid h-8 w-8 place-items-center rounded-lg', theme === v ? 'bg-fill text-onfill' : 'text-muted')}>
          <I size={15} />
        </button>
      ))}
    </div>
  )
}

function Notifications() {
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<any[]>([])
  const load = () => api<any[]>('/notifications').then(setItems).catch(() => {})
  useEffect(() => { load() }, [])
  const unread = items.filter((i) => !i.is_read).length
  return (
    <div className="relative">
      <button className="relative grid h-10 w-10 place-items-center rounded-xl hover:bg-surface2" aria-label={`Notifications, ${unread} unread`} onClick={() => setOpen(!open)}>
        <Bell size={18} />
        {unread > 0 && <span className="absolute right-1.5 top-1.5 grid h-4 min-w-4 place-items-center rounded-full bg-fillstrong px-1 text-[10px] font-bold text-onfill">{unread}</span>}
      </button>
      {open && (
        <div className="card absolute right-0 z-40 mt-2 w-[min(22rem,calc(100vw-2rem))] p-2">
          {items.length === 0 && <p className="p-3 text-sm text-muted">You're all caught up.</p>}
          {items.slice(0, 8).map((n) => (
            <button key={n.notification_id} className={clsx('block w-full rounded-xl p-3 text-left hover:bg-surface2', !n.is_read && 'bg-teal-soft/50')}
              onClick={async () => { await api(`/notifications/${n.notification_id}/read`, { method: 'POST' }); load() }}>
              <div className="text-sm font-semibold">{n.title}</div>
              <div className="text-xs text-muted">{n.message}</div>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export function Layout({ children }: { children?: ReactNode }) {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const loc = useLocation()
  const [drawer, setDrawer] = useState(false)
  useEffect(() => setDrawer(false), [loc.pathname])
  if (!user) return null
  const items = NAV.filter((n) => n.roles.includes(user.user_role))
  const SideNav = (
    <nav className="space-y-0.5" aria-label="Main">
      {items.map(({ to, label, icon: I }) => (
        <NavLink key={to} to={to} end={to === '/'}
          className={({ isActive }) => clsx('flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium', isActive ? 'bg-fill text-onfill font-semibold' : 'text-ink/80 hover:bg-fillsoft')}>
          <I size={17} aria-hidden /> {label}
        </NavLink>
      ))}
    </nav>
  )
  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[17rem_1fr]">
      <aside className="sticky top-0 hidden h-screen flex-col gap-6 overflow-y-auto border-r border-line bg-surface p-5 lg:flex">
        <Logo />
        {SideNav}
        <div className="mt-auto space-y-3">
          <ThemeSwitch />
          <p className="text-[11px] italic text-muted">Balance Within. Harmony Around. Well-being for All.</p>
          <p className="text-[10px] text-muted/80" title="Build time">Build {__BUILD_TIME__}</p>
        </div>
      </aside>

      {drawer && (
        <div className="fixed inset-0 z-50 bg-black/40 lg:hidden" onClick={() => setDrawer(false)}>
          <div className="h-full w-72 max-w-[85vw] overflow-y-auto bg-surface p-5" onClick={(e) => e.stopPropagation()}>
            <div className="mb-6 flex items-center justify-between"><Logo compact /><button aria-label="Close menu" onClick={() => setDrawer(false)}><X /></button></div>
            {SideNav}
            <div className="mt-6"><ThemeSwitch /></div>
          </div>
        </div>
      )}

      <div className="min-w-0">
        <header className="sticky top-0 z-30 flex items-center justify-between gap-3 border-b border-line bg-bg/90 px-4 py-2 backdrop-blur sm:px-6">
          <div className="flex items-center gap-2">
            <button className="grid h-10 w-10 place-items-center rounded-xl lg:hidden" aria-label="Open menu" onClick={() => setDrawer(true)}><Menu /></button>
            <div className="lg:hidden"><Logo compact /></div>
          </div>
          <div className="flex items-center gap-1">
            <Notifications />
            <div className="hidden text-right sm:block">
              <div className="text-sm font-semibold leading-tight">{user.full_name}</div>
              <div className="text-[11px] capitalize text-muted">{user.user_role === 'counselor' ? 'Counsellor' : user.user_role}</div>
            </div>
            <button className="grid h-10 w-10 place-items-center rounded-xl hover:bg-surface2" aria-label="Sign out" onClick={() => { logout(); nav('/login') }}><LogOut size={18} /></button>
          </div>
        </header>
        {user.is_synthetic && (
          <div className="bg-saffron-soft px-4 py-1.5 text-center text-xs font-medium text-saffron">Demo account — all data shown is synthetic.</div>
        )}
        <main className="mx-auto max-w-7xl px-4 pb-28 pt-6 sm:px-6 lg:pb-10">{children ?? <Outlet />}</main>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t border-line bg-surface pb-[env(safe-area-inset-bottom)] lg:hidden" aria-label="Quick">
        {MOBILE[user.user_role].map((to) => {
          const it = NAV.find((n) => n.to === to)!
          return (
            <NavLink key={to} to={to} end={to === '/'} className={({ isActive }) => clsx('flex min-h-[56px] flex-col items-center justify-center gap-0.5 text-[10px] font-semibold', isActive ? 'text-teal' : 'text-muted')}>
              <it.icon size={20} aria-hidden /> {it.label.replace('360° Wellness ', '').replace('Wellness ', '').replace(' / Counsellor Portal', '').split(' ')[0]}
            </NavLink>
          )
        })}
        <button onClick={() => setDrawer(true)} className="flex flex-col items-center justify-center gap-0.5 text-[10px] font-semibold text-muted"><Menu size={20} aria-hidden />More</button>
      </nav>
    </div>
  )
}
