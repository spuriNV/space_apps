import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// The app reads everything real from the Field Shift API (src/api.ts, VITE_API_BASE). No dev-only file bridge:
// a production build served by the backend at / with the API at /api behaves exactly like dev.
export default defineConfig({
  base: '/',
  plugins: [react()],
  server: { port: 5170, strictPort: true },
  preview: { port: 5170, strictPort: true },
});
