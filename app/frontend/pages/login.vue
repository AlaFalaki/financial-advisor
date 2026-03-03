<template>
  <div class="wrap">
    <div class="card">
      <h2>Dashboard Login</h2>
      <p>Enter passcode to access the dashboard.</p>
      <input
        v-model="passcode"
        type="password"
        placeholder="Passcode"
        @keydown.enter="login"
      />
      <button @click="login" :disabled="loading">
        <span v-if="loading">Checking…</span>
        <span v-else>Login</span>
      </button>
      <div v-if="error" class="error">{{ error }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
const route = useRoute()
const apiFetch = useApiFetch()

const passcode = ref("")
const error = ref("")
const loading = ref(false)

const login = async () => {
  error.value = ""
  if (!passcode.value) {
    error.value = "Passcode is required."
    return
  }
  loading.value = true
  try {
    await apiFetch("/api/login", {
      method: "POST",
      body: { passcode: passcode.value }
    })
    localStorage.setItem("app_auth_ok", "1")
    const next = typeof route.query.next === "string" ? route.query.next : "/"
    await navigateTo(next)
  } catch {
    error.value = "Invalid passcode."
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.wrap {
  min-height: calc(100vh - 80px);
  display: grid;
  place-items: center;
}
.card {
  width: min(420px, calc(100vw - 32px));
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  padding: 16px;
  display: grid;
  gap: 10px;
}
input {
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
  padding: 10px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
}
button {
  background: var(--accent);
  border: none;
  color: white;
  box-sizing: border-box;
  padding: 10px 12px;
  border-radius: 8px;
}
.error {
  color: #b91c1c;
  font-size: 14px;
}
</style>
