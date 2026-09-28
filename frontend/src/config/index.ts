/** Centralized runtime configuration. Only browser-safe values here. */
export const API_URL: string =
  (import.meta.env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") ||
  "http://127.0.0.1:8123";

export const API_PREFIX = "/api/v1";
