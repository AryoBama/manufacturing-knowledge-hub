<script lang="ts">
  import type { EquipmentView } from '#lib/api.ts'
  import Symbol from './Symbol.svelte'

  let { equipment, finalCount, nonFinalCount }: { equipment: EquipmentView; finalCount: number; nonFinalCount: number } = $props()

  const last = $derived(
    equipment.maintenance.last_date
      ? new Date(equipment.maintenance.last_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
      : null,
  )
</script>

<!-- Reads like an equipment nameplate: symbol plate on the left, engraved fields on the right. -->
<header class="@container border border-ink bg-panel">
  <div class="grid @2xl:grid-cols-[9rem_1fr]">
    <div class="grid place-items-center bg-shell p-6 text-white @2xl:p-4"><Symbol name={equipment.symbol} size={84} strokeWidth={1.25} /></div>
    <div>
      <div class="border-b border-rule px-5 py-4">
        <h1 class="code text-[36px] font-medium leading-tight tracking-tight">{equipment.tag}</h1>
        <p class="text-[17px] font-medium">{equipment.name}</p>
      </div>
      <dl class="grid grid-cols-2 @xl:grid-cols-4">
        <div class="border-b border-r border-rule px-4 py-3 @xl:border-b-0"><dt class="label text-muted">Type</dt><dd class="mt-1 text-[14px] leading-snug">{equipment.type}</dd></div>
        <div class="border-b border-rule px-4 py-3 @xl:border-b-0 @xl:border-r"><dt class="label text-muted">Area</dt><dd class="code mt-1 text-[15px]">{equipment.area}</dd></div>
        <div class="border-r border-rule px-4 py-3">
          <dt class="label text-muted">Documents</dt>
          <dd class="mt-1 flex flex-wrap items-center gap-x-2 text-[15px]"><span class="code">{equipment.document_count}</span>
            {#if nonFinalCount > 0}<span class="inline-flex items-center gap-1 text-[13px] text-caution-ink"><span aria-hidden="true" class="h-2.5 w-2.5 rotate-45 bg-caution"></span>{nonFinalCount} not final</span>{:else if finalCount > 0}<span class="text-[13px] text-muted">all final</span>{/if}
          </dd>
        </div>
        <div class="px-4 py-3">
          <dt class="label text-muted">Maintenance</dt>
          <dd class="mt-1 text-[15px]"><span class="code">{equipment.maintenance.events}</span> <span class="text-[13px] text-muted">events · <span class="code">{equipment.maintenance.failures}</span> failures</span></dd>
          {#if last}<dd class="text-[12px] text-muted">latest {last}</dd>{/if}
          {#if equipment.maintenance.events > 0}<dd class="mt-1 text-[13px]"><a href="/failure-memory?tag={equipment.tag}" class="font-semibold underline decoration-rule underline-offset-4 hover:decoration-ink">Open failure memory</a></dd>{/if}
        </div>
      </dl>
    </div>
  </div>
</header>
