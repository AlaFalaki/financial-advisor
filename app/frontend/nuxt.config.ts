export default defineNuxtConfig({
  devtools: { enabled: false },

  runtimeConfig: {
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || "http://localhost:8000",
      apiKey: process.env.NUXT_PUBLIC_API_KEY || ""
    }
  },

  compatibilityDate: "2026-02-26"
})
