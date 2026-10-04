<script lang="ts">
  import { goto } from '$app/navigation'
  import { navigating } from '$app/state'
  import { MessageSquareText, Search } from '@lucide/svelte'
  import AppShell from '#lib/components/AppShell.svelte'
  import FailureModeBars from '#lib/components/FailureModeBars.svelte'
  import FailureSidebar from '#lib/components/FailureSidebar.svelte'
  import { documentPath, type SimilarFailureCase } from '#lib/api.ts'
  import type { PageProps } from './$types'

  let { data }: PageProps = $props()

  const equipment = $derived(data.plant?.areas.flatMap((a) => a.equipment) ?? [])
  const selectable = $derived(equipment.filter((e) => e.maintenance_events > 0))
  const current = $derived(equipment.find((e) => e.tag === data.tag) ?? null)

  // Writable derived: follows the URL, but the form can edit it before submitting.
  let tag = $derived(data.tag ?? '')
  let query = $derived(data.q)

  const EXAMPLES = ['Mechanical seal leaking', 'High bearing vibration', 'Low suction pressure trip', 'High discharge temperature']

  function search(e: Event) {
    e.preventDefault()
    if (!tag) return
    const params = new URLSearchParams({ tag })
    if (query.trim()) params.set('q', query.trim())
    void goto(`/failure-memory?${params}`)
  }

  // The same incident can be recorded under two work-order IDs. Merge those for display, keeping every ID visible.
  type Case = SimilarFailureCase & { alsoRecordedAs: string[] }
  const cases = $derived.by<Case[]>(() => {
    const merged = new Map<string, Case>()
    for (const c of data.report?.similar_cases ?? []) {
      const key = `${c.date}|${c.symptom}|${c.failure_mode}`
      const hit = merged.get(key)
      if (hit) hit.alsoRecordedAs.push(c.event_id)
      else merged.set(key, { ...c, alsoRecordedAs: [] })
    }
    return [...merged.values()]
  })

  const pattern = $derived(data.report?.pattern_summary ?? data.pattern)
  const rca = $derived(data.report?.rca_insights ?? null)
  const fmtDate = (d: string) => new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
  const eventLink = (id: string, t: string) => `${documentPath('SAP-PM-HIST', t)}#${id}`
  const askChat = $derived(`Which past failures on ${data.tag} match: "${data.q}"? Cite the work orders.`)
  const noData = $derived(!!data.tag && !!pattern && pattern.total_maintenance_records === 0)
</script>

