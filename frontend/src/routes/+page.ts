import { createApi } from '#lib/api.ts'
import type { PageLoad } from './$types'

const FINAL = ['Issued for Operation', 'Approved']

// Live totals for the landing strip; the page still renders if the backend is down.
export const load: PageLoad = async ({ fetch }) => {
  try {
    const api = createApi(fetch)
    const [docs, plant] = await Promise.all([api.documents(), api.plant()])
    const final = docs.filter((d) => FINAL.includes(d.status ?? '')).length
    return {
      totals: {
        documents: docs.length,
        final,
        notFinal: docs.length - final,
        equipment: plant.areas.reduce((n, a) => n + a.equipment.length, 0),
      },
    }
  } catch {
    return { totals: null }
  }
}
