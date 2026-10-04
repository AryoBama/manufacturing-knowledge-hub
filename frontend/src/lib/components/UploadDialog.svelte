<script lang="ts">
  import { UploadCloud, X } from '@lucide/svelte'

  let { onclose }: { onclose: () => void } = $props()
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && onclose()} />

<!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
<div class="fixed inset-0 z-50 grid place-items-center bg-ink/60 p-4" onclick={onclose}>
  <div class="w-full max-w-md border border-rule bg-panel text-ink" role="dialog" aria-modal="true" aria-labelledby="upload-title" tabindex="-1" onclick={(e) => e.stopPropagation()}>
    <div class="flex items-center justify-between bg-shell px-5 py-3 text-white">
      <h2 id="upload-title" class="label">Add Document</h2>
      <button onclick={onclose} aria-label="Close" class="grid h-8 w-8 place-items-center hover:bg-shell-2"><X size={18} /></button>
    </div>
    <div class="p-5">
      <div class="grid place-items-center border border-dashed border-rule px-4 py-10 text-center">
        <UploadCloud class="mb-2 text-muted" size={32} strokeWidth={1.5} />
        <p class="text-sm text-muted">Upload documents (XLSX, PDF) to the repository</p>
      </div>
      <p class="mt-4 flex gap-3 border border-caution bg-caution-wash p-3 text-sm text-caution-ink">
        <span aria-hidden="true" class="mt-1.5 h-2.5 w-2.5 shrink-0 rotate-45 bg-caution"></span>
        <span>Upload is not available yet: the backend has no ingestion endpoint. Documents are loaded from the extraction pipeline (<code class="code">data/extracted</code>).</span>
      </p>
      <div class="mt-5 flex justify-end">
        <button onclick={onclose} class="bg-shell px-4 py-2 text-sm font-semibold text-white hover:bg-shell-2">Close</button>
      </div>
    </div>
  </div>
</div>
