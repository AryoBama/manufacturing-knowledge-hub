<script lang="ts">
  import { ChevronDown, Lightbulb } from '@lucide/svelte'
  import { tick } from 'svelte'
  import { documentPath, type GeneratedAnswer, type SourceCitation } from '#lib/api.ts'
  import { typeCode } from '#lib/docTypes.ts'
  import StatusMark from './StatusMark.svelte'

  let { answer, messageId }: { answer: GeneratedAnswer; messageId: string } = $props()

  // Signal word: how far to trust this answer, stated before anything else (SDS convention).
  const signal = $derived.by(() => {
    if (answer.confidence === 'UNVERIFIED') return { word: 'Unverified', tone: 'danger' as const }
    if (answer.requires_clarification) return { word: 'Conflict: verify before use', tone: 'caution' as const }
    if (answer.confidence === 'LOW') return { word: 'Low confidence', tone: 'caution' as const }
    if (answer.confidence === 'MEDIUM') return { word: 'Partially verified', tone: 'caution' as const }
    return { word: 'Verified', tone: 'ok' as const }
  })
  const TONE = {
    ok: 'bg-shell text-white',
    caution: 'bg-caution text-ink',
    danger: 'bg-danger text-white',
  }
  const LEVEL: Record<string, string> = { HIGH: 'High', MEDIUM: 'Medium', LOW: 'Low', UNVERIFIED: 'Unverified' }

  const cites = $derived(answer.citations)
  const issued = $derived(
    answer.trace?.timestamp
      ? new Date(answer.trace.timestamp).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
      : null,
  )
  // Keep the last word and its reference chips on one line so chips never wrap alone.
  const split = (t: string) => {
    const i = t.lastIndexOf(' ')
    return i < 0 ? ['', t] : [t.slice(0, i + 1), t.slice(i + 1)]
  }
  const code = (c: SourceCitation, n: number) => `${typeCode(c.document_type)}${n}`

  // Points arrive as raw text lines ("  • foo", "  1. bar", "Heading:"); split into headings and claims.
  const lines = $derived(
    answer.detailed_points.map((raw, i) => {
      const text = raw.trim().replace(/^[•\-]\s*/, '').replace(/^\d+\.\s+/, '')
      return { text, heading: text.endsWith(':'), refs: answer.point_citations?.[i] ?? [] }
    }),
  )

  let active = $state<number | null>(null)
  let expanded = $state<Record<number, boolean>>({})

  async function goToCitation(n: number) {
    active = n
    expanded[n] = true
    await tick()
    document.getElementById(`cite-${messageId}-${n}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }

  const PRIORITY: Record<string, string> = { CRITICAL: 'Critical', HIGH: 'High', MEDIUM: 'Medium', LOW: 'Low' }
</script>

{#snippet marks(refs: number[])}
  {#each refs as n (n)}
    {@const c = cites[n - 1]}
    {#if c}
      <button
        onclick={() => goToCitation(n)}
        title="{c.document_id}{c.page != null ? ` · p. ${c.page}` : ''}"
        aria-label="Source {code(c, n)}: {c.document_id}"
        class="code ml-1.5 inline-grid h-[18px] -translate-y-px place-items-center rounded-xs px-1 align-middle text-[11px] font-medium leading-none hover:bg-shell {active === n ? 'bg-shell text-white ring-2 ring-ink ring-offset-1' : 'bg-ink text-white'}"
      >{code(c, n)}</button>
    {/if}
  {/each}
{/snippet}

<article class="@container border border-rule bg-panel" aria-label="Answer">
  <div class="flex items-center gap-3 px-4 py-2.5 {TONE[signal.tone]}">
    {#if signal.tone !== 'ok'}
      <span aria-hidden="true" class="grid h-5 w-5 shrink-0 rotate-45 place-items-center border-2 {signal.tone === 'danger' ? 'border-white' : 'border-ink'}">
        <span class="-rotate-45 text-[11px] font-bold leading-none">!</span>
      </span>
    {/if}
    <span class="label text-[13px]">{signal.word}</span>
    <span class="code ml-auto text-[12px]">{cites.length} {cites.length === 1 ? 'source' : 'sources'}</span>
  </div>

  <dl class="grid grid-cols-2 border-b border-rule @xl:grid-cols-[1.4fr_1fr_0.9fr_1.2fr]">
    <div class="border-b border-r border-rule px-4 py-2.5 @xl:border-b-0">
      <dt class="label text-muted">Equipment</dt>
      <dd class="mt-1 flex flex-wrap items-baseline gap-x-2 text-sm"><span class="code font-medium">{answer.equipment_tag ?? '-'}</span>{#if answer.equipment_name}<span class="text-muted">{answer.equipment_name}</span>{/if}</dd>
    </div>
    <div class="border-b border-rule px-4 py-2.5 @xl:border-b-0 @xl:border-r">
      <dt class="label text-muted">Intent</dt>
      <dd class="mt-1 text-sm capitalize">{answer.intent.replace(/_/g, ' ')}</dd>
    </div>
    <div class="border-b border-r border-rule px-4 py-2.5 @xl:border-b-0">
      <dt class="label text-muted">Confidence</dt>
      <dd class="mt-1 text-sm">{LEVEL[answer.confidence]}</dd>
    </div>
    <div class="border-b border-rule px-4 py-2.5 @xl:border-b-0">
      <dt class="label text-muted">ID kueri</dt>
      <dd class="code mt-1 break-all">{answer.query_id ?? '-'}</dd>
      {#if issued}<dd class="code text-[12px] text-muted">{issued}</dd>{/if}
    </div>
  </dl>

  <div class="px-4 py-4">
    {#if answer.requires_clarification && answer.clarification_prompt}
      <p class="mb-3 border border-caution bg-caution-wash p-3 text-sm text-caution-ink">{answer.clarification_prompt}</p>
    {/if}
    <p class="text-[17px] font-medium leading-snug text-ink">
      {split(answer.summary_answer)[0]}<span class="whitespace-nowrap">{split(answer.summary_answer)[1]}{@render marks(answer.summary_citations ?? [])}</span>
    </p>
    <p class="mt-1.5 text-[13px] text-muted">{answer.confidence_reason}</p>
  </div>

  {#if lines.length > 0}
    <div class="border-t border-rule">
      {#each lines as l, i (i)}
        {#if l.heading}
          <h3 class="label border-b border-rule bg-ground px-4 py-2 text-muted">{l.text.replace(/:$/, '')}</h3>
        {:else}
          <p class="border-b border-rule px-4 py-2.5 text-[15px] leading-snug last:border-b-0">{split(l.text)[0]}<span class="whitespace-nowrap">{split(l.text)[1]}{@render marks(l.refs)}</span></p>
        {/if}
      {/each}
    </div>
  {/if}

  {#if answer.recommendations.length > 0}
    <div class="border-t border-rule">
      <h3 class="label flex items-center gap-2 border-b border-rule bg-ground px-4 py-2 text-muted">
        <Lightbulb size={14} /> Recommended actions
      </h3>
      {#each answer.recommendations as r}
        <div class="grid gap-x-4 gap-y-1 border-b border-rule px-4 py-3 last:border-b-0 @xl:grid-cols-[6rem_1fr]">
          <span class="label pt-1 {r.priority === 'CRITICAL' || r.priority === 'HIGH' ? 'text-ink' : 'text-muted'}">
            {PRIORITY[r.priority] ?? r.priority}
          </span>
          <div>
            <p class="font-medium">{r.action}</p>
            <p class="text-sm text-muted">{r.basis}</p>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  {#if cites.length > 0}
    <div class="border-t border-rule">
      <h3 class="label bg-shell px-4 py-2.5 text-white">Sources</h3>
      <div role="table" aria-label="Sources">
        <div role="row" class="label hidden grid-cols-[4rem_minmax(0,1fr)_6rem_11rem_4rem_2rem] gap-3 border-b border-rule bg-ground px-4 py-2 text-muted @xl:grid">
          <span role="columnheader">Code</span><span role="columnheader">Document</span><span role="columnheader">Rev</span><span role="columnheader">Status</span><span role="columnheader">Page</span><span></span>
        </div>
        {#each cites as c, i (c.evidence_id + i)}
          {@const n = i + 1}
          <div id="cite-{messageId}-{n}" role="row" class="border-b border-rule last:border-b-0 {active === n ? 'bg-caution-wash' : ''}">
            <div class="grid grid-cols-[4rem_minmax(0,1fr)_2rem] items-center gap-x-3 gap-y-0.5 px-4 py-2.5 @xl:grid-cols-[4rem_minmax(0,1fr)_6rem_11rem_4rem_2rem]">
              <span role="cell"><span class="code inline-grid h-[18px] place-items-center rounded-xs bg-ink px-1 text-[11px] font-medium leading-none text-white">{code(c, n)}</span></span>
              <a role="cell" href={documentPath(c.document_id, answer.equipment_tag)} class="code min-w-0 truncate font-medium underline decoration-rule underline-offset-4 hover:decoration-ink" title={c.file_name}>{c.document_id}</a>
              <span role="cell" class="code hidden text-muted @xl:block">{c.revision ?? '-'}</span>
              <span role="cell" class="hidden @xl:block"><StatusMark status={c.status} /></span>
              <span role="cell" class="code hidden text-muted @xl:block">{c.page ?? '-'}</span>
              {#if c.excerpt}
                <button onclick={() => (expanded[n] = !expanded[n])} aria-label="Show excerpt {code(c, n)}" aria-expanded={!!expanded[n]} class="grid h-7 w-7 place-items-center text-muted hover:bg-ground hover:text-ink">
                  <ChevronDown size={16} class={expanded[n] ? 'rotate-180' : ''} />
                </button>
              {:else}<span></span>{/if}
              <p class="code col-span-3 text-[12px] text-muted @xl:hidden">{[c.revision, c.page != null ? `p. ${c.page}` : null, c.status].filter(Boolean).join(' · ')}</p>
            </div>
            {#if expanded[n] && c.excerpt}
              <p class="border-t border-rule bg-ground px-4 py-2.5 text-[13px] leading-relaxed text-muted">“{c.excerpt}”</p>
            {/if}
          </div>
        {/each}
      </div>
    </div>
  {/if}
</article>
