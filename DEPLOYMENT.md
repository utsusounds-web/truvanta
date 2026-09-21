# Getting TRUVANTA online

This is the answer to "where do I go online from" — right now, the app only
runs on your own computer (`localhost`), which is why no one else can open it.
This guide gets it onto the internet, on a real address, that you and your
staff can open from any phone or computer.

You need **one thing** installed on the server you deploy to: **Docker**.
Everything else — the database, the backend, the website — is handled
automatically by one command.

---

## Option A — the fast way (recommended)

### 1. Get a server
Rent a small VPS (virtual private server). Any of these work — pick one,
sign up, and note the IP address it gives you:
- DigitalOcean (Droplet) — from about $6/month
- Hetzner Cloud — cheaper, works well from Africa/Europe
- AWS Lightsail
- Any provider that lets you pick "Ubuntu 22.04" or "Docker" as the image

A $6–12/month plan (1 CPU, 1–2GB RAM) is enough for a small/medium business.

### 2. Install Docker on the server
SSH into your new server, then run:
```bash
curl -fsSL https://get.docker.com | sh
```

### 3. Copy TRUVANTA onto the server
From your own computer:
```bash
scp -r truvanta root@YOUR_SERVER_IP:/opt/truvanta
```
(Replace `YOUR_SERVER_IP` with the address your hosting provider gave you.)

### 4. Configure it
SSH into the server, then:
```bash
cd /opt/truvanta
cp .env.example .env
nano .env        # fill in SECRET_KEY and DB_PASSWORD — see below
```
To generate a `SECRET_KEY`, run this once and paste the result in:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```
For `DB_PASSWORD`, pick any password — Docker creates the database for you.

Also set:
```
ALLOWED_HOSTS=YOUR_SERVER_IP
FRONTEND_URL=http://YOUR_SERVER_IP
```
(Once you have a real domain name pointed at the server, use that instead
of the IP address — see "Adding a domain and HTTPS" below.)

### 5. Start everything
```bash
docker compose up -d
```
That's the one command. It builds the app, sets up the database, and starts
everything. The first run takes a few minutes; after that, restarts are fast.

### 6. Open it
Go to `http://YOUR_SERVER_IP` in a browser. You should see the TRUVANTA
login/signup screen. Register your account and business as normal.

### 7. Create your platform-admin account
The account you register with `docker compose up` running is a normal
business owner account. To get access to the Platform Admin panel (Billing →
Plans, Rent Mode, etc.), mark yourself as staff:
```bash
docker compose exec backend python manage.py createsuperuser
```
Follow the prompts (you can use the same email you registered with, or a
new one) — this account can log into `/admin/` (Django's built-in admin) and
also sees the "Platform Admin" link in the app's sidebar.

---

## Adding a domain and HTTPS

Running on a bare IP address works, but a real domain (e.g.
`app.yourbusiness.com`) looks trustworthy and lets you add HTTPS (the
padlock icon), which browsers increasingly require for things like camera
access.

1. Buy a domain (Namecheap, GoDaddy, etc. — a few dollars/year).
2. Point it at your server: in your domain's DNS settings, add an "A record"
   for `app` (or `@` for the bare domain) pointing to your server's IP.
3. Install [Caddy](https://caddyserver.com/) or use
   [Nginx Proxy Manager](https://nginxproxymanager.com/) in front of the
   `frontend` container — both can get you free, auto-renewing HTTPS
   certificates in a few minutes. This is a separate, optional setup step;
   ask if you want help with this specific piece.
4. Update `.env`: set `ALLOWED_HOSTS` and `FRONTEND_URL` to your real domain,
   then `docker compose up -d --build` to apply it.

---

## Everyday operations

**Updating the app after I send you new code:**
```bash
cd /opt/truvanta
docker compose down
# replace the files with the new version
docker compose up -d --build
```

**Checking logs if something looks wrong:**
```bash
docker compose logs -f backend
docker compose logs -f frontend
```

**Backing up your data** (the database is the important part):
```bash
docker compose exec db pg_dump -U truvanta truvanta > backup-$(date +%F).sql
```
Run this regularly (a daily cron job is ideal) and keep the `.sql` files
somewhere safe — they're your entire business's data.

**Stopping everything:**
```bash
docker compose down
```
(Your data stays safe in Docker's storage — this doesn't delete anything.)

---

## Option B — no server management at all

If renting and managing a server feels like too much, managed platforms
(Railway, Render, Fly.io) can run this same `docker-compose.yml` setup with
far less manual work, for a monthly fee that's usually similar to a VPS.
This is worth doing if you'd rather pay a bit more and never touch a
terminal — ask if you'd like the walkthrough for one of these specifically.

---

## Turning on paid features

Once you're online and ready to start charging businesses for premium
features, go to **Platform Admin → Rent Mode** inside the app and switch it
on. Nothing else needs to change — this is the single switch that turns
enforcement on and off, any time.
