import { useQuery, type UseQueryOptions } from '@tanstack/react-query'
import { api } from '../services/api'

/** Query wrapper: lazy per-widget loading with polling for live data. */
export function useApi<T = any>(path: string | null, opts: { refetch?: number; staleTime?: number } & Partial<UseQueryOptions<T>> = {}) {
  const { refetch, staleTime, ...rest } = opts
  return useQuery<T>({
    queryKey: [path],
    queryFn: () => api.get<T>(path as string),
    enabled: !!path,
    refetchInterval: refetch,
    staleTime: staleTime ?? 20_000,
    retry: 1,
    ...rest,
  })
}

/** Query backed by a POST endpoint (e.g. the screener), keyed by body. */
export function usePostApi<T = any>(path: string, body: unknown, opts: { refetch?: number; enabled?: boolean } = {}) {
  return useQuery<T>({
    queryKey: [path, JSON.stringify(body)],
    queryFn: () => api.post<T>(path, body),
    refetchInterval: opts.refetch,
    enabled: opts.enabled ?? true,
    staleTime: 20_000,
    retry: 1,
  })
}
