<template>
  <AdvisorShell>
    <div class="layout">
      <div class="main">
        <div class="hero">
          <div class="hero-left">
            <h2>Advisor Workspace</h2>
            <div class="meta">
              <div><strong>Request:</strong> {{ detail?.request?.question_text }}</div>
              <div><strong>Status:</strong> {{ detail?.request?.status }}</div>
            </div>
            <div class="user-card grid">
              <div class="section-label">User</div>
              <div class="user-line"><strong>User:</strong> {{ detail?.user?.name }} ({{ detail?.user?.email }})</div>
              <div class="user-line"><strong>Province:</strong> {{ detail?.profile?.user?.province }}</div>
              <div class="user-line"><strong>Birth Year:</strong> {{ detail?.profile?.user?.birthYear }}</div>
              <div class="user-line"><strong>Marital Status:</strong> {{ detail?.profile?.user?.maritalStatus }}</div>
              <div class="user-line"><strong>Retirement Year:</strong> {{ detail?.profile?.user?.retirementYear }}</div>

              <div class="section-label">Income</div>
              <div class="user-line"><strong>Employment Income:</strong> {{ detail?.profile?.income?.employmentIncomeAnnual }}</div>
              <div class="user-line"><strong>Pension Annual:</strong> {{ detail?.profile?.income?.pensionAnnual }}</div>
              <div class="user-line"><strong>CPP Start Age:</strong> {{ detail?.profile?.income?.cppStartAge }}</div>
              <div class="user-line"><strong>OAS Start Age:</strong> {{ detail?.profile?.income?.oasStartAge }}</div>
              <div class="user-line"><strong>Other Income:</strong> {{ detail?.profile?.income?.otherIncomeAnnual }}</div>

              <div class="section-label">Spending</div>
              <div class="user-line"><strong>Target Net Annual:</strong> {{ detail?.profile?.spending?.targetNetAnnual }}</div>
              <div class="user-line"><strong>Inflation Assumption:</strong> {{ detail?.profile?.spending?.inflationAssumption }}</div>

              <div class="section-label">Accounts</div>
              <div class="user-line"><strong>TFSA Balance:</strong> {{ detail?.profile?.accounts?.tfsa?.balance }}</div>
              <div class="user-line"><strong>RRSP Balance:</strong> {{ detail?.profile?.accounts?.rrsp?.balance }}</div>
              <div class="user-line"><strong>Non-Reg Balance:</strong> {{ detail?.profile?.accounts?.nonRegistered?.balance }}</div>
              <div class="user-line"><strong>Non-Reg ACB:</strong> {{ detail?.profile?.accounts?.nonRegistered?.adjustedCostBase }}</div>

              <div class="section-label">Assumptions</div>
              <div class="user-line"><strong>Expected Return:</strong> {{ detail?.profile?.assumptions?.expectedReturn }}</div>
              <div class="user-line"><strong>Return Volatility:</strong> {{ detail?.profile?.assumptions?.returnVolatility }}</div>
              <div class="user-line"><strong>Planning Horizon:</strong> {{ detail?.profile?.assumptions?.planningHorizonYears }}</div>
              <div class="user-line"><strong>Investment Risk:</strong> {{ detail?.profile?.assumptions?.investmentRisk }}</div>
              <div class="user-line"><strong>Return Override %:</strong> {{ detail?.profile?.assumptions?.investmentReturnOverride }}</div>
            </div>
          </div>
          <div class="hero-right">
            <button class="primary" @click="generateReport" :disabled="reportId || generating">
              <span v-if="generating">Generating…</span>
              <span v-else>Generate Report</span>
            </button>
          </div>
        </div>

        <div class="panel report" v-if="reportId">
          <div class="report-header">
            <h3>Report</h3>
            <div class="actions">
              <button @click="toggleEdit">
                <span v-if="editing">Cancel Edit</span>
                <span v-else>Edit</span>
              </button>
              <button @click="saveFinal" :disabled="saving">
                <span v-if="saving">Saving…</span>
                <span v-else>Save</span>
              </button>
              <button @click="approve" :disabled="approving">
                <span v-if="approving">Confirming…</span>
                <span v-else>Confirm (Approve)</span>
              </button>
            </div>
          </div>
          <div v-if="editing">
            <textarea v-model="draft" rows="18"></textarea>
          </div>
          <div v-else class="preview" v-html="render(draft)"></div>

          <div class="citations">
            <h4>Citations</h4>
            <ul>
              <li v-for="c in citations" :key="c.id">
                {{ c.citation_key }} — {{ c.title }} ({{ c.source_ref }})
              </li>
            </ul>
          </div>
        </div>
      </div>

      <aside class="chat">
        <h3>Advisor Chat</h3>
        <div class="messages">
          <div v-for="(m, idx) in messages" :key="idx" :class="['msg', m.role]">
            <pre>{{ m.content }}</pre>
          </div>
        </div>
        <div class="composer">
          <textarea v-model="concerns" rows="4" placeholder="Ask agent to change or reformat..."></textarea>
          <button @click="refine" :disabled="refining">
            <span v-if="refining">Sending…</span>
            <span v-else>Send</span>
          </button>
        </div>
      </aside>
    </div>
  </AdvisorShell>
