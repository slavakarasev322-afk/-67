from pathlib import Path


APP_VERSION = "1.0.0"

APP_NAME = "Мониторинг расходов ЖКХ"


BASE_DIR = Path(__file__).resolve().parent.parent.parent


DATA_DIR = BASE_DIR / "data"


DATABASE_PATH = DATA_DIR / "housing.db"