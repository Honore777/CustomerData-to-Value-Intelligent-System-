# Deploying the Frontend to Vercel (Vite + React)

Minimal steps to deploy the Vite frontend to Vercel.

1) Build settings
- Framework: select `Other` or `Vite` (Vercel auto-detects). Use the following commands:
  - Build Command: `npm run build`
  - Output Directory: `dist`

2) Environment variables (set these in Vercel project settings)
- `VITE_API_URL` — backend base URL (e.g. `https://api.your-backend.onrender.com/api`)
- `VITE_SUPABASE_URL` / `VITE_SUPABASE_KEY` — if frontend needs Supabase client access (only if used by frontend)

3) Important notes
- Vite exposes env vars only when prefixed with `VITE_`. The backend needs `FRONTEND_URL` set to the Vercel URL for invite links.
- If backend uses httponly cookies, make sure frontend requests include `credentials: 'include'` and CORS is configured on the backend for the frontend origin.

4) Local verification
```bash
# build locally
npm install
npm run build
# serve the dist folder
npx serve dist
```

If you want, I can add a Vercel `vercel.json` example and a small script to copy environment variables between Render and Vercel recommendations.
