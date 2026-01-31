import os
import uuid
import urllib.parse
from sqlalchemy import create_engine, text
from src.core import get_logger


class DatabaseContext:
    def __init__(self):
        self.logger = get_logger(__name__)
        self.engine = self._create_db_engine()

    def _create_db_engine(self):
        """
        Prywatna metoda pomocnicza do inicjalizacji silnika bazy danych.
        Jest wywoływana dopiero przy tworzeniu instancji klasy, co naprawia błędy importu.
        """
        raw_conn_string = os.getenv("CONNECTION_STRING")

        if not raw_conn_string:
            error_msg = "Environment variable 'CONNECTION_STRING' is not set."
            self.logger.critical(error_msg)
            raise ValueError(error_msg)

        try:
            params = urllib.parse.quote_plus(raw_conn_string)

            sqlalchemy_database_url = f"mssql+pyodbc:///?odbc_connect={params}"

            return create_engine(sqlalchemy_database_url, pool_pre_ping=True)

        except Exception as e:
            self.logger.critical(f"Failed to initialize database engine: {e}")
            raise

    def TakeLatestSynchronizationDate(self):
        query = text(
            "SELECT TOP(1) LastSyncDate FROM SimPitchMl.dbo.Synchronization order by LastSyncDate desc;"
        )

        try:
            with self.engine.connect() as connection:
                result = connection.execute(query).fetchone()
                return result[0] if result else None
        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            raise

    def CreateLatestSynchronizationRow(self, LastSyncDate, AddedSimulations):
        query = text(
            """
            INSERT INTO SimPitchMl.dbo.Synchronization (Id, LastSyncDate, AddedSimulations) 
            VALUES (:id, :date, :count)
        """
        )

        try:
            with self.engine.connect() as connection:
                # 2. Pass parameters as a dictionary
                connection.execute(
                    query,
                    {
                        "id": uuid.uuid4(),
                        "date": LastSyncDate,
                        "count": AddedSimulations,
                    },
                )

                connection.commit()

                self.logger.info("New synchronization row created.")
        except Exception as e:
            self.logger.error(f"Insert failed: {e}")
            raise
