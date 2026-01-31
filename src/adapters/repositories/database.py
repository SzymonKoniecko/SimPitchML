import os
import urllib
from sqlalchemy import create_engine, text
from src.core import get_logger

RAW_CONN_STRING = os.getenv("CONNECTION_STRING")

# 2. Tworzymy URL dla SQLAlchemy
# Musimy zakodować parametry, żeby SQLAlchemy "zjadło" string ODBC
params = urllib.parse.quote_plus(RAW_CONN_STRING)

# Jeśli zmienisz bibliotekę na 'pyodbc', zmień też tu prefiks na 'mssql+pyodbc'
SQLALCHEMY_DATABASE_URL = f"mssql+pyodbc:///?odbc_connect={params}"

class DatabaseContext:
    def __init__(self):
        self.logger = get_logger(__name__) 
        # Tworzymy silnik (to robisz raz na całą aplikację, najlepiej globalnie)
        # pool_pre_ping=True sprawdza czy połączenie żyje przed użyciem
        self.engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_pre_ping=True)

    def TakeLatestSynchronizationDate(self):
        query = text("SELECT SyncDate FROM SimPitchMl.dbo.Synchronization;")
        
        try:
            # Używamy context managera 'with' - połączenie wraca do puli automatycznie
            with self.engine.connect() as connection:
                result = connection.execute(query).fetchone()
                return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            raise
