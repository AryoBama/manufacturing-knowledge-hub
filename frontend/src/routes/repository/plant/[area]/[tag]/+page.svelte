<script lang="ts">
  import Breadcrumb from '#lib/components/Breadcrumb.svelte'
  import DocumentList from '#lib/components/DocumentList.svelte'
  import EquipmentPlate from '#lib/components/EquipmentPlate.svelte'
  import ProtectionDiagram from '#lib/components/ProtectionDiagram.svelte'
  import Symbol from '#lib/components/Symbol.svelte'
  import type { PageProps } from './$types'

  let { data, params }: PageProps = $props()

  const FINAL = ['Issued for Operation', 'Approved']
  const eq = $derived(data.equipment)
  const items = $derived(data.docs.filter((d) => d.equipment_tag === params.tag))
  const finalCount = $derived(items.filter((d) => FINAL.includes(d.status ?? '')).length)
</script>

<Breadcrumb
  crumbs={[
    { label: 'Plant', href: '/repository?view=plant' },
    { label: `Area ${params.area}`, href: `/repository/plant/${params.area}` },
  ]}
/>

{#if data.equipmentError || !eq}
  <h1 class="code text-[32px] font-medium leading-tight tracking-tight">{params.tag}</h1>
  <p class="mt-2 border border-danger bg-danger-wash p-3 text-sm text-danger-ink">{data.equipmentError ?? 'Equipment not found.'}</p>
{:else}
  <EquipmentPlate equipment={eq} {finalCount} nonFinalCount={items.length - finalCount} />

  <div class="mt-8">
    {#if eq.has_diagram}
      <ProtectionDiagram equipment={eq} />

      {#if eq.instruments.length || eq.components.length}
        <div class="@container mt-6 grid gap-6 @3xl:grid-cols-2">
          {#if eq.instruments.length}
            <section class="border border-rule bg-panel">
              <h3 class="label bg-shell px-4 py-2.5 text-white">Monitoring instruments</h3>
              {#each eq.instruments as i (i.tag)}
                <div class="grid grid-cols-[7.5rem_minmax(0,1fr)] gap-3 border-b border-rule px-4 py-2.5 last:border-b-0">
                  <span class="code font-medium">{i.tag}</span>
                  <span class="text-[14px]">{i.instrument_type ?? i.role}<span class="block text-[12px] text-muted">{i.description.split('. ')[0]}</span></span>
                </div>
              {/each}
            </section>
          {/if}
          {#if eq.components.length}
            <section class="border border-rule bg-panel">
              <h3 class="label bg-shell px-4 py-2.5 text-white">Components &amp; actuators</h3>
              {#each eq.components as c (c.tag)}
                <div class="grid grid-cols-[9.5rem_minmax(0,1fr)] gap-3 border-b border-rule px-4 py-2.5 last:border-b-0">
                  <span class="code font-medium">{c.tag}</span>
                  <span class="text-[14px]">{c.description}</span>
                </div>
              {/each}
            </section>
          {/if}
        </div>
      {/if}
    {:else}
      <div class="flex items-start gap-4 border border-dashed border-rule p-5">
        <Symbol name="pid" size={36} class="shrink-0 text-muted" />
        <p class="text-[15px] text-muted">
          No protection map is available for <span class="code">{eq.tag}</span>: its interlock and instrument data have not been extracted.
          The documents and maintenance history below can still be opened.
        </p>
      </div>
    {/if}
  </div>

  <h2 class="label mb-3 mt-10 text-muted">Documents · {items.length}</h2>
  <DocumentList docs={items} showTag={false} empty="No documents for this equipment yet." />
{/if}
