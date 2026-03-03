<template>
  <UserShell>
    <div class="home">
      <div class="left">
        <h2>Chat + Intake</h2>
        <p class="hint">Focus on updating your profile or submitting a report request.</p>
        <p class="hint">Example: “Submit a drawdown strategy to minimize taxes.”</p>
      </div>
      <div class="chat">
        <div class="messages">
          <div v-for="(m, idx) in messages" :key="idx" :class="['msg', m.role]">
            <pre>{{ m.content }}</pre>
          </div>
        </div>
        <div class="composer">
          <textarea v-model="input" rows="3" placeholder="Type your message..."></textarea>
          <div class="row">
            <label class="file">
              Upload PDF (optional)
              <input type="file" accept="application/pdf" @change="onFile" />
            </label>
            <button @click="send" :disabled="sending">
              <span v-if="sending">Sending…</span>
              <span v-else>Send</span>
            </button>
          </div>
          <div class="quick-actions">
            <button
              v-for="q in quickQuestions"
              :key="q"
              class="quick-btn"
              @click="sendQuickQuestion(q)"
              :disabled="sending"
            >
              {{ q }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </UserShell>
</template>

<script setup lang="ts">
import UserShell from "~/components/UserShell.vue"

const apiFetch = useApiFetch()
const input = ref("")
const sending = ref(false)
const quickQuestions = [
  "A drawdown strategy to minimize taxes.",
  "Guidance on which accounts to draw from first (e.g., RRSP, TFSA, non-registered).",
  "A safe withdrawal amount we could reasonably expect."
]
const messages = ref<{ role: string; content: string }[]>([
  { role: "assistant", content: "Hi — ask me about drawdown strategy, account order, or safe withdrawal." }
])

const send = async () => {
  const text = input.value.trim()
  if (!text) return
  messages.value.push({ role: "user", content: text })
  sending.value = true
  try {
    const res = await apiFetch<any>("/api/users/1/chat", {
      method: "POST",
      body: { messages: messages.value }
    })
    messages.value.push({ role: "assistant", content: res.assistant_message })
    input.value = ""
  } finally {
    sending.value = false
  }
}

const onFile = async (e: Event) => {
  const target = e.target as HTMLInputElement
  const file = target.files ? target.files[0] : null
  target.value = ""
  if (!file) return
  sending.value = true
  try {
    const form = new FormData()
    form.append("file", file)
    const res = await apiFetch<any>("/api/users/1/chat/upload", {
      method: "POST",
      body: form
    })
    messages.value.push({ role: "assistant", content: res.assistant_message })
  } finally {
    sending.value = false
  }
}

const sendQuickQuestion = async (q: string) => {
  input.value = q
  await send()
}
</script>

<style scoped>
.home {
  display: grid;
  grid-template-columns: 1fr 875px;
  gap: 16px;
}
.left {
  padding: 16px;
}
.hint {
  color: #6b7280;
}
.chat {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #eef1f4;
  display: flex;
  flex-direction: column;
  height: calc(100vh - 220px);
}
.messages {
  flex: 1;
  overflow: auto;
  padding: 12px;
  background: #f9fafb;
}
.msg pre {
  background: #fff;
  border-left: 3px solid var(--accent);
  padding: 8px;
  white-space: pre-wrap;
  word-break: break-word;
}
.composer {
  padding: 12px;
  border-top: 1px solid #eef1f4;
}
.row {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  align-items: center;
}
textarea {
  width: 100%;
  margin-bottom: 8px;
}
.quick-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 16px;
  margin-bottom: 8px;
}
.quick-btn {
  background: #eef1f4;
  color: #111827;
  border: 1px solid #d5dbe3;
  font-size: 12px;
  border-radius: 999px;
  padding: 6px 10px;
  cursor: pointer;
}
.file {
  background: #f3f4f6;
  padding: 6px 10px;
  border-radius: 8px;
  cursor: pointer;
}
.file input {
  display: none;
}
button {
  background: var(--accent);
  border: none;
  color: white;
  padding: 8px 12px;
  border-radius: 6px;
}
</style>
