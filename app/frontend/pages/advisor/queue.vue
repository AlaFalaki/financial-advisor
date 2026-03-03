<template>
  <AdvisorShell>
    <h2>Report Requests</h2>
    <div v-for="r in requests" :key="r.id" class="panel">
      <div>Request {{ r.id }} — {{ r.question_text }}</div>
      <div>Status: {{ r.status }}</div>
      <div v-if="r.report_id">Report: {{ r.report_id }} ({{ r.report_status }})</div>
      <NuxtLink :to="`/advisor/request/${r.id}`">Open Request</NuxtLink>
    </div>
  </AdvisorShell>
</template>

<script setup lang="ts">
import AdvisorShell from "~/components/AdvisorShell.vue"

const apiFetch = useApiFetch()
const requests = ref<any[]>([])

const load = async () => {
  requests.value = await apiFetch<any[]>("/api/advisor/requests")
}

onMounted(load)
</script>

<style scoped>
.panel {
  background: #fff;
  padding: 16px;
  border-radius: 12px;
  margin-bottom: 16px;
}
</style>
