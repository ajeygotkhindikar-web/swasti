const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? '/api'
const TOKEN_KEY = 'swasti.token'

export function getToken(): string | null {
  try { return sessionStorage.getItem(TOKEN_KEY) } catch { return null }
}
export function setToken(t: string | null) {
  try { t ? sessionStorage.setItem(TOKEN_KEY, t) : sessionStorage.removeItem(TOKEN_KEY) } catch { /* storage unavailable */ }
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}

export async function api<T = any>(path: string, opts: { method?: string; body?: unknown; raw?: boolean } = {}): Promise<T> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  if (opts.body !== undefined) headers['Content-Type'] = 'application/json'
  const res = await fetch(BASE + path, { method: opts.method ?? 'GET', headers, body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined })
  if (res.status === 401 && token) { setToken(null); window.location.assign('/login') }
  if (!res.ok) {
    let msg = res.statusText
    try { const j = await res.json(); msg = typeof j.detail === 'string' ? j.detail : JSON.stringify(j.detail) } catch { /* ignore */ }
    throw new ApiError(res.status, msg)
  }
  if (opts.raw) return res as unknown as T
  return res.status === 204 ? (undefined as T) : res.json()
}

export async function downloadPdf(path: string, filename: string) {
  const res = await api<Response>(path, { raw: true })
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  setTimeout(() => URL.revokeObjectURL(url), 2000)
}
