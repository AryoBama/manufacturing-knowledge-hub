import { createApi } from '#lib/api.ts'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ url, fetch }) => {
  const api = createApi(fetch)
  const tag = url.searchParams.get('tag')
  const q = (url.searchParams.get('q') ?? '').trim()
  try {
    const plant = await api.plant()
    const pattern = tag ? await api.failurePatterns(tag) : null
    const report = tag && q ? await api.failureSearch(q, tag) : null
    return { plant, tag, q, pattern, report, error: null as string | null }
  } catch (e) {
    return { plant: null, tag, q, pattern: null, report: null, error: e instanceof Error ? e.message : String(e) }
  }
}
