import pandas
from pandas import DataFrame
from sqlalchemy import text

from repository.dbconnector import DBConnector


class PatientThreadDAO:
    def __init__(self):
        raise TypeError("cannot instantiate class PatientThreadDAO")

    @staticmethod
    def add_thread(patient_id: int, additional_info: str = None ,status: bool = True, diagnosis_id: int = None) -> int | None:
        try:
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("""
                    INSERT INTO patient_thread (patient_id, status, additional_info, diagnosis_id)
                    VALUES (:patient_id, :status, :additional_info, :diagnosis_id)
                """), parameters={
                    "patient_id": patient_id,
                    "status": status,
                    "additional_info": additional_info,
                    "diagnosis_id": diagnosis_id
                })
                conn.commit()
                return result.fetchone()[0]
        except Exception as e:
            print(e)
            return None

    @staticmethod
    def get(thread_id: int) -> DataFrame:
        engine = DBConnector().get_engine()
        query = text("""
            SELECT * FROM patient_thread
            WHERE thread_id = :thread_id
        """)
        return pandas.read_sql(query, engine, params={ "thread_id": thread_id})

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
    def change_status(thread_id: int, status: bool) -> bool:
        try:
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(text("""
                    UPDATE patient_thread
                    SET status = :status
                    WHERE thread_id = :thread_id
                """), parameters={
                    "thread_id": thread_id,
                    "status": status
                })
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def nbr_threads_per_patient(patient_id: int) -> int:
        try:
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("""
                SELECT COUNT(*) AS nbr_threads
                from patient_thread
                where patient_id = :patient_id
                """), parameters={"patient_id": patient_id})
                conn.commit()
                return result.fetchone()[0]
        except Exception as e:
            print(e)
            return 0



    @staticmethod
    def nbr_active_threads_per_patient(patient_id: int) -> int:
        try:
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("""
                SELECT COUNT(*) AS nbr_threads
                from patient_thread
                where patient_id = :patient_id and status = TRUE
                """), parameters={"patient_id": patient_id})
                conn.commit()
                return result.fetchone()[0]
        except Exception as e:
            print(e)
            return 0

    @staticmethod
    def last_session_date(patient_id: int):
        try:
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("""
                select MAX(created_at) AS last_session_date
                from patient_thread
                where patient_id = :patient_id"""), parameters={"patient_id": patient_id})
                conn.commit()
                return result.fetchone()[0]
        except Exception as e:
            print(e)
            return None