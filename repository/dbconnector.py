import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine


class DBConnector:
    _instance = None
    _engine = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DBConnector, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        if self._engine is None:
            try:
                config = self._load_configs()
                connection_string = (
                    f"postgresql://{config['user']}:{config['password']}"
                    f"@{config['host']}:{config['port']}/{config['database']}"
                )
                self._engine = create_engine(connection_string)
            except Exception as e:
                print(f"Database connection error: {e}")
                raise

    @staticmethod
    def _load_configs():
        env_path = Path(__file__).parent.parent / "core" / ".env"

        if not env_path.exists():
            raise FileNotFoundError(f".env not found at {env_path}")

        load_dotenv(dotenv_path=env_path)

        return {
            'host': os.getenv("DB_HOST_ADDRESS"),

            'port': int(os.getenv("DB_PORT", 5432)),
            'database': os.getenv("DATABASE"),
            'user': os.getenv("ADMIN_USERNAME"),
            'password': os.getenv("ADMIN_PASSWORD")
        }

    def get_engine(self):
        return self._engine