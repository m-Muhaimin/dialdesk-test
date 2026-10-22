# DialDesk — multi-tenant AI voice receptionist

Businesses sign up, configure an AI receptionist, and add one `<script>` tag to their website. Visitors tap **Talk to us**, speak to the agent in the browser (WebRTC → Pipecat), and the agent checks real availability, books appointments and captures leads. Owners see everything in a dashboard.

**Stack:** Next.js 16 (App Router) · Supabase (Auth + Postgres + RLS) · Pipecat · Groq Whisper STT · Ollama (default) or Groq LLM · local Kokoro TTS · Stripe (optional) · Resend (optional) · Tailwind CSS 4.
**No build-time env needed.** Every setting is read at runtime, so one build runs anywhere.

## How it works

```
Visitor's browser ──WebRTC audio──────────────► Pipecat voice service
      │ SDP offer                                    │ Groq Whisper → Ollama/Groq → local Kokoro
      ▼                                              │ signed call token scopes the session
/api/realtime/session ─► /api/realtime/connect ──────┘
                                                     │ calls availability/booking tools
                                                     ▼
                                     /api/realtime/tool ─► Supabase
```

* Browser audio goes to the Pipecat service. Prompts, tool definitions and the Groq key stay server-side.
* The LLM runs on Ollama locally by default, or on Groq when `LLM_PROVIDER=groq`. Kokoro generates speech locally; OpenAI Realtime is not used.
* Bookings are validated server-side (opening hours, slot grid, lead time, 120-day window) and a **unique index** prevents double-booking even under races.
* Dashboard reads/writes go through Supabase **RLS**; the public voice path uses the service role but every query is scoped by a business id taken from a signed token.

## Setup (10 minutes)

1. **Supabase** → create a project → SQL Editor → run `supabase/schema.sql`.
   Authentication → URL Configuration: set *Site URL* to your app URL and add `https://YOUR-APP/auth/callback` to *Redirect URLs*.
2. **Env vars** → copy `.env.example` to `.env` and fill in: `APP_SECRET` (`openssl rand -base64 48`), the three Supabase values, and a valid `GROQ_API_KEY`.
3. **Pick the LLM** (see *Choosing the LLM provider* below). With the default `LLM_PROVIDER=ollama`, **start Ollama** with the model in `LLAMA_MODEL` (default `qwen2.5:3b`). The model **must support tool calls** — the receptionist books appointments and captures leads through `check_availability`, `book_appointment` and `capture_lead`. Ollama rejects tool calls for models without that support, and the call then dies after the greeting. `python voice-pipeline\local_voice.py --check` verifies this before the service starts, and `ollama pull qwen2.5:3b` fetches a known-good model. With `LLM_PROVIDER=groq` no local model is needed: `--check` validates the Groq key and chat model instead.
4. **Install and run the voice service** in one terminal: `python -m pip install -r voice-pipeline\requirements-local.txt`, then `python voice-pipeline\web_voice.py`. The service reads `APP_URL` and `GROQ_API_KEY` from the project `.env`/`.env.local` files.
5. **Run the app** in another terminal: `npm install && npm run dev` → http://localhost:3000 → sign up → onboarding → Agent settings → add your site under *Allowed websites* → make a test call from your public page (`/b/<slug>`). The dev launcher gives Supabase values in the project env files precedence over inherited shell values.

### Choosing the LLM provider (voice service)

The voice service picks its LLM with one variable, so the operator can switch without touching code:

| Variable | Default | Notes |
|---|---|---|
| `LLM_PROVIDER` | `ollama` | `ollama` keeps the fully offline path. `groq` sends the conversation to Groq. Any other value stops the service at startup with `LLM_PROVIDER must be 'ollama' or 'groq'`. |
| `GROQ_LLM_MODEL` | `openai/gpt-oss-120b` | Groq chat model, used only when `LLM_PROVIDER=groq`. Groq ids are exact. |
| `GROQ_BASE_URL` | `https://api.groq.com/openai/v1` | Groq OpenAI-compatible base URL, used only when `LLM_PROVIDER=groq`. |

**Pick `groq` when the local model cannot be trusted with tools.** The receptionist books and captures leads through `check_availability`, `book_appointment` and `capture_lead`, so a model that answers from memory breaks the flow silently: small local models routinely say "9:00 AM tomorrow is available" without calling anything. On an 8 GB CPU-only box `qwen2.5:1.5b` does exactly that, and `gemma3:1b` has no tool support at all, so the call dies after the greeting with a 400. `openai/gpt-oss-120b` on Groq is the recommended local-dev default when RAM is tight — it resolves the date and issues the real tool call in under a second. Ollama is still fine with a tool-capable model such as `qwen2.5:3b`, which just needs more RAM. The Groq key (`GROQ_API_KEY`) is shared with Whisper STT; both entry points read the provider and the Groq key from the process environment and the project env files, and `python voice-pipeline\local_voice.py --check` prints the active provider plus the model it validated before any audio starts.

