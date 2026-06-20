# Not used — we went with Vercel

The dashboard control backend lives at **`/api/control.js`** (a Vercel serverless
function), because you already run Vercel for myadventurecostarica.com.

You can ignore or delete this `control-worker/` folder. `worker.js` here is only a
Cloudflare-flavoured copy kept as a fallback; it is not deployed.
