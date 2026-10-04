<script lang="ts">
  import { goto } from '$app/navigation'
  import { page } from '$app/state'
  import { FolderOpen, History, MessageSquarePlus, Plus, Trash2 } from '@lucide/svelte'
  import { chatStore } from '#lib/chatStore.svelte.ts'
  import Brand from './Brand.svelte'
  import UploadDialog from './UploadDialog.svelte'

  let uploadOpen = $state(false)

  function remove(id: string) {
    if (!confirm('Delete this conversation?')) return
    chatStore.remove(id)
    if (page.params.chatId === id) void goto('/chat')
  }
</script>

<div class="flex h-full min-h-0 flex-col">
  <div class="space-y-3 p-4">
    <Brand />
    <button onclick={() => (uploadOpen = true)} class="flex w-full items-center border border-white/25 px-3 py-2.5 text-sm font-semibold text-white hover:bg-shell-2">
      <Plus size={18} class="shrink-0" />
      <span class="flex-1 text-center">Add Document</span>
      <span class="w-[18px]"></span>
    </button>
    <a href="/repository" class="flex w-full items-center gap-2 border border-white/25 px-3 py-2 text-sm text-white hover:bg-shell-2">
      <FolderOpen size={18} strokeWidth={1.75} />
      Knowledge Repository
    </a>
    <a href="/failure-memory" class="flex w-full items-center gap-2 border border-white/25 px-3 py-2 text-sm text-white hover:bg-shell-2">
      <History size={18} strokeWidth={1.75} />
      Failure Memory
    </a>
  </div>

  <div class="label px-4 pb-2 pt-3 text-shell-text">Chat History</div>
  <nav class="scroll-thin min-h-0 flex-1 overflow-y-auto px-2 pb-2">
    {#if chatStore.chats.length === 0}
      <p class="px-2 py-3 text-sm text-shell-text">No conversations yet.</p>
    {/if}
    {#each chatStore.chats as c (c.id)}
      {@const active = page.params.chatId === c.id}
      <div class="group relative">
        <a
          href="/chat/{c.id}"
          aria-current={active ? 'page' : undefined}
          class="block truncate py-2 pl-3 pr-9 text-sm {active ? 'bg-shell-2 font-semibold text-white' : 'text-shell-text hover:bg-shell-2 hover:text-white'}"
        >{c.title}</a>
        <button
          aria-label="Delete conversation: {c.title}"
          onclick={() => remove(c.id)}
          class="absolute right-1 top-1/2 grid h-7 w-7 -translate-y-1/2 place-items-center text-shell-text opacity-0 hover:bg-shell hover:text-white focus-visible:opacity-100 group-hover:opacity-100 [@media(hover:none)]:opacity-100"
        ><Trash2 size={14} /></button>
      </div>
    {/each}
  </nav>

  <div class="border-t border-white/15 p-3">
    <a href="/chat" class="flex w-full items-center justify-center gap-2 bg-panel px-3 py-2.5 text-sm font-semibold text-ink hover:bg-ground">
      <MessageSquarePlus size={16} /> New chat
    </a>
  </div>
  {#if uploadOpen}<UploadDialog onclose={() => (uploadOpen = false)} />{/if}
</div>
