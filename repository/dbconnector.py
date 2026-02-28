import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, Engine, Connection


class DBConnector:
    _instance = None
    _engine = None
    _connection_string = None

    def __new__(cls):

        #check if there's an existent connection instance
        #else creates a new one
        #returns the same instance each time
        if cls._instance is None:
            cls._instance = super(DBConnector, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """
        initialize the DB connection variables
        :return: None
        """
        if self._engine is None:
            try:
                config = self._load_configs()
                self.connection_string = self._create_connection_string()
                self._engine = create_engine(self.connection_string)
            except Exception as e:
                print(f"Database connection error: {e}")
                raise

    @staticmethod
    def _load_configs()->dict:
        """
        this method is used to load the environment variables
        that are relevant to the DB connection
        and put them in a dictionary
        :return: dict with the connection information
        """
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

    def _create_connection_string(self)->str:
        """
        this method is used to create the connection string
        it gets the info from the environment variables
        then combines them to a url string to create DB connections
        :return: connection string
        """
        config = self._load_configs()
        conn_string = (
            f"postgresql://{config['user']}:{config['password']}"
            f"@{config['host']}:{config['port']}/{config['database']}"
        )
        return conn_string

    def get_engine(self)->Engine:
        """
        :return: instance of sqlalchemy Engine object
        """
        return self._engine
    def get_connection(self)->Connection:
        """

        :return: instance of sqlalchemy Connection object
        """
        return self._engine.connect()

    def get_connection_string(self) -> str:
        """
        creates the connection string
        using the environment variables
        :return: connection string
        """
        if self._connection_string is not None:
            return self._connection_string
        else:
            return self._create_connection_string()