<script lang="ts">
  import type { EquipmentView } from '#lib/api.ts'
  import { isaParts, SYMBOLS } from '#lib/symbols.ts'

  let { equipment }: { equipment: EquipmentView } = $props()

  const PITCH = 70
  const W = 940
  const LOGIC_X = 360
  const LOGIC_W = 110
  const EFFECT_X = 610

  const trips = $derived(equipment.trips)
  const permissives = $derived(equipment.permissives)

  // Distinct effects (columns of the cause-effect logic), in first-seen order.
  const effects = $derived.by(() => {
    const seen = new Map<string, { key: string; target: string | null; kind: string; label: string }>()
    for (const t of trips)
      for (const e of t.effects) {
        const key = e.target ?? e.action
        if (!seen.has(key)) seen.set(key, { key, target: e.target, kind: e.kind, label: e.action.replace(/\s*\(EFF-\d+\)/, '') })
      }
    return [...seen.values()]
  })

  const tripRows = $derived(trips.length)
  const tripsBottom = $derived(40 + Math.max(tripRows, effects.length) * PITCH)
  const permTop = $derived(tripsBottom + 30)
  const height = $derived(permissives.length ? permTop + permissives.length * PITCH + 20 : tripsBottom + 10)
  const logicTop = 22
  const logicBottom = $derived(40 + (tripRows - 1) * PITCH + 24)
  const logicMid = $derived((logicTop + logicBottom) / 2)
  const permMid = $derived(permTop + 40 + ((permissives.length - 1) * PITCH) / 2)

  let selected = $state<string | null>(null)
  let hovered = $state<string | null>(null)
  const active = $derived(hovered ?? selected)
  const activeTrip = $derived(trips.find((t) => (t.id ?? t.initiator) === active) ?? null)
  const effectOn = (key: string) => !activeTrip || activeTrip.effects.some((e) => (e.target ?? e.action) === key)

  const tripKey = (t: { id: string | null; initiator: string }) => t.id ?? t.initiator
  const symbolFor = (kind: string) => (kind === 'valve' ? 'valve' : kind === 'control_valve' ? 'control_valve' : kind === 'pump' ? 'pump' : kind === 'compressor' ? 'compressor' : 'system')
  const select = (k: string) => (selected = selected === k ? null : k)
</script>

<svelte:window onkeydown={(e) => e.key === 'Escape' && (selected = null)} />

