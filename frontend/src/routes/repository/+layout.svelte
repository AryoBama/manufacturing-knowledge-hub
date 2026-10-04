<script lang="ts">
  import { page } from '$app/state'
  import { ChevronRight, History, MessageSquareText } from '@lucide/svelte'
  import AppShell from '#lib/components/AppShell.svelte'
  import Brand from '#lib/components/Brand.svelte'
  import { DOC_TYPES } from '#lib/docTypes.ts'
  import type { LayoutData } from './$types'

  let { data, children }: { data: LayoutData; children: import('svelte').Snippet } = $props()

  let openTipe = $state(true)
  let openPlant = $state(true)

  const path = $derived(page.url.pathname)
  const count = (key: string) => data.docs.filter((d) => d.document_type === key).length
  const visibleTypes = $derived(DOC_TYPES.filter((t) => t.key !== 'OTHER' || count('OTHER') > 0))
  const link = (active: boolean) =>
    `flex items-center justify-between px-3 py-1.5 text-sm ${active ? 'bg-shell-2 font-semibold text-white' : 'text-shell-text hover:bg-shell-2 hover:text-white'}`
</script>

<AppShell>
  {#snippet sidebar()}
    <div class="flex h-full min-h-0 flex-col">
      <div class="space-y-3 p-4">
        <Brand />
        <a href="/chat" class="flex w-full items-center justify-center gap-2 bg-panel px-3 py-2.5 text-sm font-semibold text-ink hover:bg-ground">
          <MessageSquareText size={16} /> Open Chatbot
        </a>
        <a href="/failure-memory" class="flex w-full items-center gap-2 border border-white/25 px-3 py-2 text-sm text-white hover:bg-shell-2">
          <History size={18} strokeWidth={1.75} /> Failure Memory
        </a>
      </div>
      <div class="label px-4 pb-2 pt-3 text-shell-text">Repository Hierarchy</div>
      <nav class="scroll-thin min-h-0 flex-1 space-y-1 overflow-y-auto px-2 pb-4">
        <a href="/repository" class={link(path === '/repository')}>All Knowledge</a>

        <div>
          <button onclick={() => (openTipe = !openTipe)} aria-expanded={openTipe} class="label flex w-full items-center gap-2 px-3 py-2.5 text-white">
            <ChevronRight size={14} class="transition {openTipe ? 'rotate-90' : ''}" /> Document Types
          </button>
          {#if openTipe}
            <div class="ml-4 border-l border-white/20 pl-1">
              {#each visibleTypes as t (t.key)}
                <a href="/repository/type/{t.key}" class={link(path === `/repository/type/${t.key}`)}>
                  <span>{t.label}</span><span class="code text-[12px]">{count(t.key)}</span>
                </a>
              {/each}
            </div>
          {/if}
        </div>

        <div>
          <button onclick={() => (openPlant = !openPlant)} aria-expanded={openPlant} class="label flex w-full items-center gap-2 px-3 py-2.5 text-white">
            <ChevronRight size={14} class="transition {openPlant ? 'rotate-90' : ''}" /> Plant
          </button>
          {#if openPlant}
            <div class="ml-4 border-l border-white/20 pl-1">
              {#each data.plant.areas as a (a.area)}
                <a href="/repository/plant/{a.area}" class={link(path === `/repository/plant/${a.area}`)}>Area {a.area}</a>
                {#if path.startsWith(`/repository/plant/${a.area}`)}
                  <div class="ml-3 border-l border-white/20 pl-1">
                    {#each a.equipment as e (e.tag)}
                      <a href="/repository/plant/{a.area}/{e.tag}" class={link(path === `/repository/plant/${a.area}/${e.tag}`)}>
                        <span class="code text-[13px]">{e.tag}</span><span class="code text-[12px]">{e.document_count}</span>
                      </a>
                    {/each}
                  </div>
                {/if}
              {/each}
            </div>
          {/if}
        </div>
      </nav>
    </div>
  {/snippet}

  <main class="scroll-thin min-h-0 min-w-0 flex-1 overflow-y-auto">
    <div class="mx-auto max-w-5xl px-4 py-6 md:px-8 md:py-10">
      {#if data.error}
        <p class="border border-danger bg-danger-wash p-4 text-sm text-danger-ink">Could not load the repository: {data.error}. Make sure the backend is running on port 8000.</p>
      {:else}
        {@render children()}
      {/if}
    </div>
  </main>
</AppShell>
