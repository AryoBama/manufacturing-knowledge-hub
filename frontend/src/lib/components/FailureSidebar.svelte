<script lang="ts">
  import { FolderOpen, MessageSquareText } from '@lucide/svelte'
  import type { PlantEquipment } from '#lib/api.ts'
  import Brand from './Brand.svelte'

  let { equipment, activeTag }: { equipment: PlantEquipment[]; activeTag: string | null } = $props()

  const withHistory = $derived([...equipment].filter((e) => e.maintenance_events > 0).sort((a, b) => b.failure_count - a.failure_count))
  const withoutHistory = $derived(equipment.length - withHistory.length)
</script>

<div class="flex h-full min-h-0 flex-col">
  <div class="space-y-3 p-4">
    <Brand />
    <a href="/chat" class="flex w-full items-center justify-center gap-2 bg-panel px-3 py-2.5 text-sm font-semibold text-ink hover:bg-ground">
      <MessageSquareText size={16} /> Open Chatbot
    </a>
    <a href="/repository" class="flex w-full items-center gap-2 border border-white/25 px-3 py-2 text-sm text-white hover:bg-shell-2">
      <FolderOpen size={18} strokeWidth={1.75} /> Knowledge Repository
    </a>
  </div>

  <div class="label flex items-center justify-between px-4 pb-2 pt-3 text-shell-text"><span>Equipment</span><span>Failures</span></div>
  <nav class="scroll-thin min-h-0 flex-1 overflow-y-auto px-2 pb-4">
    {#each withHistory as e (e.tag)}
      <a
        href="/failure-memory?tag={e.tag}"
        aria-current={activeTag === e.tag ? 'page' : undefined}
        title={e.name}
        class="flex items-center justify-between px-3 py-2 text-sm {activeTag === e.tag ? 'bg-shell-2 font-semibold text-white' : 'text-shell-text hover:bg-shell-2 hover:text-white'}"
      >
        <span><span class="code text-[13px]">{e.tag}</span><span class="block text-[12px] opacity-80">{e.name}</span></span>
        <span class="code text-[13px]">{e.failure_count}</span>
      </a>
    {/each}
    {#if withoutHistory > 0}
      <p class="px-3 py-3 text-[12px] leading-snug text-shell-text">{withoutHistory} more registered equipment have no maintenance records loaded.</p>
    {/if}
  </nav>
</div>
