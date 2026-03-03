<template>
  <div class="app" :class="roleClass">
    <header class="topbar">
      <div class="brand">Advisor-in-the-loop Retirement Drawdown Assistant</div>
      <div class="mock-auth">
        <span>Role:</span>
        <select v-model="selectedUser" @change="switchUser">
          <option value="1">User</option>
          <option value="2">Advisor</option>
        </select>
      </div>
    </header>
    <NuxtPage />
  </div>
</template>

<script setup lang="ts">
const selectedUser = ref("1")
const roleClass = ref("user-theme")
const router = useRouter()
const route = useRoute()
const apiFetch = useApiFetch()

const switchUser = async () => {
  const res = await apiFetch<any>("/api/mock/switch", {
    method: "POST",
    body: { user_id: Number(selectedUser.value) }
  })
  roleClass.value = res.role === "ADVISOR" ? "advisor-theme" : "user-theme"
  if (res.role === "ADVISOR") {
    router.push("/advisor/queue")
  } else {
    router.push("/user/chat-intake")
  }
}

onMounted(async () => {
  if (localStorage.getItem("app_auth_ok") !== "1") {
    if (route.path !== "/login") {
      await router.push(`/login?next=${encodeURIComponent(route.fullPath)}`)
    }
    return
  }
  const res = await apiFetch<any>("/api/mock/session")
  selectedUser.value = String(res.user_id)
  roleClass.value = res.role === "ADVISOR" ? "advisor-theme" : "user-theme"
  if (res.role === "ADVISOR") {
    router.push("/advisor/queue")
  } else {
    router.push("/user/chat-intake")
  }
})
</script>

<style>
:root {
  --font-body: "Space Grotesk", system-ui, sans-serif;
  --font-display: "DM Serif Display", serif;
  --user-bg: #f9f2ec;
  --user-accent: #d17a5a;
  --advisor-bg: #eef5fb;
  --advisor-accent: #2c5aa0;
  --bg: #ffffff;
  --accent: #000000;
  --ink: #1b1b1b;
}
.user-theme {
  --bg: var(--user-bg);
  --accent: var(--user-accent);
}
.advisor-theme {
  --bg: var(--advisor-bg);
  --accent: var(--advisor-accent);
}
body {
  margin: 0;
  font-family: var(--font-body);
  color: var(--ink);
  background: var(--bg);
}
.app {
  min-height: 100vh;
}
.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  border-bottom: 1px solid #ddd;
}
.brand {
  font-family: var(--font-display);
  font-size: 20px;
}
.mock-auth select {
  margin-left: 8px;
}
</style>
