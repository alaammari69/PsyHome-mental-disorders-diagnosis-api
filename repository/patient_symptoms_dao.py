import pandas
from pandas import DataFrame
from sqlalchemy import text

from models.custom_enums import SymptomLikelihood
from repository.dbconnector import DBConnector


class PatientSymptomDAO:
    def __init__(self):
        raise TypeError("cannot instantiate class PatientSymptomDAO")


    @staticmethod
    def get_all():
        query = text("""
                     select * from patient_symptoms
                     """)
        engine = DBConnector().get_engine()
        return pandas.read_sql(query, engine)

    @staticmethod
    def get_by_patient_id(patient_id: int):
        query = text("""
                     select *
                     from patient_symptoms
                     where patient_id = :patient_id
                     """)
        params = {"patient_id": patient_id}
        engine = DBConnector().get_engine()
        return pandas.read_sql(query, engine, params=params)

    @staticmethod
    def get_by_patient_thread_id(patient_id: int, thread_id: str):
        query = text("""
                     select *
                     from patient_symptoms
                     where patient_id = :patient_id
                       and thread_id = :thread_id
                     """)
        params = {"patient_id": patient_id, "thread_id": thread_id}
        engine = DBConnector().get_engine()
        return pandas.read_sql(query, engine, params=params)

    @staticmethod
    def get_by_patient_symptom_id(patient_id: int, symptom_id: int) -> DataFrame:
        query = text("""
                     select *
                     from patient_symptoms
                     where patient_id = :patient_id
                       and symptom_id = :symptom_id
                     """)
        params = {"patient_id": patient_id, "symptom_id": symptom_id}
        engine = DBConnector().get_engine()
        return pandas.read_sql(query, engine, params=params)


    @staticmethod
    def get_by_patient_symptom_thread_id(patient_id: int, symptom_id: int, thread_id: str)->DataFrame:
        query = text("""
            select * from patient_symptoms
            where patient_id = :patient_id and symptom_id = :symptom_id and thread_id = :thread_id
        """)
        params = {"patient_id": patient_id ,"symptom_id": symptom_id, "thread_id": thread_id}
        engine = DBConnector().get_engine()
        return pandas.read_sql(query, engine, params=params)

    @staticmethod
    def insert(patient_id: int, thread_id: str, symptom_id: int, confidence: int):
        try:
            query = text("""
                         INSERT INTO patient_symptoms (patient_id, symptom_id, confidence, thread_id)
                         VALUES (:patient_id, :symptom_id, :confidence, :thread_id)
                         """)
            params = {
                "patient_id": patient_id,
                "symptom_id": symptom_id,
                "confidence": likelihood_to_str(confidence),  # key change
                "thread_id": thread_id
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
    def delete(patient_id: int, symptom_id: int)->bool:
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
    def check_symptom_exists(patient_id: int, symptom_id: int)->bool:
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
            return False

    @staticmethod
    def update(patient_id: int, symptom_id: int, thread_id: str, confidence: int) -> bool:
        try:
            query = text("""
                         UPDATE patient_symptoms
                         SET confidence = :confidence,
                             thread_id  = :thread_id
                         WHERE patient_id = :patient_id
                           AND symptom_id = :symptom_id
                         """)
            params = {
                "patient_id": patient_id,
                "symptom_id": symptom_id,
                "confidence": likelihood_to_str(confidence),
                "thread_id": thread_id
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
    def insert_or_update_max_confidence(patient_id: int, symptom_id: int, thread_id: str, confidence: int) -> bool:
        try:
            existing = PatientSymptomDAO.get_by_patient_symptom_id(
                patient_id=patient_id,
                symptom_id=symptom_id
            )

            if existing is None or existing.empty:
                print("adding new symptom")
                return PatientSymptomDAO.insert(
                    patient_id=patient_id,
                    thread_id=thread_id,
                    symptom_id=symptom_id,
                    confidence=confidence
                )
            else:
                # DB returns ENUM as string → convert to IntEnum
                current_symptom_name = existing["symptom_name"]
                current_conf_str = existing["confidence"].iloc[0]
                current_conf = SymptomLikelihood[current_conf_str].value

                print("symptom name is: ", current_symptom_name)
                print("New confidence:", confidence)
                print("Existing confidence:", current_conf,"\n")

                if (confidence > current_conf) and (current_conf != SymptomLikelihood.NEUTRAL):
                    print("updating confidence...")
                    return PatientSymptomDAO.update(
                        patient_id=patient_id,
                        thread_id=thread_id,
                        symptom_id=symptom_id,
                        confidence=confidence
                    )

            print("nothing is updated")
            return True

        except Exception as e:
            print(e)
            return False

    @staticmethod
    def get_patient_symptoms_full_description(patient_id: int)->DataFrame|None:
        try:
            query = text("""
                SELECT ps.*, s.*
                FROM patient_symptoms ps JOIN symptoms s ON ps.symptom_id = s.symptom_id
                WHERE ps.patient_id = :patient_id
            """)
            params = {"patient_id": patient_id}
            engine = DBConnector().get_engine()
            return pandas.read_sql(query, engine, params=params)
        except Exception as e:
            print(e)
            return None


def likelihood_to_str(value: int) -> str:
    return SymptomLikelihood(value).name

