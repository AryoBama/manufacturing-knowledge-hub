<script lang="ts">
  import type { MaintenanceEvent } from '#lib/api.ts'

  let { events }: { events: MaintenanceEvent[] } = $props()

  const failures = $derived(events.filter((e) => e.failure_occurred))
  const downtime = $derived(events.reduce((n, e) => n + (e.downtime_hours ?? 0), 0))
  let onlyFailures = $state(false)
  const shown = $derived(onlyFailures ? failures : events)
  const fmt = (d: string) => new Date(d).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
</script>

<section class="border border-rule bg-panel">
  <h3 class="label bg-shell px-4 py-2.5 text-white">Maintenance history</h3>
  <dl class="grid grid-cols-3 border-b border-rule">
    <div class="border-r border-rule px-4 py-3"><dt class="label text-muted">Events</dt><dd class="code mt-1 text-[22px] font-medium">{events.length}</dd></div>
    <div class="border-r border-rule px-4 py-3">
      <dt class="label text-muted">Failures</dt>
      <dd class="code mt-1 flex items-center gap-2 text-[22px] font-medium">{#if failures.length}<span aria-hidden="true" class="h-3 w-3 rotate-45 bg-caution"></span>{/if}{failures.length}</dd>
    </div>
    <div class="px-4 py-3"><dt class="label text-muted">Downtime</dt><dd class="code mt-1 text-[22px] font-medium">{downtime.toFixed(1)}<span class="ml-1 text-[13px] font-normal text-muted">h</span></dd></div>
  </dl>
  <div class="flex items-center justify-between border-b border-rule bg-ground px-4 py-2">
    <span class="label text-muted">{shown.length} of {events.length} events</span>
    <label class="flex items-center gap-2 text-[13px]"><input type="checkbox" bind:checked={onlyFailures} class="h-4 w-4 accent-shell" /> Failures only</label>
  </div>

  <ol>
    {#each shown as e (e.event_id)}
      <li id={e.event_id} class="scroll-mt-4 target:bg-caution-wash grid gap-x-6 gap-y-1 border-b border-rule px-4 py-3 last:border-b-0 @2xl:grid-cols-[9rem_minmax(0,1fr)]">
        <div>
          <p class="code font-medium">{fmt(e.date)}</p>
          <p class="code text-[12px] text-muted">{e.event_id}</p>
          {#if e.failure_occurred}
            <p class="mt-1 inline-flex items-center gap-1.5 text-[13px] font-medium text-caution-ink"><span aria-hidden="true" class="h-2.5 w-2.5 rotate-45 bg-caution"></span>Failures</p>
          {/if}
        </div>
        <div class="space-y-1 text-[15px]">
          <p class="font-medium">{e.symptom ?? '-'}</p>
          {#if e.failure_mode}<p class="text-[13px]"><span class="label text-muted">Mode</span> {e.failure_mode}</p>{/if}
          <p class="text-[14px]"><span class="label text-muted">Root cause</span> {e.root_cause ?? '-'}</p>
          <p class="text-[14px]"><span class="label text-muted">Action</span> {e.corrective_action ?? '-'}</p>
          <p class="code text-[12px] text-muted">
            {#if e.downtime_hours}downtime {e.downtime_hours} h · {/if}{#if e.parts_replaced.length}parts: {e.parts_replaced.join(', ')}{/if}
          </p>
        </div>
      </li>
    {/each}
  </ol>
</section>
