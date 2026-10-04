<script lang="ts">
  import type { FailureModeFrequency } from '#lib/api.ts'

  let { modes }: { modes: FailureModeFrequency[] } = $props()
  const max = $derived(Math.max(1, ...modes.map((m) => m.count)))
</script>

<!-- One series, one hue: the bar length is the count, so identity needs no legend. Values sit beside each bar. -->
<ul class="divide-y divide-rule">
  {#each modes as m (m.failure_mode)}
    <li class="grid grid-cols-[minmax(0,1fr)_3.5rem] items-center gap-x-4 gap-y-1.5 px-4 py-3 @2xl:grid-cols-[minmax(0,16rem)_minmax(0,1fr)_5rem]" title="{m.failure_mode}: {m.count} (work orders {m.sample_event_ids.join(', ')})">
      <span class="text-[14px] leading-snug">{m.failure_mode}</span>
      <span class="code text-right text-[14px] font-medium @2xl:order-3">{m.count}<span class="ml-1.5 text-[12px] font-normal text-muted">{Math.round(m.percentage)}%</span></span>
      <span class="col-span-2 h-2.5 bg-ground @2xl:order-2 @2xl:col-span-1" role="img" aria-label="{m.count} of {max} max">
        <span class="block h-full bg-shell" style="width: {(m.count / max) * 100}%"></span>
      </span>
    </li>
  {/each}
</ul>
