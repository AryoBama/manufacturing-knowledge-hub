<script lang="ts">
  import { page } from '$app/state'
  import ChatView from '#lib/components/ChatView.svelte'
</script>

{#key page.params.chatId}
  <ChatView chatId={page.params.chatId} />
{/key}
