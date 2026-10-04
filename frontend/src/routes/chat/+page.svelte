<script lang="ts">
  import { page } from '$app/state'
  import ChatView from '#lib/components/ChatView.svelte'
</script>

<ChatView initialQuestion={page.url.searchParams.get('q')} />
