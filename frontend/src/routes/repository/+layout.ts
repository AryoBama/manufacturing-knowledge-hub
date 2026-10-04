import { createApi } from '#lib/api.ts'
import type { LayoutLoad } from './$types'

export const load: LayoutLoad = async ({ fetch }) => {
  const api = createApi(fetch)
  try {
    const [docs, plant] = await Promise.all([api.documents(), api.plant()])
    return { docs, plant, error: null as string | null }
  } catch (e) {
    return { docs: [], plant: { plant: '', areas: [] }, error: e instanceof Error ? e.message : String(e) }
  }
}
