from pathlib import Path
from database import DatabaseConnection

# from web_scrapper import Letter
# from directories import Directories
# from documents import PdfHandler
# from reuc import ReucExcelHandler
from sqlalchemy import text
from datetime import datetime, time
import pandas as pd

# from UI import Terminal
from dataclasses import dataclass


@dataclass
class Message:
    correlativo: str
    msg_type_id: int
    doc_type: str  # Not used in DB, only for convenience: "R", "E", "OP"
    msg_url: str

    msg_id: int = -1
    msg_channel_id: int = 1
    registered_by_id: int = 14
    created_on: datetime = datetime.now()
    modified_on: datetime = datetime.now()
    msg_date: datetime = datetime.now()
    company_name: str | None = None
    company_id: int | None = None
    materia_macro: str | None = None
    materia_micro: str | None = None
    subject: str | None = None
    external_code: str | None = None
    sender_name: str | None = None
    attachments: int = 0
    confidential: bool = False
    replying: int = 0
    response_required: bool = False
    replied: int = 0
    pdf_inner_link: str | None = None
    inner_link_resolved: bool | None = None
    comment: str | None = None
    ai_summary: str | None = None
    ai_request: str | None = None
    ai_another_subject: bool | None = None


class EmtpDb(DatabaseConnection):
    """Class to handle database operations for EMTP Stream."""

    def __init__(self, debug: bool = False):
        super().__init__()
        self.debug = debug

    def get_msg_record(
        self,
        msg_type_id: int,
        correlativo: str,
        msg_channel_id: int = 1,  # Sistema de Correspondencia
    ) -> int | None:
        """Gets the message record with the given Correlativo, MsgTypeID,
        and MsgChannelID from the database."""

        with self.engine.connect() as connection:
            result = connection.execute(
                text(
                    """
                    SELECT MsgID
                    FROM Msg
                    WHERE Correlativo = :correlativo
                    AND MsgTypeID = :msg_type_id
                    AND MsgChannelID = :msg_channel_id
                    """
                ),
                {
                    "correlativo": correlativo,
                    "msg_type_id": msg_type_id,
                    "msg_channel_id": msg_channel_id,
                },
            )
            rows = result.fetchall()
            if rows:
                return rows[0][0]  # Return MsgID
            else:
                return None

    def get_msgs_from_db(
        self,
        doc_types: list[str] = ["R", "E", "OP"],
    ) -> list[Message]:
        db_messages = []
        with self.engine.connect() as connection:
            select_query = text(
                """
                SELECT MsgID,
                    Correlativo, MsgTypeID, MsgUrl,
                    AISummary, AIRequest, AIAnotherSubject
                FROM Msg
                WHERE MsgChannelID = 1
                AND MsgTypeID IN (1, 2, 3)
                """
            )
            result = connection.execute(select_query).mappings().all()
            for row in result:
                msg_type_id = row["MsgTypeID"]
                if msg_type_id == 1:
                    doc_type = "R"
                elif msg_type_id == 2:
                    doc_type = "E"
                elif msg_type_id == 3:
                    doc_type = "OP"
                else:
                    continue  # Skip unknown message types

                if doc_type not in doc_types:
                    continue

                msg = Message(
                    correlativo=row["Correlativo"],
                    msg_url=row["MsgUrl"],
                    doc_type=doc_type,
                    msg_type_id=msg_type_id,
                    ai_summary=row["AISummary"],
                    ai_request=row["AIRequest"],
                    ai_another_subject=row["AIAnotherSubject"],
                    msg_id=row["MsgID"],
                )

                db_messages.append(msg)

                if self.debug:
                    print(
                        f"Fetched MsgID={row['MsgID']} "
                        f"with Correlativo={msg.correlativo} "
                        f"and MsgTypeID={msg.msg_type_id} from DB."
                    )

        return db_messages

    def get_view_data(self, view_name: str) -> list[dict]:
        """get view tables"""
        with self.engine.connect() as connection:
            query = text(f"SELECT * FROM {view_name}")
            result = connection.execute(query).mappings().all()
            result_df = pd.DataFrame(result)

        return result_df  # lista de diccionarios

    def get_pending_correlatives(self, df: pd.DataFrame) -> list[str]:
        """get pending correlativos from PendingMsgQ view"""
        df["correlativo"] = df["Subject"].str.extract(r"(DE\d{5}-\d{2})")
        df_pendings = df["correlativo"].dropna().tolist()
        return df_pendings


if __name__ == "__main__":
    try:
        db = EmtpDb()

        view_name = "PendingMsgQ"  # <-- cámbialo

        print(f"Extraancting View data {view_name}")

        # get data
        df = db.get_view_data(view_name)
        print(f"Total Pending Messages: {len(df)}\n")

        # Mostrar primeras filas como tabla
        print(df.head(20))  # muestra primeras 20 filas
        df_pendings = db.get_pending_correlatives(df)
        print(df_pendings)
    except Exception as e:
        print(f"Error: {e}")


""" if __name__ == "__main__":
    try:
        print("Conectando a la base de datos...")

        db = EmtpDb(debug=False)

        print("Extrayendo mensajes desde la tabla Msg...")
        messages = db.get_msgs_from_db()

        print(f"Total mensajes encontrados: {len(messages)}")

        # Convertir a DataFrame
        data = []
        for msg in messages:
            data.append(
                {
                    "MsgID": msg.msg_id,
                    "Correlativo": msg.correlativo,
                    "Tipo": msg.doc_type,
                    "MsgTypeID": msg.msg_type_id,
                    "URL": msg.msg_url,
                    "AI Summary": msg.ai_summary,
                    "AI Request": msg.ai_request,
                    "AI Another Subject": msg.ai_another_subject,
                }
            )

        df = pd.DataFrame(data)

        print("\nVista tabla:")
        print(df.head(20))  # muestra primeras 10 filas

    except Exception as e:
        print(f"Error al consultar la base de datos: {e}") """
