import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from database.db import init_db, init_db_v2, init_db_v3, init_db_v4, init_db_v5, init_db_v6, seed_demo_data, seed_demo_user
from engines.alert_presets import seed_presets
init_db()
init_db_v2()
init_db_v3()
init_db_v4()
init_db_v5()
init_db_v6()
seed_demo_data()
seed_demo_user()
seed_presets()
print("DB_READY - 12 sessions seeded")
