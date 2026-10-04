<script lang="ts">
  import type { Permissive, Trip } from '#lib/api.ts'
  import Symbol from '../Symbol.svelte'
  import { isaParts } from '#lib/symbols.ts'

  let { trips, permissives }: { trips: Trip[]; permissives: Permissive[] } = $props()

  // Columns of the matrix are the distinct effects, in the order they first appear.
  const effects = $derived.by(() => {
    const seen = new Map<string, { target: string; kind: string; label: string }>()
    for (const t of trips)
      for (const e of t.effects) {
        const key = e.target ?? e.action
        if (!seen.has(key)) seen.set(key, { target: key, kind: e.kind, label: e.action.replace(/\s*\(EFF-\d+\)/, '') })
      }
    return [...seen.values()]
  })
  const hits = (t: Trip, target: string) => t.effects.some((e) => (e.target ?? e.action) === target)
  const kindSymbol: Record<string, string> = { pump: 'pump', compressor: 'compressor', valve: 'valve', control_valve: 'control_valve', system: 'system', other: 'other' }
</script>

<section class="border border-rule bg-panel">
  <h3 class="label bg-shell px-4 py-2.5 text-white">Cause-and-effect matrix</h3>
  <div class="scroll-thin overflow-x-auto">
    <table class="w-full min-w-[720px] border-collapse text-left">
      <thead>
        <tr class="border-b border-rule bg-ground align-bottom">
          <th class="label px-4 py-3 text-muted">Trip</th>
          <th class="label px-3 py-3 text-muted">Setpoint</th>
          <th class="label px-3 py-3 text-muted">Voting</th>
          {#each effects as e (e.target)}
            <th class="px-2 py-3 text-center" title={e.label}>
              <Symbol name={kindSymbol[e.kind] ?? 'other'} size={26} class="mx-auto text-shell" />
              <span class="code mt-1 block text-[11px] font-medium">{e.target}</span>
            </th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each trips as t (t.id ?? t.initiator)}
          {@const [fn, loop] = isaParts(t.initiator)}
          <tr class="border-b border-rule last:border-b-0">
            <th scope="row" class="px-4 py-3 font-normal">
              <span class="flex items-center gap-3">
                <span class="code inline-grid h-[18px] place-items-center rounded-xs bg-ink px-1 text-[11px] font-medium leading-none text-white">{t.id}</span>
                <span>
                  <span class="code block font-medium">{fn}-{loop}</span>
                  <span class="block max-w-[22ch] text-[12px] leading-tight text-muted">{t.description.replace(/\s*\(Setpoint.*$/, '')}</span>
                </span>
              </span>
            </th>
            <td class="code px-3 py-3">{t.setpoint ?? '-'}</td>
            <td class="code px-3 py-3">{t.voting ?? '-'}</td>
            {#each effects as e (e.target)}
              <td class="px-2 py-3 text-center">
                {#if hits(t, e.target)}
                  <span class="mx-auto block h-3 w-3 rotate-45 bg-ink" role="img" aria-label="{t.initiator} triggers {e.label}"></span>
                {:else}
                  <span class="text-muted-soft" aria-label="no effect">·</span>
                {/if}
              </td>
            {/each}
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</section>

{#if permissives.length > 0}
  <section class="mt-6 border border-rule bg-panel">
    <h3 class="label bg-shell px-4 py-2.5 text-white">Start permissives</h3>
    {#each permissives as p (p.id ?? p.source)}
      {@const [fn, loop] = isaParts(p.source)}
      <div class="grid grid-cols-[3rem_9rem_minmax(0,1fr)_4rem] items-center gap-3 border-b border-rule px-4 py-2.5 last:border-b-0">
        <span class="code inline-grid h-[18px] w-fit place-items-center rounded-xs bg-ink px-1 text-[11px] font-medium leading-none text-white">{p.id}</span>
        <span class="code font-medium">{fn}-{loop}</span>
        <span class="text-[15px]">{p.description.replace(/\s*\(Logic Gate.*$/, '')}</span>
        <span class="label text-right text-muted">{p.gate ?? ''}</span>
      </div>
    {/each}
  </section>
{/if}
