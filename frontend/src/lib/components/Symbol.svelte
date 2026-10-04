<script lang="ts">
  import { SYMBOLS } from '#lib/symbols.ts'

  let { name, size = 24, strokeWidth = 1.5, class: cls = '' }: { name: string; size?: number; strokeWidth?: number; class?: string } = $props()

  const markup = $derived(SYMBOLS[name] ?? SYMBOLS.other)
</script>

<!-- Static, authored markup from symbols.ts: not user input. -->
<svg
  class={cls}
  viewBox="0 0 48 48"
  width={size}
  height={size}
  fill="none"
  stroke="currentColor"
  stroke-width={strokeWidth}
  stroke-linejoin="miter"
  stroke-linecap="square"
  aria-hidden="true"
>{@html markup}</svg>
