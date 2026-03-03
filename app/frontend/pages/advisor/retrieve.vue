<template>
  <AdvisorShell>
    <h2>KB Retrieval Test</h2>
    <div class="panel">
      <label>Query</label>
      <input v-model="query" placeholder="e.g. OAS clawback" />
      <label>User ID (optional)</label>
      <input v-model.number="userId" type="number" />
      <div class="actions">
        <button @click="run">Run Retrieval</button>
      </div>
    </div>
    <div class="panel" v-if="results.length">
      <h3>Results</h3>
      <ul>
        <li v-for="(r, idx) in results" :key="idx">
          <div><strong>{{ r.title }}</strong> ({{ r.source_ref }})</div>
          <div>{{ r.excerpt }}</div>
        </li>
      </ul>
    </div>
  </AdvisorShell>
</template>

<script setup lang="ts">
import AdvisorShell from "~/components/AdvisorShell.vue"

const apiFetch = useApiFetch()
const query = ref("")
const userId = ref(1)
const results = ref<any[]>([])

const run = async () => {
  const res = await apiFetch<any>("/api/advisor/retrieve", {
    method: "POST",
    body: { query: query.value, user_id: userId.value }
  })
  results.value = res.results || []
}
</script>

<style scoped>
.panel {
  background: #fff;
  padding: 16px;
  border-radius: 12px;
  margin-bottom: 16px;
}
input {
  width: 100%;
  margin-bottom: 8px;
}
button {
  background: var(--accent);
  border: none;
  color: white;
  padding: 8px 12px;
  border-radius: 6px;
}
</style>
