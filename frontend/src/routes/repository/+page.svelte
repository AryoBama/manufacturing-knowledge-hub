<script lang="ts">
  import RepositoryHome from '#lib/components/RepositoryHome.svelte'
  import type { PageProps } from './$types'

  let { data }: PageProps = $props()
</script>

<RepositoryHome docs={data.docs} plant={data.plant} />
