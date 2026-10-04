<script lang="ts">
  import Breadcrumb from '#lib/components/Breadcrumb.svelte'
  import DocumentList from '#lib/components/DocumentList.svelte'
  import { docTypeMeta } from '#lib/docTypes.ts'
  import type { PageProps } from './$types'

  let { data, params }: PageProps = $props()

  const meta = $derived(docTypeMeta(params.docType))
  const items = $derived(data.docs.filter((d) => d.document_type === params.docType))
</script>

<Breadcrumb crumbs={[{ label: 'Type', href: '/repository' }]} />
<h1 class="text-[32px] font-bold leading-tight tracking-tight">{meta.label}</h1>
<p class="mt-1 max-w-2xl text-muted">{meta.description}</p>
<div class="mt-8"><DocumentList docs={items} empty="No documents in this category yet." /></div>
