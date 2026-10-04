<script lang="ts">
  import { documentPath, type DocumentSummary } from '#lib/api.ts'
  import StatusMark from './StatusMark.svelte'

  let { docs, empty = 'No documents yet.', showTag = true }: { docs: DocumentSummary[]; empty?: string; showTag?: boolean } = $props()

  // Final documents first, anything not final floats below them so it cannot be missed.
  const RANK: Record<string, number> = { 'Issued for Operation': 0, Approved: 1 }
  const sorted = $derived(
    [...docs].sort(
      (a, b) =>
        (RANK[a.status ?? ''] ?? 2) - (RANK[b.status ?? ''] ?? 2) ||
        (a.equipment_tag ?? '').localeCompare(b.equipment_tag ?? '') ||
        a.document_id.localeCompare(b.document_id),
    ),
  )
  const cols = $derived(
    showTag
      ? '@4xl:grid-cols-[minmax(0,11rem)_minmax(0,12rem)_minmax(0,1fr)_6.5rem_4.5rem]'
      : '@4xl:grid-cols-[minmax(0,11rem)_minmax(0,12rem)_minmax(0,1fr)_4.5rem]',
  )
</script>

{#if docs.length === 0}
  <p class="border border-dashed border-rule p-8 text-center text-sm text-muted">{empty}</p>
{:else}
  <div class="@container"><div role="table" aria-label="Document list" class="border border-rule bg-panel">
    <div role="row" class="label hidden gap-4 bg-shell px-4 py-2.5 text-white @4xl:grid {cols}">
      <span role="columnheader">Status</span>
      <span role="columnheader">Document no.</span>
      <span role="columnheader">Title</span>
      {#if showTag}<span role="columnheader">Tag</span>{/if}
      <span role="columnheader">Rev</span>
    </div>
    {#each sorted as d (d.document_id + '@' + d.equipment_tag)}
      <a
        role="row"
        href={documentPath(d.document_id, d.equipment_tag)}
        class="grid gap-x-4 gap-y-1 border-b border-rule px-4 py-3 last:border-b-0 hover:bg-ground @4xl:items-center {cols}"
      >
        <span role="cell"><StatusMark status={d.status} /></span>
        <span role="cell" class="code truncate text-ink" title={d.document_id}>{d.document_id}</span>
        <span role="cell" class="min-w-0 text-[15px] font-medium">{d.title}</span>
        <span class="flex gap-4 @4xl:contents">
          {#if showTag}<span role="cell" class="code text-muted">{d.equipment_tag ?? '-'}</span>{/if}
          <span role="cell" class="code text-muted">{d.revision ?? '-'}</span>
        </span>
      </a>
    {/each}
  </div>
  </div>
{/if}
