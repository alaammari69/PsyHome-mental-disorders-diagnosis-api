import pandas
from pandas import DataFrame
from sqlalchemy import text

from repository.dbconnector import DBConnector


class PatientThreadDAO:
    def __init__(self):
        raise TypeError("cannot instantiate class PatientThreadDAO")

    @staticmethod
    def add_thread(patient_id: int, thread_id: int, code: str, status: bool = True) -> int | None:
        try:
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO patient_thread (patient_id, thread_id, code, status)
                    VALUES (:patient_id, :thread_id, :code, :status)
                    RETURNING id
                """), parameters={
                    "patient_id": patient_id,
                    "thread_id": thread_id,
                    "code": code,
                    "status": status
                })
                conn.commit()
                return result.fetchone()[0]
        except Exception as e:
            print(e)
            return None

    @staticmethod
    def get(patient_id: int, thread_id: int) -> DataFrame:
        engine = DBConnector().get_engine()
        query = text("""
            SELECT * FROM patient_thread
            WHERE patient_id = :patient_id AND thread_id = :thread_id
        """)
        return pandas.read_sql(query, engine, params={"patient_id": patient_id, "thread_id": thread_id})

    @staticmethod
    def get_by_patient_id(patient_id: int) -> DataFrame:
        engine = DBConnector().get_engine()
        query = text("""
            SELECT * FROM patient_thread
            WHERE patient_id = :patient_id
            ORDER BY created_at DESC
        """)
        return pandas.read_sql(query, engine, params={"patient_id": patient_id})

    @staticmethod
    def change_status(patient_id: int, thread_id: int, status: bool) -> bool:
        try:
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE patient_thread
                    SET status = :status
                    WHERE patient_id = :patient_id AND thread_id = :thread_id
                """), parameters={
                    "patient_id": patient_id,
                    "thread_id": thread_id,
                    "status": status
                })
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False