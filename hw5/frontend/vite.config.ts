import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// The desk runs on http://localhost:5173 and calls the FastAPI backend directly at
// http://localhost:8000 (see src/api.ts). The backend allows this origin via CORS.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
})