{#snippet bubble(cx: number, cy: number, tag: string)}
  {@const [fn, loop] = isaParts(tag)}
  <circle {cx} {cy} r="23" class="fill-panel stroke-ink" stroke-width="1.5" />
  <path d="M{cx - 23} {cy}H{cx + 23}" class="stroke-ink" stroke-width="1.5" />
  <text x={cx} y={cy - 4} font-size={fn.length > 3 ? 10.5 : 12} font-weight="700" text-anchor="middle" class="fill-ink">{fn}</text>
  <text x={cx} y={cy + 14} font-size="11" text-anchor="middle" class="fill-ink font-mono">{loop}</text>
{/snippet}

<div class="@container border border-rule bg-panel">
  <div class="flex flex-wrap items-center justify-between gap-2 bg-shell px-4 py-2.5 text-white">
    <h3 class="label">Protection map {equipment.logic_tag ? `· ${equipment.logic_tag}` : ''}</h3>
    <p class="code text-[12px] text-shell-text">{trips.length} trips · {permissives.length} start permissives{trips[0]?.sil ? ` · ${trips[0].sil}` : ''}</p>
  </div>

  <p class="border-b border-rule bg-ground px-4 py-1.5 text-[12px] text-muted @3xl:hidden">Scroll sideways to see the whole diagram.</p>
  <div class="scroll-thin overflow-x-auto">
    <svg viewBox="0 0 {W} {height}" class="block min-w-[760px]" role="group" aria-label="Protection cause-and-effect diagram {equipment.tag}">
      <!-- initiator → logic lines -->
      {#each trips as t, i (tripKey(t))}
        {@const y = 40 + i * PITCH + 2}
        {@const on = !active || active === tripKey(t)}
        <path d="M66 {y}H{LOGIC_X}" class="stroke-ink" stroke-width={active === tripKey(t) ? 2.25 : 1.25} opacity={on ? 1 : 0.18} />
      {/each}
      <!-- logic → effect elbows -->
      {#each effects as e, j (e.key)}
        {@const y = 40 + j * PITCH + 2}
        <path d="M{LOGIC_X + LOGIC_W} {logicMid}H{LOGIC_X + LOGIC_W + 50}V{y}H{EFFECT_X - 6}" fill="none" class="stroke-ink" stroke-width={activeTrip && effectOn(e.key) ? 2.25 : 1.25} opacity={effectOn(e.key) ? 1 : 0.15} />
      {/each}

      <!-- logic block -->
      <rect x={LOGIC_X} y={logicTop} width={LOGIC_W} height={logicBottom - logicTop} class="fill-shell" />
      <text x={LOGIC_X + LOGIC_W / 2} y={logicMid - 8} font-size="13" font-weight="700" text-anchor="middle" class="fill-white font-mono">{equipment.logic_tag ?? 'LOGIC'}</text>
      <text x={LOGIC_X + LOGIC_W / 2} y={logicMid + 10} font-size="11" text-anchor="middle" class="fill-shell-text">{trips[0]?.sil ?? ''}</text>
      <text x={LOGIC_X + LOGIC_W / 2} y={logicMid + 28} font-size="11" font-weight="600" letter-spacing="1.2" text-anchor="middle" class="fill-shell-text">OR</text>

      <!-- initiators -->
      {#each trips as t, i (tripKey(t))}
        {@const y = 40 + i * PITCH + 2}
        {@const k = tripKey(t)}
        <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
        <g
          role="button"
          tabindex="0"
          aria-pressed={selected === k}
          aria-label="Trip {t.id} {t.initiator}, setpoint {t.setpoint ?? 'not available'}"
          class="cursor-pointer outline-none [&:focus-visible_.hit]:stroke-ink"
          opacity={!active || active === k ? 1 : 0.35}
          onclick={() => select(k)}
          onmouseenter={() => (hovered = k)}
          onmouseleave={() => (hovered = null)}
          onfocus={() => (hovered = k)}
          onblur={() => (hovered = null)}
          onkeydown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), select(k))}
        >
          <rect class="hit fill-transparent" stroke-width="2" x="2" y={y - 32} width={LOGIC_X - 20} height="64" />
          {@render bubble(44, y, t.initiator)}
          <text x="82" y={y - 6} font-size="14" font-weight="700" class="fill-ink font-mono" paint-order="stroke" stroke-width="5" style="stroke: var(--color-panel)">{t.setpoint ?? '-'}</text>
          <text x="82" y={y + 14} font-size="12" class="fill-muted" paint-order="stroke" stroke-width="5" style="stroke: var(--color-panel)">{t.id} · voting {t.voting ?? '-'}</text>
        </g>
      {/each}

      <!-- effects -->
      {#each effects as e, j (e.key)}
        {@const y = 40 + j * PITCH + 2}
        <g opacity={effectOn(e.key) ? 1 : 0.2}>
          <svg x={EFFECT_X} y={y - 22} width="44" height="44" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="miter" stroke-linecap="square" class="text-ink">{@html SYMBOLS[symbolFor(e.kind)]}</svg>
          <text x={EFFECT_X + 56} y={y - 3} font-size="14" font-weight="700" class="fill-ink font-mono">{e.target ?? '-'}</text>
          <text x={EFFECT_X + 56} y={y + 15} font-size="12" class="fill-muted">{e.label}</text>
        </g>
      {/each}

      <!-- start permissives → AND → equipment -->
      {#if permissives.length}
        <text x="2" y={permTop + 6} font-size="11" font-weight="700" letter-spacing="1.2" class="fill-muted">START PERMISSIVES</text>
        {#each permissives as p, i (p.id ?? p.source)}
          {@const y = permTop + 40 + i * PITCH}
          <path d="M66 {y}H{LOGIC_X}" class="stroke-ink" stroke-width="1.25" />
          {@render bubble(44, y, p.source)}
          <text x="82" y={y - 4} font-size="13" font-weight="600" class="fill-ink" paint-order="stroke" stroke-width="5" style="stroke: var(--color-panel)">{p.description.replace(/\s*\(Logic Gate.*$/, '')}</text>
          <text x="82" y={y + 14} font-size="12" class="fill-muted font-mono" paint-order="stroke" stroke-width="5" style="stroke: var(--color-panel)">{p.id}</text>
        {/each}
        <rect x={LOGIC_X} y={permTop + 12} width={LOGIC_W} height={permissives.length * PITCH - 20} class="fill-ink" />
        <text x={LOGIC_X + LOGIC_W / 2} y={permMid + 5} font-size="15" font-weight="700" letter-spacing="1" text-anchor="middle" class="fill-white">AND</text>
        <path d="M{LOGIC_X + LOGIC_W} {permMid}H{EFFECT_X - 6}" class="stroke-ink" stroke-width="1.5" />
        <svg x={EFFECT_X} y={permMid - 22} width="44" height="44" viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="miter" stroke-linecap="square" class="text-ink">{@html SYMBOLS[equipment.symbol] ?? SYMBOLS.other}</svg>
        <text x={EFFECT_X + 56} y={permMid - 3} font-size="14" font-weight="700" class="fill-ink font-mono">{equipment.tag}</text>
        <text x={EFFECT_X + 56} y={permMid + 15} font-size="12" class="fill-muted">Start permitted</text>
      {/if}
    </svg>
  </div>

  <div class="border-t border-rule px-4 py-3 text-[14px]" aria-live="polite">
    {#if activeTrip}
      <p><span class="code font-medium">{activeTrip.id} · {activeTrip.initiator}</span> {activeTrip.description.replace(/\s*\(Setpoint.*$/, '')}: <span class="code">{activeTrip.setpoint}</span>, voting <span class="code">{activeTrip.voting}</span></p>
      <p class="mt-1 text-muted">Effects: {activeTrip.effects.map((e) => e.action.replace(/\s*\(EFF-\d+\)/, '')).join(' → ')}</p>
    {:else}
      <p class="text-muted">Select a trip to trace its effects. Other lines and symbols dim.</p>
    {/if}
  </div>
</div>
