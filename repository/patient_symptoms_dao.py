import pandas
from sqlalchemy import text

from repository.dbconnector import DBConnector


class PatientSymptomDAO:
    def __init__(self):
        raise TypeError("cannot instantiate class PatientSymptomDAO")


    @staticmethod
    def get_all():
        query = text("""
        select * from patient_symptoms""")
        engine = DBConnector().get_engine()
        return pandas.read_sql(query, engine)

    @staticmethod
    def get_by_patient(patient_id: int):
        query = text("""
            select * from patient_symptoms
            where patient_id = :patient_id
        """)
        params = {"patient_id": patient_id}
        engine = DBConnector().get_engine()
        return pandas.read_sql(query, engine, params=params)

    @staticmethod
    def get_by_patient_symptom_id(patient_id: int, symptom_id: int):
        query = text("""
            select * from patient_symptoms
            where patient_id = :patient_id and symptom_id = :symptom_id
        """)
        params = {"patient_id": patient_id, "symptom_id": symptom_id}

        engine = DBConnector().get_engine()
        return pandas.read_sql(query, engine, params=params)

    @staticmethod
    def insert(patient_id: int, symptom_id: int, intensity: int):
        try:
            query = text("""
                INSERT INTO patient_symptoms (patient_id, symptom_id, intensity)
                VALUES (:patient_id, :symptom_id, :intensity)
            """)
            params = {
                "patient_id": patient_id,
                "symptom_id": symptom_id,
                "intensity": intensity
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
    def delete(patient_id: int, symptom_id: int):
        try:
            query = text("""
                DELETE FROM patient_symptoms
                WHERE patient_id = :patient_id
                  AND symptom_id = :symptom_id
            """)
            params = {
                "patient_id": patient_id,
                "symptom_id": symptom_id
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
    def check_symptom_exists(patient_id: int, symptom_id: int):
        query = text("""
            select count(*) from patient_symptoms
            where patient_id = :patient_id and symptom_id = :symptom_id
        """)
        params = {"patient_id": patient_id, "symptom_id": symptom_id}
        try:
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                count = pandas.read_sql(query, conn, params=params)["count(*)"][0]
                return count > 0
        except Exception as e:
            print(e)
            return None


    @staticmethod
    def update(patient_id: int, symptom_id: int, intensity: int = None):
        try:
            updates = []
            params = {"patient_id": patient_id, "symptom_id": symptom_id}

            if intensity is not None:
                updates.append("intensity = :intensity")
                params["intensity"] = intensity

            if not updates:
                return True  # Nothing to update

            query = text(f"""
                UPDATE patient_symptoms 
                SET {', '.join(updates)} 
                WHERE patient_id = :patient_id AND symptom_id = :symptom_id
            """)
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(query, parameters=params)
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False