Microphone access requires **HTTPS** (localhost is exempt), so use a real domain in production.

### Local stack behind a public tunnel

To test from a browser that is not on `localhost`, run three processes. The tunnel exposes only the app; the Pipecat service stays local and is reached over loopback.

```bash
# 1. voice service — reads GROQ_API_KEY from the project env files
DIALDESK_APP_URL=http://localhost:3010 python -m uvicorn web_voice:app --app-dir voice-pipeline --host 127.0.0.1 --port 7860

# 2. app in production mode (npm run build first)
npm start -- -p 3010

# 3. tunnel
ngrok http 3010
```

In `.env.local` set `APP_URL=https://<subdomain>.ngrok-free.dev` (the browser needs a secure context for `getUserMedia`) and `DIALDESK_APP_URL=http://localhost:3010` (the voice service calls the app back directly instead of hairpinning through the tunnel). `VOICE_PIPELINE_URL` stays `http://127.0.0.1:7860`.

Both `npm run dev` and `npm start` prefer the project env files over inherited shell values. Next.js does not override variables that are already set, so a stale `SUPABASE_*` value in your shell or Windows user environment would otherwise shadow `.env.local`; the launchers drop the inherited values first.

The tunnel carries HTTP only. WebRTC media flows directly between the browser and the Pipecat service, so it needs a reachable UDP path — see *Known limits*.

## Deploy

| Platform | Steps |
|---|---|
| **Vercel + VPS voice** | Vercel serves the Next.js app only. Run `voice-pipeline/Dockerfile` on a Linux VPS with public HTTPS and UDP connectivity for WebRTC. Set `VOICE_PIPELINE_URL` in Vercel to the VPS voice-service URL and `DIALDESK_APP_URL` on the VPS to the canonical Vercel app URL. The Pipecat service is deliberately not a Vercel Function: its dependency bundle exceeds Vercel's 500 MB function limit and it needs long-lived WebRTC/UDP media handling. |
| **Render / Railway** | Deploy the Next.js app and `voice-pipeline/Dockerfile` as separate services. Set `VOICE_PIPELINE_URL` in the app and `DIALDESK_APP_URL` in the voice service. |
| **VPS + Docker** | On a Linux Docker host, copy `.env.example` to `.env`, set `APP_URL=https://your.domain` and `DOMAIN=your.domain`, configure Groq and Ollama, then run `docker compose up -d --build`. Caddy gets the HTTPS certificate automatically. The voice service uses host networking for WebRTC media; allow its UDP traffic through the firewall. |
| **VPS + PM2** | Deploy Next.js as usual and run the Python voice service separately with `uvicorn web_voice:app --host 0.0.0.0 --port 7860` from `voice-pipeline`. Set `VOICE_PIPELINE_URL` in Next.js and `DIALDESK_APP_URL` in the voice service. |

Liveness check: `GET /api/health`. Readiness check: `GET /api/health?deep=1` (also checks the database). Run `supabase/schema.sql` before deploying, and re-run it on existing projects to install the atomic monthly-call reservation and migrate existing voice selections.

Embed snippet (shown in the dashboard):
```html
<script src="https://YOUR-APP/widget.js" data-business="BUSINESS_ID" defer></script>
```
Optional attributes: `data-color="#14232F"`, `data-position="left"`.

## Environment variables

