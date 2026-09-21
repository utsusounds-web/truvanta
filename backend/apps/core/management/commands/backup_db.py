"""Backs up the database and records the attempt in BackupLog, which
is what powers the 'last backed up' indicator in Platform Admin.

Point a cron job (or, in Docker, the host machine's crontab calling
`docker compose exec`) at this on a schedule — daily is reasonable
for a small business:

    0 2 * * * cd /opt/truvanta && docker compose exec -T backend python manage.py backup_db

Works with both backends configured in settings.py:
- Postgres: shells out to `pg_dump` (must be on PATH — already true
  inside the backend Docker image).
- SQLite (default local dev): just copies the .sqlite3 file, since
  there's no separate server process to dump from.
"""
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import BackupLog

BACKUP_DIR = Path(settings.BASE_DIR) / "backups"


class Command(BaseCommand):
    help = "Back up the database and record the attempt (see BackupLog / Platform Admin)."

    def handle(self, *args, **options):
        BACKUP_DIR.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        db = settings.DATABASES["default"]
        engine = db["ENGINE"]

        log = BackupLog.objects.create(status="failed")  # flipped to success below if it works
        try:
            if "postgresql" in engine:
                filename = f"backup-{timestamp}.sql"
                filepath = BACKUP_DIR / filename
                env_args = []
                if db.get("PASSWORD"):
                    import os
                    os.environ["PGPASSWORD"] = db["PASSWORD"]
                cmd = [
                    "pg_dump",
                    "-h", db.get("HOST", "localhost"),
                    "-p", str(db.get("PORT", "5432")),
                    "-U", db.get("USER", "postgres"),
                    "-d", db["NAME"],
                    "-f", str(filepath),
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
                if result.returncode != 0:
                    raise RuntimeError(result.stderr[:1000])
            else:
                # SQLite — just copy the file.
                filename = f"backup-{timestamp}.sqlite3"
                filepath = BACKUP_DIR / filename
                shutil.copy(db["NAME"], filepath)

            log.status = "success"
            log.filename = filename
            log.size_bytes = filepath.stat().st_size
            log.completed_at = timezone.now()
            log.save(update_fields=["status", "filename", "size_bytes", "completed_at"])
            self.stdout.write(self.style.SUCCESS(f"Backed up to {filepath} ({log.size_bytes} bytes)."))

        except Exception as e:  # noqa: BLE001 — always record the failure, never crash the cron job silently
            log.error = str(e)[:1000]
            log.save(update_fields=["error"])
            self.stderr.write(self.style.ERROR(f"Backup failed: {e}"))

        # Keep only the 30 most recent backup files on disk — the log
        # rows themselves are cheap and kept indefinitely, but the
        # actual dump files would otherwise grow without bound.
        all_backups = sorted(BACKUP_DIR.glob("backup-*"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in all_backups[30:]:
            old.unlink(missing_ok=True)
