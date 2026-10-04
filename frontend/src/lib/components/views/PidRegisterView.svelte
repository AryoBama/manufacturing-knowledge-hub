<script lang="ts">
  import { isaParts } from '#lib/symbols.ts'

  type Row = { tag: string | null; instrument_type: string | null; description: string | null; setpoint: string; unit: string | null; function: string | null }
  let { rows }: { rows: Row[] } = $props()

  // Some values already embed their unit ("< 9 m³/h for 30s" with unit "m3/h"); don't print it twice.
  const norm = (v: string) => v.toLowerCase().replace(/³/g, '3')
  const showUnit = (r: Row) => !!r.unit && !norm(r.setpoint).includes(norm(r.unit))
</script>

<section class="border border-rule bg-panel">
  <h3 class="label bg-shell px-4 py-2.5 text-white">Instrument register</h3>
  <div class="scroll-thin overflow-x-auto">
    <table class="w-full min-w-[720px] border-collapse text-left">
      <thead>
        <tr class="border-b border-rule bg-ground">
          <th class="label px-4 py-2.5 text-muted">Tag</th>
          <th class="label px-3 py-2.5 text-muted">Type</th>
          <th class="label px-3 py-2.5 text-muted">Description</th>
          <th class="label px-3 py-2.5 text-muted">Setpoint</th>
          <th class="label px-3 py-2.5 text-muted">Function</th>
        </tr>
      </thead>
      <tbody>
        {#each rows as r, i (r.tag ?? i)}
          {@const [fn, loop] = r.tag ? isaParts(r.tag) : ['', '']}
          <tr class="border-b border-rule align-top last:border-b-0">
            <td class="px-4 py-3">
              <!-- ISA 5.1 bubble: function letters over loop number -->
              <span class="flex items-center gap-3">
                <svg viewBox="0 0 40 40" width="36" height="36" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true">
                  <circle cx="20" cy="20" r="17" /><path d="M3 20H37" />
                  <text x="20" y="17" font-size={fn.length > 3 ? 9 : 11} font-weight="600" text-anchor="middle" fill="currentColor" stroke="none">{fn}</text>
                  <text x="20" y="31" font-size="10" text-anchor="middle" fill="currentColor" stroke="none" class="font-mono">{loop}</text>
                </svg>
                <span class="code whitespace-nowrap font-medium">{r.tag ?? '-'}</span>
              </span>
            </td>
            <td class="px-3 py-3 text-[14px]">{r.instrument_type ?? '-'}</td>
            <td class="px-3 py-3 text-[14px]">{r.description ?? '-'}</td>
            <td class="code px-3 py-3 font-medium">{r.setpoint}{#if showUnit(r)}<span class="ml-1 font-normal text-muted">{r.unit}</span>{/if}</td>
            <td class="px-3 py-3 text-[14px] text-muted">{r.function ?? '-'}</td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</section>
