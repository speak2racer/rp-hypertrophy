"""
Run once to grant admin rights to a user.
Usage: python set_admin.py <username>
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from database import set_admin

username = sys.argv[1] if len(sys.argv) > 1 else "spischek"
set_admin(username, True)
print(f"✅ Admin-Rechte für '{username}' gesetzt.")
