export default defineNuxtRouteMiddleware((to) => {
  if (!import.meta.client) return

  const isLoginRoute = to.path === "/login"
  const isAuthed = localStorage.getItem("app_auth_ok") === "1"

  if (!isAuthed && !isLoginRoute) {
    return navigateTo(`/login?next=${encodeURIComponent(to.fullPath)}`)
  }

  if (isAuthed && isLoginRoute) {
    const next = typeof to.query.next === "string" ? to.query.next : "/"
    return navigateTo(next)
  }
})
