<script lang="ts">
  import { goto } from '$app/navigation'
  import { SendHorizonal } from '@lucide/svelte'
  import { tick } from 'svelte'
  import { chatStore } from '#lib/chatStore.svelte.ts'
  import AnswerView from './AnswerView.svelte'
  import AppShell from './AppShell.svelte'
  import ChatSidebar from './ChatSidebar.svelte'

  let { chatId, initialQuestion }: { chatId?: string; initialQuestion?: string | null } = $props()

  const SUGGESTIONS = [
    'What is the vibration trip setpoint for GA-1201A?',
    'What are the start permissives for GA-1201A?',
    'What was the root cause of past seal leaks on GA-1201A?',
  ]

  let input = $state('')
  let scroller: HTMLDivElement

  const chat = $derived(chatStore.get(chatId))
  const messages = $derived(chat?.messages ?? [])
  const pending = $derived(!!chatId && !!chatStore.pending[chatId])

  $effect(() => {
    void messages.length
    void pending
    tick().then(() => scroller?.scrollTo({ top: scroller.scrollHeight, behavior: 'smooth' }))
  })

  function send(text: string) {
    if (!text.trim() || pending) return
    input = ''
    const id = chatStore.send(text, chatId)
    if (id !== chatId) void goto(`/chat/${id}`, { replaceState: true })
  }

  // Deep link from the repository (/chat?q=...): ask once, then drop the query from the URL.
  let askedInitial = false
  $effect(() => {
    if (initialQuestion && !askedInitial) {
      askedInitial = true
      send(initialQuestion)
    }
  })
</script>

<AppShell>
  {#snippet sidebar()}<ChatSidebar />{/snippet}

  <main class="flex min-h-0 min-w-0 flex-1 flex-col">
    <div bind:this={scroller} class="scroll-thin flex-1 overflow-y-auto">
     <div class="flex min-h-full flex-col">
      <div class="mx-auto w-full max-w-3xl flex-1 space-y-6 px-4 py-6 md:py-10" aria-live="polite">
        {#if messages.length === 0}
          <div class="pt-6 md:pt-14">
            <h1 class="text-[32px] font-bold leading-tight tracking-tight">What do you need to know?</h1>
            <p class="mt-2 max-w-xl text-muted">Every answer carries source codes that point to documents in the Knowledge Repository.</p>
            <p class="label mt-8 text-muted">Example questions</p>
            <ul class="mt-2 border border-rule bg-panel">
              {#each SUGGESTIONS as s}
                <li class="border-b border-rule last:border-b-0">
                  <button onclick={() => send(s)} class="flex w-full items-center justify-between gap-4 px-4 py-3 text-left text-[15px] hover:bg-ground">
                    <span>{s}</span><span aria-hidden="true" class="code text-muted">→</span>
                  </button>
                </li>
              {/each}
            </ul>
          </div>
        {/if}

        {#each messages as m (m.id)}
          {#if m.role === 'user'}
            <div class="flex justify-end">
              <p class="max-w-[85%] bg-ink px-4 py-2.5 text-[15px] text-white">{m.text}</p>
            </div>
          {:else if m.error}
            <p class="border border-danger bg-danger-wash p-3 text-sm text-danger-ink">Could not get an answer: {m.text}</p>
          {:else if m.answer}
            <AnswerView answer={m.answer} messageId={m.id} />
          {:else}
            <p class="text-sm">{m.text}</p>
          {/if}
        {/each}

        {#if pending}
          <p class="label motion-safe:animate-pulse text-muted">Searching documents…</p>
        {/if}
      </div>
      <div class="sticky bottom-0 border-t border-rule bg-panel">
       <div class="mx-auto w-full max-w-3xl px-4 py-4">
      <form
        onsubmit={(e) => {
          e.preventDefault()
          send(input)
        }}
        class=""
      >
        <div class="flex items-end gap-2 border border-ink bg-panel p-1.5 focus-within:outline focus-within:outline-2 focus-within:outline-offset-2 focus-within:outline-ink">
          <textarea
            bind:value={input}
            onkeydown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                send(input)
              }
            }}
            rows="1"
            placeholder="Ask a technical question…"
            aria-label="Technical question"
            class="max-h-40 min-h-[40px] flex-1 resize-none bg-transparent px-2 py-2 text-[15px] outline-none [field-sizing:content]"
          ></textarea>
          <button
            type="submit"
            disabled={!input.trim() || pending}
            class="flex h-10 items-center gap-2 bg-shell px-4 text-sm font-semibold text-white hover:bg-shell-2 disabled:border disabled:border-rule disabled:bg-ground disabled:text-muted"
          >Send <SendHorizonal size={16} /></button>
        </div>
      </form>
       </div>
      </div>
     </div>
    </div>
  </main>
</AppShell>
