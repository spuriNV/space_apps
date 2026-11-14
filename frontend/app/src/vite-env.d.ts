/// <reference types="vite/client" />
interface ImportMetaEnv {
  /** CropLytics API base, e.g. http://localhost:8000/api (dev default) or /api (production default) */
  readonly VITE_API_BASE?: string;
}
