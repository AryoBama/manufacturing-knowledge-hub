import { createApi } from '#lib/api.ts'
import type { PageLoad } from './$types'

export const load: PageLoad = async ({ params, fetch }) => {
  try {
    return { equipment: await createApi(fetch).equipment(params.tag), equipmentError: null as string | null }
  } catch (e) {
    return { equipment: null, equipmentError: e instanceof Error ? e.message : String(e) }
  }
}
