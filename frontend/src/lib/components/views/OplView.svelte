<script lang="ts">
  let { header, sections }: { header: string[]; sections: { title: string; lines: string[] }[] } = $props()
</script>

<div class="space-y-4">
  {#if header.length}
    <div class="border border-rule bg-panel px-4 py-3 text-[14px] text-muted">
      {#each header as h}<p>{h}</p>{/each}
    </div>
  {/if}
  {#each sections as s (s.title)}
    <section class="border border-rule bg-panel">
      <h3 class="label bg-ground px-4 py-2.5 text-muted">{s.title}</h3>
      {#if s.lines.length}
        <ol class="divide-y divide-rule">
          {#each s.lines as l, i (i)}
            <li class="px-4 py-2.5 text-[15px] leading-snug">{l}</li>
          {/each}
        </ol>
      {/if}
    </section>
  {/each}
</div>
