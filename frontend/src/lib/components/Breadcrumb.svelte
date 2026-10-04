<script lang="ts">
  let { crumbs }: { crumbs: { label: string; href: string }[] } = $props()
</script>

<nav aria-label="Breadcrumb" class="label mb-4 flex flex-wrap items-center gap-x-2 gap-y-1 text-muted">
  <a href="/repository" class="hover:text-ink hover:underline">Repository</a>
  {#each crumbs as c (c.href)}
    <span aria-hidden="true">/</span>
    <a href={c.href} class="hover:text-ink hover:underline">{c.label}</a>
  {/each}
</nav>
