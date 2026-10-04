<script lang="ts">
  import { goto } from '$app/navigation'
  import { ArrowLeft, MessageSquareText } from '@lucide/svelte'
  import StatusMark from '#lib/components/StatusMark.svelte'
  import Symbol from '#lib/components/Symbol.svelte'
  import DatasheetView from '#lib/components/views/DatasheetView.svelte'
  import InterlockView from '#lib/components/views/InterlockView.svelte'
  import MaintenanceView from '#lib/components/views/MaintenanceView.svelte'
  import OplView from '#lib/components/views/OplView.svelte'
  import PidRegisterView from '#lib/components/views/PidRegisterView.svelte'
  import { docTypeMeta } from '#lib/docTypes.ts'
  import type { PageProps } from './$types'

  let { data }: PageProps = $props()

  const doc = $derived(data.doc)
  const meta = $derived(doc ? docTypeMeta(doc.document_type) : null)
  const fields = $derived(
    doc
      ? ([
          ['Type', meta?.label ?? null, false],
          ['Document no.', doc.document_id, true],
          ['Equipment', doc.equipment_tag ? `${doc.equipment_tag}${doc.equipment_name ? ` ${doc.equipment_name}` : ''}` : null, false],
          ['Revision', doc.revision, true],
          ['Source file', doc.file_name, false],
        ] as [string, string | null, boolean][]).filter(([, v]) => v)
      : [],
  )
  const question = $derived(doc ? `Summarize document ${doc.document_id}${doc.equipment_tag ? ` for ${doc.equipment_tag}` : ''}` : '')
</script>

<button onclick={() => (history.length > 1 ? history.back() : goto('/repository'))} class="label mb-5 flex items-center gap-2 text-muted hover:text-ink">
  <ArrowLeft size={14} /> Back
</button>

{#if data.error || !doc || !meta}
  <p class="border border-danger bg-danger-wash p-4 text-sm text-danger-ink">{data.error ?? 'Document not found.'}</p>
{:else}
  <div class="flex flex-wrap items-start gap-x-6 gap-y-4">
    <Symbol name={meta.symbol} size={56} strokeWidth={1.25} class="shrink-0 text-shell" />
    <div class="min-w-0 flex-1 basis-64">
      <h1 class="text-[28px] font-bold leading-tight tracking-tight">{doc.title}</h1>
      <div class="mt-3"><StatusMark status={doc.status} /></div>
    </div>
    <a
      href="/chat?q={encodeURIComponent(question)}"
      class="flex shrink-0 items-center gap-2 border border-ink bg-panel px-4 py-2.5 text-sm font-semibold hover:bg-ground"
    >
      <MessageSquareText size={16} /> Ask Chatbot
    </a>
  </div>

  <dl class="mt-8 grid border-l border-t border-rule bg-panel sm:grid-cols-2">
    {#each fields as [k, v, mono] (k)}
      <div class="border-b border-r border-rule px-4 py-3">
        <dt class="label text-muted">{k}</dt>
        <dd class="mt-1 break-words {mono ? 'code font-medium' : 'text-[15px] font-medium'}">{v}</dd>
      </div>
    {/each}
  </dl>

  <div class="@container mt-10">
    {#if doc.structured}
      {@const st = doc.structured}
      {#if st.kind === 'datasheet'}<DatasheetView groups={st.groups} />
      {:else if st.kind === 'interlock'}<InterlockView trips={st.trips} permissives={st.permissives} />
      {:else if st.kind === 'pid'}<PidRegisterView rows={st.rows} />
      {:else if st.kind === 'maintenance'}<MaintenanceView events={st.events} />
      {:else if st.kind === 'opl'}<OplView header={st.header} sections={st.sections} />
      {:else if st.kind === 'plot_plan'}<DatasheetView groups={[{ category: 'Coordinates & location', rows: st.rows }]} />
      {/if}
    {/if}

    <details open={!doc.structured} class="group mt-8">
      <summary class="label cursor-pointer select-none py-2 text-muted hover:text-ink">Source text · {doc.chunks.length} parts</summary>
      <div class="mt-3 space-y-4">
        {#each doc.chunks as c (c.chunk_id)}
          <section id={c.chunk_id} class="border border-rule bg-panel">
            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 border-b border-rule bg-ground px-4 py-2">
              <span class="text-sm font-semibold">{c.title}</span>
              {#if c.page != null}<span class="code text-muted">p. {c.page}</span>{/if}
              {#if c.sheet}<span class="code text-muted">{c.sheet}</span>{/if}
            </div>
            <pre class="max-w-[75ch] whitespace-pre-wrap px-4 py-4 font-sans text-[15px] leading-relaxed">{c.content}</pre>
          </section>
        {/each}
      </div>
    </details>
  </div>
{/if}
