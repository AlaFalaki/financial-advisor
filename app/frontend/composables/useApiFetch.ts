export const useApiFetch = () => {
  const config = useRuntimeConfig()

  return async <T>(path: string, options: any = {}): Promise<T> => {
    const apiKey = String(config.public.apiKey || "").trim()
    const headers = {
      ...(options.headers || {}),
      ...(apiKey ? { "x-api-key": apiKey } : {})
    }
    return await $fetch<T>(`${config.public.apiBase}${path}`, {
      ...options,
      headers
    })
  }
}

