import { useCallback, useEffect, useState } from 'react'
import { api } from './api'

export function useApi<T>(path: string | null, deps: unknown[] = []) {
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(!!path)
  const load = useCallback(async () => {
    if (!path) { setLoading(false); return }
    setLoading(true); setError(null)
    try { setData(await api<T>(path)) } catch (e: any) { setError(e.message) } finally { setLoading(false) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, ...deps])
  useEffect(() => { load() }, [load])
  return { data, error, loading, reload: load, setData }
}

export function useTheme() {
  const read = () => { try { return localStorage.getItem('swasti.theme.v2') === 'dark' ? 'dark' : 'light' } catch { return 'light' } }
  const [theme, setThemeState] = useState<string>(read)
  useEffect(() => {
    const root = document.documentElement
    root.setAttribute('data-theme', theme)
    try { localStorage.setItem('swasti.theme.v2', theme) } catch { /* ignore */ }
  }, [theme])
  return [theme, setThemeState] as const
}
