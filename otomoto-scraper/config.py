from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "otomoto"

# URL = "https://www.otomoto.pl/osobowe/mitsubishi/asx/od-2016?search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000"
# CSV_FILE = str(DATA_DIR / "mitsubishi-asx.csv")

URL = "https://www.otomoto.pl/osobowe/mitsubishi/asx/od-2016?page=5&search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000"
CSV_FILE = str(DATA_DIR / "mitsubishi-asx.csv")

# URL = "https://www.otomoto.pl/osobowe/dacia/duster/od-2016?search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000https://www.otomoto.pl/osobowe/dacia/duster/od-2016?search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000https://www.otomoto.pl/osobowe/dacia/duster/od-2016?search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000"
# CSV_FILE = str(DATA_DIR / "dacia-duster.csv")

# URL = "https://www.otomoto.pl/osobowe/dacia/duster/od-2016?page=9&search%5Bfilter_enum_fuel_type%5D=petrol&search%5Bfilter_float_mileage%3Ato%5D=150000"
# CSV_FILE = str(DATA_DIR / "dacia-duster.csv")

# URL = "https://www.otomoto.pl/osobowe/kia/sportage/od-2016?search%5Bfilter_enum_fuel_type%5D=petrol"
# CSV_FILE = str(DATA_DIR / "kia-sportage.csv")

# URL = "https://www.otomoto.pl/osobowe/kia/sportage/od-2016?page=10&search%5Bfilter_enum_fuel_type%5D=petrol"
# CSV_FILE = str(DATA_DIR / "kia-sportage.csv")

HEADLESS = False
WAIT_MS = 3000