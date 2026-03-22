import gzip
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a local database backup snapshot."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output-dir",
            default=str(Path(settings.BASE_DIR).parent / "data" / "backups"),
            help="Directory to write backup files into.",
        )
        parser.add_argument(
            "--gzip",
            action="store_true",
            help="Compress the backup with gzip.",
        )

    def handle(self, *args, **options):
        output_dir = Path(options["output_dir"]).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
        db = settings.DATABASES["default"]
        engine = db.get("ENGINE", "")

        if engine.endswith("sqlite3"):
            source = Path(db["NAME"]).resolve()
            if not source.exists():
                raise CommandError(f"SQLite database not found: {source}")

            target = output_dir / f"backup-{timestamp}.sqlite3"
            shutil.copy2(source, target)
            final_path = self._maybe_gzip(target, options["gzip"])
            self.stdout.write(self.style.SUCCESS(f"Backup created: {final_path}"))
            return

        if not engine.endswith("postgresql"):
            raise CommandError(f"Unsupported database engine: {engine}")

        dump_path = output_dir / f"backup-{timestamp}.sql"
        env = os.environ.copy()
        if db.get("PASSWORD"):
            env["PGPASSWORD"] = str(db["PASSWORD"])

        command = [
            "pg_dump",
            "--host",
            str(db.get("HOST") or ""),
            "--port",
            str(db.get("PORT") or "5432"),
            "--username",
            str(db.get("USER") or ""),
            "--dbname",
            str(db.get("NAME") or ""),
            "--file",
            str(dump_path),
            "--no-owner",
            "--no-privileges",
        ]

        try:
            subprocess.run(command, check=True, env=env)
        except FileNotFoundError as exc:
            raise CommandError("pg_dump tapılmadı. PostgreSQL client tools quraşdırılmalıdır.") from exc
        except subprocess.CalledProcessError as exc:
            raise CommandError(f"pg_dump xətası: {exc}") from exc

        final_path = self._maybe_gzip(dump_path, options["gzip"])
        self.stdout.write(self.style.SUCCESS(f"Backup created: {final_path}"))

    def _maybe_gzip(self, path: Path, compress: bool) -> Path:
        if not compress:
            return path

        gz_path = path.with_suffix(path.suffix + ".gz")
        with path.open("rb") as src, gzip.open(gz_path, "wb") as dst:
            shutil.copyfileobj(src, dst)
        path.unlink()
        return gz_path
