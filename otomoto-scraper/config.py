from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "otomoto"
SESSION_STATE_FILE = DATA_DIR / ".session-state.json"

# URL = "https://www.otomoto.pl/osobowe/suzuki/vitara/od-2016?search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000"
# CSV_FILE = str(DATA_DIR / "suzuki-vitara.csv")

# URL = "https://www.otomoto.pl/osobowe/suzuki/vitara/od-2016?page=2&search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000"
# CSV_FILE = str(DATA_DIR / "suzuki-vitara.csv")

# URL = "https://www.otomoto.pl/osobowe/nissan/qashqai/od-2016?search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000"
# CSV_FILE = str(DATA_DIR / "nissan-qashqai.csv")

# URL = "https://www.otomoto.pl/osobowe/nissan/qashqai/od-2016?page=5&search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000"
# CSV_FILE = str(DATA_DIR / "nissan-qashqai.csv")

# URL = "https://www.otomoto.pl/osobowe/mitsubishi/asx/od-2016?search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000"
# CSV_FILE = str(DATA_DIR / "mitsubishi-asx.csv")

# URL = "https://www.otomoto.pl/osobowe/mitsubishi/asx/od-2016?page=2&search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000"
# CSV_FILE = str(DATA_DIR / "mitsubishi-asx.csv")

URL = "https://www.otomoto.pl/osobowe/dacia/duster/od-2016?search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000https://www.otomoto.pl/osobowe/dacia/duster/od-2016?search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000https://www.otomoto.pl/osobowe/dacia/duster/od-2016?search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000"
CSV_FILE = str(DATA_DIR / "dacia-duster.csv")

# URL = "https://www.otomoto.pl/osobowe/dacia/duster/od-2016?page=9&search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000"
# CSV_FILE = str(DATA_DIR / "dacia-duster.csv")

# URL = "https://www.otomoto.pl/osobowe/kia/sportage/od-2016?search%5Bfilter_enum_fuel_type%5D=petrol"
# CSV_FILE = str(DATA_DIR / "kia-sportage.csv")

# URL = "https://www.otomoto.pl/osobowe/kia/sportage/od-2016?search%5Bfilter_enum_fuel_type%5D=petrol"
# CSV_FILE = str(DATA_DIR / "kia-sportage.csv")

HEADLESS = False
WAIT_MS = 3000
MAX_PAGES = 10
MAX_NAVIGATION_RETRIES = 3

POST_NAVIGATION_DELAY_RANGE_MS = (3000, 6500)
PAGE_BREAK_DELAY_RANGE_MS = (9000, 18000)
SCROLL_PAUSE_RANGE_MS = (900, 2200)
SCROLL_STEP_RANGE_PX = (1400, 4200)
RETRY_BACKOFF_DELAY_RANGE_MS = (4000, 10000)

START_URL = URL