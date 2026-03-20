from sqlalchemy import create_engine
import pyodbc
import socket


class ServerConfig:
    def __init__(
        self,
        server_name: str = socket.gethostname(),  # Default to local machine
        database_name: str = "EMTP_Correspondence",
    ):
        self.server_name = server_name
        self.database_name = database_name


class DatabaseConnection:
    def __init__(self, server: ServerConfig = ServerConfig()):
        drivers = pyodbc.drivers()

        if "ODBC Driver 18 for SQL Server" in drivers:
            driver = "ODBC Driver 18 for SQL Server"
        elif "ODBC Driver 17 for SQL Server" in drivers:
            driver = "ODBC Driver 17 for SQL Server"
        else:
            sql_drivers = [d for d in drivers if "SQL Server" in d]
            if sql_drivers:
                driver = sql_drivers[-1]  # pick the newest of whatever exists
            else:
                raise RuntimeError(
                    "No SQL Server ODBC driver found. Install ODBC Driver 18 or 17."
                )

        self.conn_str = (
            f"mssql+pyodbc://@{server.server_name}/{server.database_name}"
            f"?driver={driver.replace(' ', '+')}"
            "&trusted_connection=yes"
            "&Encrypt=no"
            "&TrustServerCertificate=yes"
        )

        self.engine = create_engine(self.conn_str, fast_executemany=True)


if __name__ == "__main__":
    from sqlalchemy import text

    conn = DatabaseConnection()

    with conn.engine.begin() as connection:
        select_query = text(
            """
            SELECT *
            FROM Company
            """
        )
        result = connection.execute(select_query).mappings().all()

        for row in result:
            print(row["CompanyID"], row["RazonSocial"])
