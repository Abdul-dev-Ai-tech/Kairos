"""Explicit one-time release management against the configured cloud database."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
path = root / '.env.vercel'
if not path.exists():
    raise SystemExit('Run vercel env pull .env.vercel --environment=production first. Keep that file private.')
load_dotenv(path, override=True)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.vercel')
if os.environ['DJANGO_SETTINGS_MODULE'] != 'config.settings.vercel':
    raise SystemExit('The release environment must use config.settings.vercel.')
from django.core.management import execute_from_command_line
execute_from_command_line([str(root / 'manage.py'), *sys.argv[1:]])