</template>

<script setup lang="ts">
import AdvisorShell from "~/components/AdvisorShell.vue"
import { marked } from "marked"

const apiFetch = useApiFetch()
const route = useRoute()
const detail = ref<any>(null)
const reportId = ref<number | null>(null)
const draft = ref("")
const citations = ref<any[]>([])
const concerns = ref("")
const messages = ref<{ role: string; content: string }[]>([])
const editing = ref(false)
const generating = ref(false)
const saving = ref(false)
const approving = ref(false)
const refining = ref(false)

const load = async () => {
  const requestId = route.params.requestId
  detail.value = await apiFetch<any>(`/api/requests/${requestId}/detail`)
  if (detail.value?.report?.id) {
    reportId.value = detail.value.report.id
    const report = await apiFetch<any>(`/api/reports/${reportId.value}`)
    draft.value = report.draft_md
    citations.value = report.citations || []
  }
}

const generateReport = async () => {
  const requestId = route.params.requestId
  generating.value = true
  try {
    const res = await apiFetch<any>(`/api/requests/${requestId}/generate-report`, {
      method: "POST"
    })
    reportId.value = res.report_id
    const report = await apiFetch<any>(`/api/reports/${reportId.value}`)
    draft.value = report.draft_md
    citations.value = report.citations || []
  } finally {
    generating.value = false
  }
}

const render = (md: string) => marked.parse(md)
const toggleEdit = () => (editing.value = !editing.value)

const saveFinal = async () => {
  if (!reportId.value) return
  saving.value = true
  try {
    await apiFetch(`/api/reports/${reportId.value}/final`, {
      method: "PUT",
      body: { final_md: draft.value }
    })
    editing.value = false
  } finally {
    saving.value = false
  }
}

const approve = async () => {
  if (!reportId.value) return
  approving.value = true
  try {
    await apiFetch(`/api/reports/${reportId.value}/approve`, { method: "POST" })
  } finally {
    approving.value = false
  }
}

const refine = async () => {
  if (!reportId.value || !concerns.value) return
  refining.value = true
  messages.value.push({ role: "user", content: concerns.value })
  try {
    const res = await apiFetch<any>(`/api/reports/${reportId.value}/agent-refine`, {
      method: "POST",
      body: { concerns: concerns.value }
    })
    draft.value = res.draft_md
    citations.value = res.citations
    messages.value.push({ role: "assistant", content: "Draft updated." })
    concerns.value = ""
  } finally {
    refining.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.layout {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 16px;
}
.main {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.hero {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  border-radius: 14px;
  background: linear-gradient(135deg, #f7fafc, #eef3f9);
  border: 1px solid #e6ecf4;
}
.hero h2 {
  margin: 0 0 8px 0;
}
.meta {
  color: #344054;
}
.user-card {
  margin-top: 10px;
  padding: 10px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid #e6ecf4;
}
.user-card.grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px 16px;
}
.section-label {
  grid-column: 1 / -1;
  margin-top: 6px;
  font-size: 12px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #98a2b3;
  font-weight: 700;
}
.user-line {
  font-size: 13px;
  color: #475467;
}
.hero-right {
  display: flex;
  align-items: flex-start;
}
.panel {
  background: #fff;
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #eef1f4;
}
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.actions {
  display: flex;
  gap: 8px;
}
.primary {
  background: var(--accent);
  border: none;
  color: white;
  padding: 10px 14px;
  border-radius: 8px;
}
button {
  background: var(--accent);
  border: none;
  color: white;
  padding: 8px 12px;
  border-radius: 6px;
}
textarea {
  width: 100%;
}
.preview {
  padding: 8px 0;
}
.citations {
  margin-top: 16px;
  border-top: 1px solid #eef1f4;
  padding-top: 12px;
}
.chat {
  position: sticky;
  top: 16px;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 120px);
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 14px;
  padding: 16px;
}
.chat h3 {
  margin-top: 0;
}
.messages {
  flex: 1;
  overflow: auto;
  padding: 8px;
  background: #111827;
  border-radius: 10px;
  margin-bottom: 8px;
}
.msg pre {
  background: #0b1220;
  padding: 8px;
  border-left: 3px solid #38bdf8;
  color: #e2e8f0;
}
.composer textarea {
  background: #0b1220;
  color: #e2e8f0;
  border: 1px solid #1f2937;
  border-radius: 8px;
}
.composer button {
  margin-top: 8px;
  width: 100%;
}
</style>