<AppShell>
  {#snippet sidebar()}<FailureSidebar {equipment} activeTag={data.tag} />{/snippet}

  <main class="scroll-thin min-h-0 min-w-0 flex-1 overflow-y-auto">
    <div class="@container mx-auto max-w-5xl px-4 py-6 md:px-8 md:py-10">
      <h1 class="text-[32px] font-bold leading-tight tracking-tight">Failure Memory</h1>
      <p class="mt-1 max-w-2xl text-muted">Search past incidents by symptom, then see how often each failure mode occurred and which fixes worked.</p>

      <p class="mt-5 border border-ink bg-panel px-4 py-3 text-[14px]">
        <span class="font-semibold">Historical evidence is not a diagnosis.</span>
        These records show what happened before, not the current condition of the equipment.
      </p>

      {#if data.error}
        <p class="mt-6 border border-danger bg-danger-wash p-4 text-sm text-danger-ink">Could not load failure memory: {data.error}. Make sure the backend is running on port 8000.</p>
      {:else}
        <form onsubmit={search} class="mt-6 border border-ink bg-panel">
          <div class="grid @2xl:grid-cols-[18rem_minmax(0,1fr)_auto]">
            <label class="border-b border-ink px-4 py-2.5 @2xl:border-b-0 @2xl:border-r">
              <span class="label text-muted">Equipment</span>
              <select bind:value={tag} required class="mt-1 w-full bg-transparent text-[15px] font-medium outline-none">
                <option value="" disabled>Select equipment…</option>
                {#each selectable as e (e.tag)}<option value={e.tag}>{e.tag} · {e.name}</option>{/each}
              </select>
            </label>
            <label class="border-b border-ink px-4 py-2.5 @2xl:border-b-0 @2xl:border-r">
              <span class="label text-muted">Symptom or alarm</span>
              <input bind:value={query} placeholder="e.g. hexane leaking from seal gland" class="mt-1 w-full bg-transparent text-[15px] outline-none" />
            </label>
            <button type="submit" disabled={!tag} class="flex items-center justify-center gap-2 bg-shell px-6 py-3 text-sm font-semibold text-white hover:bg-shell-2 disabled:border-l disabled:border-rule disabled:bg-ground disabled:text-muted">
              <Search size={16} /> Search
            </button>
          </div>
          <div class="flex flex-wrap items-center gap-2 border-t border-rule px-4 py-2.5">
            <span class="label text-muted">Try</span>
            {#each EXAMPLES as ex}
              <button type="button" onclick={() => (query = ex)} class="border border-rule px-2.5 py-1 text-[13px] hover:border-ink hover:bg-ground">{ex}</button>
            {/each}
          </div>
        </form>

        <div aria-live="polite">
          {#if navigating.to}
            <p class="label motion-safe:animate-pulse mt-8 text-muted">Searching past incidents…</p>
          {/if}
        </div>

        {#if !data.tag}
          <p class="mt-8 border border-dashed border-rule p-8 text-center text-[15px] text-muted">Select equipment to see its failure profile, then describe a symptom to find similar past incidents.</p>
        {:else if noData}
          <p class="mt-8 border border-dashed border-rule p-8 text-center text-[15px] text-muted">No maintenance records are loaded for <span class="code">{data.tag}</span>.</p>
        {:else}
          {#if data.report}
            <section class="mt-8">
              <div class="flex flex-wrap items-end justify-between gap-3">
                <h2 class="label text-muted">Similar past incidents on <span class="code text-ink">{data.tag}</span> · {cases.length}</h2>
                <a href="/chat?q={encodeURIComponent(askChat)}" class="flex items-center gap-2 border border-ink bg-panel px-3 py-1.5 text-[13px] font-semibold hover:bg-ground"><MessageSquareText size={14} /> Ask Chatbot about this</a>
              </div>

              {#if !data.report.has_historical_precedent || cases.length === 0}
                <p class="mt-3 border border-dashed border-rule p-6 text-[15px] text-muted">No similar incident on record for “{data.q}”. That does not mean it has never happened: check the failure modes below and the maintenance history.</p>
              {:else}
                <ol class="mt-3 border border-rule bg-panel">
                  {#each cases as c (c.event_id)}
                    <li class="grid gap-x-6 gap-y-2 border-b border-rule px-4 py-4 last:border-b-0 @2xl:grid-cols-[7.5rem_minmax(0,1fr)]">
                      <div>
                        <p class="label text-muted">Text match</p>
                        <p class="code mt-1 text-[18px] font-medium">{c.similarity_score.toFixed(2)}</p>
                        <span class="mt-1 block h-1.5 bg-ground" role="img" aria-label="similarity {c.similarity_score.toFixed(2)} of 1"><span class="block h-full bg-ink" style="width: {c.similarity_score * 100}%"></span></span>
                      </div>
                      <div class="space-y-1.5 text-[15px]">
                        <p class="flex flex-wrap items-baseline gap-x-3">
                          <span class="code font-medium">{fmtDate(c.date)}</span>
                          <a href={eventLink(c.event_id, c.equipment_tag)} class="code underline decoration-rule underline-offset-4 hover:decoration-ink">{c.event_id}</a>
                          {#each c.alsoRecordedAs as other}<a href={eventLink(other, c.equipment_tag)} class="code text-[12px] text-muted underline decoration-rule underline-offset-4 hover:decoration-ink">also {other}</a>{/each}
                        </p>
                        {#if c.failure_mode}<p class="text-[17px] font-semibold leading-snug">{c.failure_mode}</p>{/if}
                        <p><span class="label mr-1 text-muted">Symptom</span>{c.symptom ?? '-'}</p>
                        <p><span class="label mr-1 text-muted">Root cause</span>{c.root_cause ?? '-'}</p>
                        <p><span class="label mr-1 text-muted">Action</span>{c.corrective_action ?? '-'}</p>
                        {#if c.parts_replaced.length}<p class="code text-[12px] text-muted">parts: {c.parts_replaced.join(', ')}</p>{/if}
                      </div>
                    </li>
                  {/each}
                </ol>
                <p class="mt-2 text-[12px] text-muted">Text match is a word-overlap score from 0 to 1. It ranks records by wording, not by likelihood of being the cause.</p>
              {/if}
            </section>

            {#if rca && (rca.root_causes.length || rca.proven_actions.length)}
              <section class="mt-8 grid gap-6 @3xl:grid-cols-2">
                <div class="border border-rule bg-panel">
                  <h3 class="label bg-shell px-4 py-2.5 text-white">Root causes seen</h3>
                  <ul class="divide-y divide-rule">{#each rca.root_causes as r}<li class="px-4 py-2.5 text-[15px] leading-snug">{r}</li>{/each}</ul>
                </div>
                <div class="border border-rule bg-panel">
                  <h3 class="label bg-shell px-4 py-2.5 text-white">Fixes that worked</h3>
                  <ul class="divide-y divide-rule">{#each rca.proven_actions as a}<li class="px-4 py-2.5 text-[15px] leading-snug">{a}</li>{/each}</ul>
                </div>
                {#if rca.reference_work_orders.length || rca.replacement_parts_used.length}
                  <p class="code text-[12px] text-muted @3xl:col-span-2">
                    {#if rca.reference_work_orders.length}Work orders: {#each rca.reference_work_orders as w, i}<a href={eventLink(w, data.tag ?? '')} class="underline decoration-rule underline-offset-4 hover:decoration-ink">{w}</a>{i < rca.reference_work_orders.length - 1 ? ', ' : ''}{/each}{/if}
                    {#if rca.replacement_parts_used.length} · Parts used: {rca.replacement_parts_used.join(', ')}{/if}
                  </p>
                {/if}
              </section>
            {/if}
          {/if}

          {#if pattern && pattern.total_maintenance_records > 0}
            <section class="mt-10">
              <h2 class="label mb-3 text-muted">Failure profile · <span class="code text-ink">{data.tag}</span>{current ? ` · ${current.name}` : ''}</h2>
              <div class="border border-rule bg-panel">
                <dl class="grid grid-cols-2 border-b border-rule @xl:grid-cols-4">
                  <div class="border-b border-r border-rule px-4 py-3 @xl:border-b-0"><dt class="label text-muted">Work orders</dt><dd class="code mt-1 text-[22px] font-medium">{pattern.total_maintenance_records}</dd></div>
                  <div class="border-b border-rule px-4 py-3 @xl:border-b-0 @xl:border-r"><dt class="label text-muted">Failures</dt><dd class="code mt-1 flex items-center gap-2 text-[22px] font-medium">{#if pattern.failure_count}<span aria-hidden="true" class="h-3 w-3 rotate-45 bg-caution"></span>{/if}{pattern.failure_count}</dd></div>
                  <div class="border-r border-rule px-4 py-3"><dt class="label text-muted">Downtime</dt><dd class="code mt-1 text-[22px] font-medium">{pattern.total_downtime_hours.toFixed(1)}<span class="ml-1 text-[13px] font-normal text-muted">h</span></dd></div>
                  <div class="px-4 py-3"><dt class="label text-muted">Failures recorded</dt><dd class="code mt-1 text-[14px] leading-snug">{pattern.earliest_record_date ? fmtDate(pattern.earliest_record_date) : '-'}<br />to {pattern.latest_record_date ? fmtDate(pattern.latest_record_date) : '-'}</dd></div>
                </dl>
                <h3 class="label border-b border-rule bg-ground px-4 py-2 text-muted">Failure modes by occurrences</h3>
                <FailureModeBars modes={pattern.top_failure_modes} />
              </div>
              <p class="mt-2 text-[12px] text-muted">Failure-mode names come from the maintenance records and the backend's classifier. Some labels are broad.</p>
            </section>
          {/if}
        {/if}
      {/if}
    </div>
  </main>
</AppShell>
