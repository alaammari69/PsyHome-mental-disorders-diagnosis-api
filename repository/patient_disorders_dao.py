import pandas
from sqlalchemy import text

from repository.dbconnector import DBConnector


class PatientDisorderDAO:
    def __init__(self):
        raise TypeError("cannot instantiate class PatientDisorderDAO")

    @staticmethod
    def get_by_patient(patient_id: int):
        query = text("""
            SELECT pd.*, d.disorder_name
            FROM patient_disorders pd
            JOIN disorders d ON d.disorder_id = pd.disorder_id
            WHERE pd.patient_id = :patient_id
        """)
        params = {"patient_id": patient_id}
        engine = DBConnector().get_engine()
        return pandas.read_sql(query, engine, params=params)

    @staticmethod
    def insert(patient_id: int, disorder_id: int, diagnosed_at=None, confidence: float = None):
        try:
            query = text("""
                INSERT INTO patient_disorders (patient_id, disorder_id, diagnosed_at, confidence)
                VALUES (:patient_id, :disorder_id, :diagnosed_at, :confidence)
            """)
            params = {
                "patient_id": patient_id,
                "disorder_id": disorder_id,
                "diagnosed_at": diagnosed_at,
                "confidence": confidence
            }
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(query, parameters=params)
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def delete(patient_id: int, disorder_id: int):
        try:
            query = text("""
                DELETE FROM patient_disorders
                WHERE patient_id = :patient_id
                  AND disorder_id = :disorder_id
            """)
            params = {
                "patient_id": patient_id,
                "disorder_id": disorder_id
            }
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(query, parameters=params)
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False

