import os, uuid
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
        query = text("SELECT TOP(1) LastSyncDate FROM SimPitchMl.dbo.Synchronization order by LastSyncDate desc;")
        
        try:
            # Używamy context managera 'with' - połączenie wraca do puli automatycznie
            with self.engine.connect() as connection:
                result = connection.execute(query).fetchone()
                return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            raise

    def CreateLatestSynchronizationRow(self, LastSyncDate, AddedSimulations):
        # 1. Use placeholders (:name) for parameters. 
        query = text("""
            INSERT INTO SimPitchMl.dbo.Synchronization (Id, SynchronizationDate, AddedSimulations) 
            VALUES (:id, :date, :count)
        """)
        
        try:
            with self.engine.connect() as connection:
                # 2. Pass parameters as a dictionary
                connection.execute(query, {"id":uuid.uuid4(), "date": LastSyncDate, "count": AddedSimulations})
                
                # 3. Commit the transaction (Crucial for INSERT/UPDATE)
                connection.commit()
                
                self.logger.info("New synchronization row created.")
        except Exception as e:
            self.logger.error(f"Insert failed: {e}")
            raise
