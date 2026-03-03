<template>
  <UserShell>
    <h2>Reports (Approved Only)</h2>
    <div class="grid">
      <div class="panel list">
        <div v-for="r in reports" :key="r.id" class="item" @click="select(r)">
          <div><strong>Report {{ r.id }}</strong></div>
          <div class="meta">{{ r.created_at }}</div>
        </div>
      </div>
      <div class="panel detail" v-if="selected">
        <div class="status">Status: {{ selected.status }}</div>
        <div v-html="render(selected.final_md || selected.draft_md || '')"></div>
      </div>
    </div>
  </UserShell>
</template>

<script setup lang="ts">
import UserShell from "~/components/UserShell.vue"
import { marked } from "marked"

const apiFetch = useApiFetch()
const reports = ref<any[]>([])
const selected = ref<any | null>(null)

const load = async () => {
  reports.value = await apiFetch<any[]>("/api/users/1/reports")
  selected.value = reports.value[0] || null
}

const render = (md: string) => marked.parse(md || "")
const select = (r: any) => (selected.value = r)

onMounted(load)
</script>

<style scoped>
.panel {
  background: #fff;
  padding: 16px;
  border-radius: 12px;
  margin-bottom: 16px;
}
.grid {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
}
.list .item {
  padding: 10px 8px;
  border-bottom: 1px solid #eee;
  cursor: pointer;
}
.list .item:hover {
  background: #f6f6f6;
}
.meta {
  font-size: 12px;
  color: #666;
}
.status {
  font-weight: 600;
  margin-bottom: 8px;
}
</style>
