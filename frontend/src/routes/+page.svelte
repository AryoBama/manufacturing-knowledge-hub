<script lang="ts">
  import Symbol from '#lib/components/Symbol.svelte'
  import { APP_NAME } from '#lib/config.ts'
  import type { PageProps } from './$types'

  let { data }: PageProps = $props()

  const ENTRIES = [
    {
      href: '/chat',
      symbol: 'bubble-qa',
      title: 'Chatbot',
      subtitle: 'Technical Q&A',
      description: 'Ask questions about plant equipment. Every answer carries source codes you can trace back to the document.',
    },
    {
      href: '/repository',
      symbol: 'sheets',
      title: 'Knowledge Repository',
      subtitle: 'Browse documents',
      description: 'Browse SOPs, datasheets, P&IDs, interlocks and maintenance history by type or by plant.',
    },
    {
      href: '/failure-memory',
      symbol: 'history',
      title: 'Failure Memory',
      subtitle: 'Learn from past incidents',
      description: 'Search similar past failures by symptom, with the root causes and fixes that worked.',
    },
  ]
  const totals = $derived(
    data.totals
      ? [
          { label: 'Documents', value: data.totals.documents, alert: false },
          { label: 'Final', value: data.totals.final, alert: false },
          { label: 'Not final', value: data.totals.notFinal, alert: data.totals.notFinal > 0 },
          { label: 'Equipment', value: data.totals.equipment, alert: false },
        ]
      : [],
  )
</script>

<main class="mx-auto flex min-h-full w-full max-w-5xl flex-col justify-center px-6 py-14 md:py-20">
  <h1 class="max-w-3xl text-[32px] font-bold leading-[1.1] tracking-tight md:text-[44px]">
    Welcome to <span class="text-shell md:whitespace-nowrap">{APP_NAME}</span>
  </h1>
  <p class="mt-4 max-w-xl text-[17px] text-muted">One place for petrochemical plant operating knowledge.</p>

  <div class="@container mt-12 grid border-l border-t border-ink md:grid-cols-3">
    {#each ENTRIES as { href, symbol, title, subtitle, description } (href)}
      <a {href} class="group flex min-h-80 flex-col border-b border-r border-ink bg-panel p-7 hover:bg-shell hover:text-white">
        <Symbol name={symbol} size={84} strokeWidth={1.1} class="text-shell group-hover:text-white" />
        <h2 class="mt-12 text-[24px] font-bold leading-tight">{title}</h2>
        <p class="mt-1 text-[17px] font-medium">{subtitle}</p>
        <p class="mt-3 max-w-sm text-[15px] text-muted group-hover:text-shell-text">{description}</p>
      </a>
    {/each}
  </div>

  {#if totals.length}
    <dl class="mt-px grid grid-cols-2 border-x border-b border-ink bg-panel sm:grid-cols-4">
      {#each totals as t (t.label)}
        <div class="border-r border-rule px-4 py-3 last:border-r-0 max-sm:border-b max-sm:[&:nth-child(2)]:border-r-0 max-sm:[&:nth-child(n+3)]:border-b-0">
          <dt class="label text-muted">{t.label}</dt>
          <dd class="code mt-1 flex items-center gap-2 text-[22px] font-medium">
            {#if t.alert}<span aria-hidden="true" class="h-3 w-3 rotate-45 bg-caution"></span>{/if}{t.value}
          </dd>
        </div>
      {/each}
    </dl>
  {/if}
</main>
