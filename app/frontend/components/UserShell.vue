<template>
  <div class="shell user">
    <nav class="nav">
      <NuxtLink to="/">Chat + Intake</NuxtLink>
      <NuxtLink to="/user/profile">Profile</NuxtLink>
      <NuxtLink to="/user/reports">Reports</NuxtLink>
    </nav>
    <section class="content">
      <slot />
    </section>
  </div>
</template>

<style scoped>
.shell.user {
  background: var(--bg);
  min-height: calc(100vh - 60px);
  padding: 24px;
}
.nav {
  display: flex;
  gap: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid rgba(0,0,0,0.1);
}
.content {
  padding-top: 16px;
}
.nav a {
  color: var(--accent);
  text-decoration: none;
  font-weight: 600;
}
</style>
