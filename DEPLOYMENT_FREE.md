# Getting TRUVANTA online for free — Render.com

This is the free alternative to the paid-VPS guide in `DEPLOYMENT.md`. It
gets you a real, working, globally-accessible URL with **no credit card**
and **no monthly cost** — with two honest trade-offs explained below so
there are no surprises.

I checked this against Render's current (2026) terms before writing it —
free tiers change often, so if anything here looks different when you
sign up, that's Render having updated something, not this guide being wrong.

## The two honest trade-offs of free hosting

1. **The free database expires after 90 days** — not 90 days of
   inactivity, 90 days from when you create it, period. You'll need to
   create a new free database and point the app at it every 3 months, or
   move to a paid database (a few dollars/month) once the business is
   real. This is Render's policy, not something I can work around.
2. **The free web service "sleeps"** after 15 minutes with no traffic,
   and takes 30–60 seconds to wake back up on the next request. Fine for
   testing and early use; annoying if a cashier is standing there waiting
   for the page to load. Upgrading the web service alone (~$7/month)
   removes this; the database can often stay free longer if you recreate
   it each cycle.

Neither of these affects your data safety — they're about availability
and cost, not risk of losing anything (make regular backups regardless,
per the main deployment guide).

## Steps

### 1. Push your code to GitHub
Render deploys from a GitHub repository, not a zip file. If you don't
already have one:
```bash
cd truvanta
git init
git add .
git commit -m "Initial commit"
```
Then create a new (private is fine) repository on github.com and follow
its instructions to push this code to it.

### 2. Sign up at render.com
No credit card required for the free tier.

### 3. Create the database first
- Dashboard → **New** → **PostgreSQL**
- Name it anything (e.g. `truvanta-db`)
- Choose the **Free** plan
- Once created, copy the **Internal Database URL** — you'll need it in step 4.

### 4. Create the backend web service
- Dashboard → **New** → **Web Service**
- Connect your GitHub repo, and set:
  - **Root Directory**: `backend`
  - **Runtime**: Docker (it will use the `Dockerfile` already in `backend/`)
  - **Plan**: Free
- Under **Environment Variables**, add:
  - `SECRET_KEY` — generate with `python -c "import secrets; print(secrets.token_urlsafe(50))"`
  - `DEBUG` — `false`
  - `DB_ENGINE` — `postgres`
  - `DATABASE_URL` — paste the Internal Database URL from step 3
    (Django needs this parsed into parts — see the note below)
  - `ALLOWED_HOSTS` — your Render backend URL once it's assigned, e.g. `truvanta-backend.onrender.com`
  - `FRONTEND_URL` / `CORS_ALLOWED_ORIGINS` — your frontend's Render URL (set after step 5)
- Deploy. Render gives you a URL like `https://truvanta-backend.onrender.com`.

**Note on `DATABASE_URL`**: this project's `settings.py` currently expects
separate `DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT` variables
rather than one combined URL. Render's Postgres gives you both formats —
use the individual host/port/name/user/password values shown on the
database's Render page instead of the combined URL, and set those five
variables individually to match what `config/settings.py` reads.

### 5. Create the frontend static site
- Dashboard → **New** → **Static Site**
- Same GitHub repo, but:
  - **Root Directory**: `frontend`
  - **Build Command**: `npm install && npm run build`
  - **Publish Directory**: `dist`
- Add environment variable `VITE_API_BASE_URL` set to your backend URL
  plus `/api`, e.g. `https://truvanta-backend.onrender.com/api`
- Deploy. Render gives you a URL like `https://truvanta-frontend.onrender.com`
  — **this is the address you give to anyone who needs to use the app.**

### 6. Finish setup
- Go back to the backend service's environment variables and set
  `FRONTEND_URL` and `CORS_ALLOWED_ORIGINS` to the frontend URL from step 5,
  then redeploy the backend so the CORS fix from earlier actually allows
  the two to talk to each other.
- Open a **Shell** on the backend service (Render's dashboard has this
  built in — no local terminal needed) and run:
  ```bash
  python manage.py migrate
  python manage.py createsuperuser
  ```
  (Not needed if you're relying on the first-account-becomes-admin
  behavior — just register normally instead.)

### 7. You're online
Visit your frontend URL from any device, anywhere. That's the link to
share with staff or use yourself, from a phone, a laptop, anywhere with
internet.

## When you outgrow free

Once real money is moving through the app, move off the free tier:
upgrade the web service (removes the sleep/wake delay) and move the
database to a paid Render plan or an external one (no more 90-day
expiry). Everything else about the setup stays exactly the same —
nothing to rebuild, just a plan change in Render's dashboard.
