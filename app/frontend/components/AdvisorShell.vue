<template>
  <div class="shell advisor">
    <nav class="nav">
      <NuxtLink to="/advisor/queue">Queue</NuxtLink>
      <NuxtLink to="/advisor/retrieve">Retrieve Test</NuxtLink>
    </nav>
    <section class="content">
      <slot />
    </section>
  </div>
</template>

<style scoped>
.shell.advisor {
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
