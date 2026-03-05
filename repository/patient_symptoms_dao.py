import pandas
from pandas import DataFrame
from sqlalchemy import text

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
    def get_by_patient_symptom_thread_id(patient_id: int, symptom_id: int, thread_id: str)->DataFrame:
        query = text("""
            select * from patient_symptoms
            where patient_id = :patient_id and symptom_id = :symptom_id and thread_id = :thread_id
        """)
        params = {"patient_id": patient_id ,"symptom_id": symptom_id, "thread_id": thread_id}
        engine = DBConnector().get_engine()
        return pandas.read_sql(query, engine, params=params)


    @staticmethod
    def insert(patient_id: int, thread_id: str, symptom_id: int, intensity: int):
        try:
            query = text("""
                INSERT INTO patient_symptoms (patient_id, symptom_id, intensity, thread_id)
                VALUES (:patient_id, :symptom_id, :intensity, :thread_id)
            """)
            params = {
                "patient_id": patient_id,
                "symptom_id": symptom_id,
                "intensity": intensity,
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
    def delete(patient_id: int, symptom_id: int, thread_id: str)->bool:
        try:
            query = text("""
                DELETE FROM patient_symptoms
                WHERE patient_id = :patient_id
                  AND symptom_id = :symptom_id
                    AND thread_id = :thread_id
            """)
            params = {
                "patient_id": patient_id,
                "symptom_id": symptom_id,
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
    def check_symptom_exists(patient_id: int, symptom_id: int, thread_id: str)->bool:
        query = text("""
            select count(*) from patient_symptoms
            where patient_id = :patient_id and symptom_id = :symptom_id and thread_id = :thread_id
        """)
        params = {"patient_id": patient_id, "symptom_id": symptom_id, "thread_id": thread_id}
        try:
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                count = pandas.read_sql(query, conn, params=params)["count(*)"][0]
                return count > 0
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def update (patient_id: int, symptom_id: int, thread_id: str, intensity: int)->bool:
        try:
            query = text("""
                UPDATE patient_symptoms
                SET intensity = :intensity
                where patient_id = :patient_id and symptom_id = :symptom_id and thread_id = :thread_id
                """)
            params = {
                "patient_id": patient_id,
                "symptom_id": symptom_id,
                "intensity": intensity,
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
    def insert_or_update_max_intensity(patient_id: int, symptom_id: int, thread_id: str, intensity: int)->bool:
        """
        This method is used to always save the max intensity value for a symptom
        if a symptom isn't stored yet, then it inserts it automatically
        :param patient_id: the patient id or user id
        :param symptom_id: symptom id
        :param thread_id: thread id or session id
        :param intensity: a value of the symptom existence (0-10)
        :return: true if no errors occurred
        """
        try:
            # first trying to retrieve the same symptom if it exists according to the patient(user) or session
            existing_symptom = PatientSymptomDAO.get_by_patient_symptom_thread_id(
                patient_id=patient_id,
                thread_id=thread_id,
                symptom_id=int(symptom_id)
            )

            # if the symptom have never been registered then it inserts it and then work done
            if existing_symptom.empty:
                return PatientSymptomDAO.insert(
                    patient_id=patient_id,
                    thread_id=thread_id,
                    symptom_id=int(symptom_id),
                    intensity=intensity
                )
            # if the symptom is already registered, we check if the new intensity is higher than the older one
            # (it means that we called this method a second time with the same parameters but the agent is more sure about the existence of this symptom)
            else:
                if intensity > existing_symptom["intensity"].iloc[0]:
                    print(existing_symptom)
                    return PatientSymptomDAO.update(
                        patient_id=patient_id,
                        thread_id=thread_id,
                        symptom_id=int(symptom_id),
                        intensity=intensity
                    )
            # in this case the intensity is lower than the original value then we just leave it
            print("nothing is updated")
            return True

        except Exception as e:
            print(e)
            return False

