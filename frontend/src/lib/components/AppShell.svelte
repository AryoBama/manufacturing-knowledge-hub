<script lang="ts">
  import { page } from '$app/state'
  import { Menu, PanelLeftClose, PanelLeftOpen, X } from '@lucide/svelte'
  import type { Snippet } from 'svelte'
  import Brand from './Brand.svelte'

  let { sidebar, children }: { sidebar: Snippet; children: Snippet } = $props()

  const KEY = 'knowledge-hub.rail-collapsed'
  let open = $state(false) // mobile/tablet drawer
  let collapsed = $state(
    (() => {
      try {
        return localStorage.getItem(KEY) === '1'
      } catch {
        return false
      }
    })(),
  )

  function setCollapsed(v: boolean) {
    collapsed = v
    try {
      localStorage.setItem(KEY, v ? '1' : '0')
    } catch {
      /* preference only; ignore */
    }
  }

  // Close the drawer after any navigation.
  $effect(() => {
    void page.url.pathname
    open = false
  })
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && (open = false)} />

<div class="flex h-full flex-col lg:flex-row">
  <header class="on-shell flex shrink-0 items-center gap-2 bg-shell px-3 py-2 lg:hidden">
    <button
      onclick={() => (open = true)}
      aria-label="Open navigation menu"
      aria-expanded={open}
      class="grid h-10 w-10 place-items-center text-white hover:bg-shell-2"
    ><Menu size={20} /></button>
    <Brand />
  </header>

  {#if open}
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
    <div class="fixed inset-0 z-30 bg-ink/50 lg:hidden" onclick={() => (open = false)}></div>
  {/if}

  <aside
    class="on-shell fixed inset-y-0 left-0 z-40 flex w-72 max-w-[85vw] shrink-0 flex-col bg-shell text-shell-text transition-transform duration-200 ease-out lg:static lg:z-auto lg:max-w-none lg:translate-x-0 lg:visible
      {collapsed ? 'lg:w-12' : 'lg:w-72'}
      {open ? 'translate-x-0' : 'invisible -translate-x-full'}"
  >
    <button
      onclick={() => (open = false)}
      aria-label="Close navigation menu"
      class="absolute right-2 top-2 z-10 grid h-9 w-9 place-items-center text-shell-text hover:bg-shell-2 hover:text-white lg:hidden"
    ><X size={18} /></button>

    {#if collapsed}
      <button
        onclick={() => setCollapsed(false)}
        aria-label="Show navigation menu"
        class="mx-auto mt-3 hidden h-9 w-9 place-items-center text-shell-text hover:bg-shell-2 hover:text-white lg:grid"
      ><PanelLeftOpen size={18} /></button>
    {:else}
      <button
        onclick={() => setCollapsed(true)}
        aria-label="Hide navigation menu"
        class="absolute right-2 top-2 z-10 hidden h-9 w-9 place-items-center text-shell-text hover:bg-shell-2 hover:text-white lg:grid"
      ><PanelLeftClose size={18} /></button>
    {/if}

    <div class="flex min-h-0 flex-1 flex-col {collapsed ? 'lg:hidden' : ''}">
      {@render sidebar()}
    </div>
  </aside>

  <div class="flex min-h-0 min-w-0 flex-1 flex-col">
    {@render children()}
  </div>
</div>
