from pathlib import Path
from unittest import result
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

    # -------------- Nuevo -----------------------------------
    def get_table_data(
        self, table_name: str, columns: list[str] | None = None
    ) -> pd.DataFrame:
        with self.engine.connect() as connection:
            cols = ", ".join(columns) if columns else "*"
            query = text(f"SELECT {cols} FROM {table_name}")
            result = connection.execute(query).mappings().all()

            result_df = pd.DataFrame(result)

        if columns:
            result_df = result_df[columns]

        return result_df

    def get_msg_pending(self, df: pd.DataFrame) -> pd.DataFrame:
        df_filtered = df[~df["Correlativo"].str.contains("-", na=False)]
        # df_filtered = df[~df["SentCorrelativo"].str.contains("-", na=False)]
        return df_filtered

    def get_pending_with_review(self, df_pending: pd.DataFrame) -> pd.DataFrame:
        # --- MsgReview ---
        df_msg_review = self.get_table_data("MsgReview", columns=["MsgID", "ReviewID"])

        df_final = df_pending.merge(df_msg_review, on="MsgID", how="left")
        # --- ReviewMsgEmtpUnit ---
        df_review_msg_unit = self.get_table_data(
            "ReviewMsgEmtpUnit", columns=["ReviewID", "MsgEmtpUnitID"]
        )
        df_final = df_final.merge(df_review_msg_unit, on="ReviewID", how="left")
        # --- MsgEmtpUnit (NUEVO) ---
        df_msg_empt_unit = self.get_table_data(
            "MsgEmtpUnit", columns=["MsgEmtpUnitID", "ModelUnitID"]
        )
        df_final = df_final.merge(df_msg_empt_unit, on="MsgEmtpUnitID", how="left")

        df_model_unit = self.get_table_data(
            "ModelUnit", columns=["ModelUnitID", "UnitName"]
        )
        df_final = df_final.merge(df_model_unit, on="ModelUnitID", how="left")

        return df_final

    def get_pending_with_review2(self) -> pd.DataFrame:
        query = text(
            """
            SELECT
                m.MsgID,
                m.MsgTypeID,
                m.MsgDate,
                m.Correlativo,
                m.CompanyName,
                m.SenderName,
                m.Subject,
                m.Obsolete,
                mr.ReviewID,
                rmeu.MsgEmtpUnitID,
                meu.ModelUnitID,
                mu.UnitName
            FROM Msg m
            LEFT JOIN MsgReview mr
                ON m.MsgID = mr.MsgID
            LEFT JOIN ReviewMsgEmtpUnit rmeu
                ON mr.ReviewID = rmeu.ReviewID
            LEFT JOIN MsgEmtpUnit meu
                ON rmeu.MsgEmtpUnitID = meu.MsgEmtpUnitID
            LEFT JOIN ModelUnit mu
                ON meu.ModelUnitID = mu.ModelUnitID
            WHERE m.Correlativo NOT LIKE '%-%'
            AND m.Obsolete = 0
        """
        )

        with self.engine.connect() as connection:
            result = connection.execute(query).mappings().all()
            df = pd.DataFrame(result)

        return df


if __name__ == "__main__":
    try:
        db = EmtpDb()
        df = db.get_pending_with_review2()
        print(df)
        df.to_excel("output4.xlsx", index=False)
    except Exception as e:
        print(f"Error: {e}")


""" Metodo antiguo"""
"""
if __name__ == "__main__":

    try:
        db = EmtpDb()

        tab = "Msg"
        colums = [
            "MsgID",
            "MsgTypeID",
            "MsgDate",
            "Correlativo",
            "CompanyName",
            "SenderName",
            "Subject",
        ]

        df = db.get_table_data(table_name=tab, columns=colums)

        print(df)
        msg_pending_table = db.get_msg_pending(df)
        msg_pending_table.to_excel("output2.xlsx", index=False)

        msg_pending_with_review = db.get_pending_with_review(msg_pending_table)
        msg_pending_with_review.to_excel("output3.xlsx", index=False)

        print(msg_pending_with_review)

    except Exception as e:
        print(f"Error: {e}")
        """
