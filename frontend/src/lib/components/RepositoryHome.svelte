<script lang="ts">
  import { goto } from '$app/navigation'
  import { page } from '$app/state'
  import { Search } from '@lucide/svelte'
  import type { DocumentSummary, PlantTree } from '#lib/api.ts'
  import { DOC_TYPES } from '#lib/docTypes.ts'
  import DocumentList from './DocumentList.svelte'
  import Symbol from './Symbol.svelte'

  let { docs, plant, areaCode }: { docs: DocumentSummary[]; plant: PlantTree; areaCode?: string } = $props()

  const q = $derived(page.url.searchParams.get('q') ?? '')
  const query = $derived(q.trim().toLowerCase())
  const view = $derived<'type' | 'plant'>(areaCode || page.url.searchParams.get('view') === 'plant' ? 'plant' : 'type')
  const area = $derived(plant.areas.find((a) => a.area === areaCode))
  const areaLabel = $derived(area && area.name !== `Area ${area.area}` ? area.name : null)

  const results = $derived(
    query
      ? docs.filter((d) =>
          [d.title, d.document_id, d.equipment_tag, d.equipment_name, d.document_type].some((f) => f?.toLowerCase().includes(query)),
        )
      : [],
  )

  function setView(v: 'type' | 'plant') {
    void goto(v === 'plant' ? '/repository?view=plant' : '/repository')
  }

  function setQuery(value: string) {
    const params = new URLSearchParams(page.url.search)
    if (value) params.set('q', value)
    else params.delete('q')
    const qs = params.toString()
    void goto(`${page.url.pathname}${qs ? `?${qs}` : ''}`, { replaceState: true })
  }
</script>

<div>
  <div class="flex flex-wrap items-end justify-between gap-x-6 gap-y-4">
    <div>
      <h1 class="text-[32px] font-bold leading-tight tracking-tight">{area ? `Area ${area.area}` : 'Knowledge Repository'}</h1>
      {#if areaLabel}<p class="mt-1 text-muted">{areaLabel}</p>{/if}
    </div>
    <div class="flex w-full flex-wrap items-center gap-3 sm:w-auto">
      <div class="inline-flex border border-ink text-sm" role="group" aria-label="View">
        {#each ['type', 'plant'] as const as v}
          <button
            onclick={() => setView(v)}
            aria-pressed={view === v}
            class="label px-4 py-2.5 {view === v ? 'bg-shell text-white' : 'bg-panel text-ink hover:bg-ground'}"
          >{v}</button>
        {/each}
      </div>
      <label class="flex min-w-0 flex-1 items-center gap-2 border border-ink bg-panel px-3 py-2 text-sm focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ink sm:w-72 sm:flex-none">
        <Search size={16} class="shrink-0 text-muted" />
        <input value={q} oninput={(e) => setQuery(e.currentTarget.value)} aria-label="Search documents or tags" placeholder="Search documents or tags…" class="w-full bg-transparent outline-none" />
      </label>
    </div>
  </div>

  <div class="@container mt-8">
    {#if query}
      <p class="label mb-3 text-muted">{results.length} {results.length === 1 ? 'document' : 'documents'} found</p>
      <DocumentList docs={results} empty="No matching documents." />
    {:else if view === 'type'}
      <div class="grid border-l border-t border-rule @xl:grid-cols-2 @3xl:grid-cols-3">
        {#each DOC_TYPES.filter((t) => t.key !== 'OTHER' || docs.some((d) => d.document_type === 'OTHER')) as t (t.key)}
          {@const n = docs.filter((d) => d.document_type === t.key).length}
          <a href="/repository/type/{t.key}" class="group flex min-h-48 flex-col border-b border-r border-rule bg-panel p-5 hover:bg-shell hover:text-white">
            <Symbol name={t.symbol} size={48} strokeWidth={1.25} class="{n === 0 ? 'text-muted-soft' : 'text-shell'} group-hover:text-white" />
            <h2 class="mt-5 text-lg font-semibold leading-tight {n === 0 ? 'text-muted' : ''} group-hover:text-white">{t.label}</h2>
            <p class="mt-1 flex-1 text-sm text-muted group-hover:text-shell-text">{t.description}</p>
            <p class="label mt-4 text-muted group-hover:text-shell-text">{n > 0 ? `${n} ${n === 1 ? 'document' : 'documents'}` : 'No documents yet'}</p>
          </a>
        {/each}
      </div>
    {:else if area}
      <div class="grid border-l border-t border-rule @xl:grid-cols-2 @3xl:grid-cols-3">
        {#each area.equipment as e (e.tag)}
          <a href="/repository/plant/{area.area}/{e.tag}" class="group flex min-h-40 flex-col border-b border-r border-rule bg-panel p-5 hover:bg-shell hover:text-white">
            <h2 class="code text-lg font-medium">{e.tag}</h2>
            <p class="mt-3 font-semibold">{e.name}</p>
            <p class="mt-1 flex-1 text-sm text-muted group-hover:text-shell-text">{e.type}</p>
            <p class="label mt-4 text-muted group-hover:text-shell-text">{e.document_count > 0 ? `${e.document_count} ${e.document_count === 1 ? 'document' : 'documents'}` : 'No documents yet'}</p>
          </a>
        {/each}
      </div>
    {:else}
      <div class="grid border-l border-t border-rule @xl:grid-cols-2 @3xl:grid-cols-3">
        {#each plant.areas as a (a.area)}
          {@const n = a.equipment.reduce((s, e) => s + e.document_count, 0)}
          <a href="/repository/plant/{a.area}" class="group flex min-h-40 flex-col border-b border-r border-rule bg-panel p-5 hover:bg-shell hover:text-white">
            <h2 class="text-lg font-semibold">Area {a.area}</h2>
            {#if a.name !== `Area ${a.area}`}<p class="mt-2 text-sm text-muted group-hover:text-shell-text">{a.name}</p>{/if}
            <p class="label mt-auto pt-4 text-muted group-hover:text-shell-text">{a.equipment.length} equipment · {n} {n === 1 ? 'document' : 'documents'}</p>
          </a>
        {/each}
      </div>
    {/if}
  </div>
</div>
