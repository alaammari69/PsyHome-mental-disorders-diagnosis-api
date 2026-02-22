import pandas
from sqlalchemy import text

from repository.dbconnector import DBConnector


class PatientDAO:
    def __init__(self):
        raise TypeError("cannot instantiate class PatientDAO")

    @staticmethod
    def get_all():
        query = text("SELECT * FROM patients ORDER BY patient_id")
        engine = DBConnector().get_engine()
        return pandas.read_sql(query, engine)

    @staticmethod
    def get(patient_id: int):
        query = text("SELECT * FROM patients WHERE patient_id = :patient_id")
        params = {"patient_id": patient_id}
        engine = DBConnector().get_engine()
        return pandas.read_sql(query, engine, params=params)

    @staticmethod
    def insert(
        first_name: str,
        last_name: str,
        external_ref: str = None,
        date_of_birth=None,
        gender: str = None
    ):
        try:
            query = text("""
                INSERT INTO patients (
                    first_name,
                    last_name,
                    external_ref,
                    date_of_birth,
                    gender
                )
                VALUES (
                    :first_name,
                    :last_name,
                    :external_ref,
                    :date_of_birth,
                    :gender
                )
                RETURNING patient_id
            """)
            params = {
                "first_name": first_name,
                "last_name": last_name,
                "external_ref": external_ref,
                "date_of_birth": date_of_birth,
                "gender": gender
            }
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                result = conn.execute(query, parameters=params)
                conn.commit()
                return result.fetchone()[0]
        except Exception as e:
            print(e)
            return None

    @staticmethod
    def delete(patient_id: int):
        try:
            query = text("DELETE FROM patients WHERE patient_id = :patient_id")
            params = {"patient_id": patient_id}
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(query, parameters=params)
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False
