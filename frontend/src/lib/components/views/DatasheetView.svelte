<script lang="ts">
  let { groups }: { groups: { category: string; rows: { parameter: string; value: string; unit: string | null }[] }[] } = $props()
</script>

<!-- A datasheet is a form: labelled cells in a ruled grid, one block per category. -->
<div class="space-y-6">
  {#each groups as g (g.category)}
    <section class="border border-rule bg-panel">
      <h3 class="label bg-shell px-4 py-2.5 text-white">{g.category}</h3>
      <dl class="grid @2xl:grid-cols-2">
        {#each g.rows as r, i (r.parameter + i)}
          <div class="grid grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] gap-4 border-b border-rule px-4 py-2.5 @2xl:odd:border-r">
            <dt class="text-[13px] text-muted">{r.parameter}</dt>
            <dd class="code break-words font-medium">{r.value}{#if r.unit}<span class="ml-1.5 font-normal text-muted">{r.unit}</span>{/if}</dd>
          </div>
        {/each}
      </dl>
    </section>
  {/each}
</div>
