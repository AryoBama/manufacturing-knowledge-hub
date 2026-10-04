import { createApi } from '#lib/api.ts'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ params, url, fetch }) => {
  const api = createApi(fetch)
  try {
    return { doc: await api.document(params.documentId, url.searchParams.get('tag')), error: null as string | null }
  } catch (e) {
    return { doc: null, error: e instanceof Error ? e.message : String(e) }
  }
}
