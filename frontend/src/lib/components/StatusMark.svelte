<script lang="ts">
  let { status, onShell = false }: { status: string | null; onShell?: boolean } = $props()

  const FINAL = ['Issued for Operation', 'Approved']
  const tone = $derived(!status ? 'none' : FINAL.includes(status) ? 'ok' : 'caution')
</script>

{#if status}
  <span class="inline-flex items-center gap-2 whitespace-nowrap text-[13px] font-medium {tone === 'caution' ? 'text-caution-ink' : 'text-ink'}">
    <span aria-hidden="true" class="h-2.5 w-2.5 shrink-0 rotate-45 {tone === 'ok' ? 'bg-ok' : 'bg-caution'}"></span>
    {status}
  </span>
{/if}
