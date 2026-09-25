import sys
from pathlib import Path

# Daftarkan root proyek ke sys.path secara otomatis untuk semua test
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