| Variable | Required | Notes |
|---|---|---|
| `APP_SECRET` | yes | 32+ chars; signs embed/call tokens. Rotating it invalidates open sessions only. |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | yes | Service role is server-only. Never expose it. |
| `APP_URL` | production | Canonical HTTPS origin, without a path. HTTP is allowed only for loopback (`localhost`, `127.0.0.1`, or `::1`) to support local production-build testing. |
| `VOICE_PIPELINE_URL` | production | Public HTTPS URL of the separately hosted Pipecat service; defaults to `http://127.0.0.1:7860` in development. Set this in Vercel's app environment. |
| `GROQ_API_KEY` | voice service | Whisper STT credentials. Audio is sent to Groq for transcription. |
| `DIALDESK_APP_URL` | voice service | Canonical app URL the Pipecat VPS uses for signed session configuration and booking tools. Set this on the voice host. |
| `LLAMA_BASE_URL`, `LLAMA_MODEL` | voice service | Ollama OpenAI-compatible local endpoint and loaded model name, used when `LLM_PROVIDER=ollama` (the default). Despite the compatibility protocol, no OpenAI API is used. The model must support tool calls. |
| `LLM_PROVIDER` | no | `ollama` (default, fully offline) or `groq` (hosted chat model). Any other value stops the service at startup. |
| `GROQ_LLM_MODEL`, `GROQ_BASE_URL` | no | Groq chat model and API base used when `LLM_PROVIDER=groq`. Defaults `openai/gpt-oss-120b` and `https://api.groq.com/openai/v1`. |
| `KOKORO_VOICE`, `KOKORO_SPEED` | no | Default local Kokoro voice and speaking rate. Per-business voice selection overrides the voice. |
| `FREE_CALLS_PER_MONTH` / `PRO_CALLS_PER_MONTH` | no | Defaults 20 / 500. Your main cost control. |
| `MAX_CALL_SECONDS` | no | Default 600. |
| `STRIPE_SECRET_KEY`, `STRIPE_PRICE_PRO`, `STRIPE_WEBHOOK_SECRET` | no | Enables the Upgrade button. Webhook endpoint: `/api/stripe/webhook` with events `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`. |
| `RESEND_API_KEY`, `RESEND_FROM_EMAIL` | no | Booking confirmation emails. |

## What was fixed vs. the original starter

| Gap in the starter | Here |
|---|---|
| Empty/placeholder source files, JSX inside `.ts`, no schema | Complete, type-checked app and SQL schema with RLS |
| `Access-Control-Allow-Origin: *` on realtime + booking endpoints | No CORS at all; the API is same-origin and gated by signed, expiring tokens |
| Anyone could mint realtime sessions (cost abuse) | Signed embed token, per-IP and per-business rate limits, monthly per-plan call cap |
| Tenant isolation undefined; service role everywhere | RLS for dashboard; service role only in server routes, always scoped by token business id; billing columns not writable by users |
| No CSP; framing rules would break the widget | Strict CSP + `X-Frame-Options: DENY` everywhere except `/embed/*`, which is frameable but checks the parent origin against an allow-list |
| `.env.local` committed, `.gitignore` lacked `.env*` | `.env*` ignored (only `.env.example` tracked) |
| Wrong package name; README promised phone calls with no telephony | Honest scope (browser voice); see below |
| No tests, CI, license, health check | 31 unit tests, GitHub Actions CI, MIT, `/api/health` |
| Single hosting path (Hostinger + CloudPanel) | Vercel, Render, Railway, Docker+Caddy, PM2 |

## Known limits (read before selling this)

* **Browser voice only — no phone numbers.** Real inbound phone calls need a telephony transport; it is not included.
* Groq provides transcription, so voice calls require an active Groq key and internet access. Chat inference runs on the configured Ollama model, or on Groq when `LLM_PROVIDER=groq` (that path needs internet as well); speech synthesis always runs locally on Kokoro.
* Production WebRTC needs a publicly reachable voice service and UDP connectivity. STUN helps with NAT traversal; strict NATs/firewalls may require a TURN server. A verified local run returned only `typ host` and `typ srflx` ICE candidates and no `typ relay`, so a browser on another network cannot reach the voice service through an HTTP tunnel: the voice service needs a public IP plus a TURN server, or the browser must be on the same network.
* **Request rate limiting is in-memory.** It is per process, so on Vercel/serverless or multiple instances each instance counts separately; use shared Redis/Upstash for distributed limits. The monthly call cap is reserved atomically in Postgres and remains exact across instances.
* **Allowed-websites check uses the iframe `Referer`.** It stops casual copy-paste embedding but a determined attacker can forge it; the call cap and rate limits bound the damage.
* A call is capped client-side (`MAX_CALL_SECONDS`) and by the 30-minute call token for tools.
* No admin/super-user console, team invitations (schema supports multiple members) or call summaries yet.
* Calls are recorded as text transcripts. Check consent/recording laws in your customers' jurisdictions; the widget shows a short AI/transcription notice.

## Verification status

Verification: run the Node tests/typecheck/build and `python -m unittest discover -s voice-pipeline -p "test_*.py"`. A live browser call also requires the configured Groq key, the configured LLM (`LLM_PROVIDER` — a running Ollama model or a reachable Groq model), the Pipecat service, microphone permission and a working WebRTC network path. Validate one real call and booking against your Supabase project before going live.
