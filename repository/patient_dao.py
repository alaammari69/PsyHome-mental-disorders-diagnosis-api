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
        cin: str,
        date_of_birth,
        gender: str,
        username: str,
        password: str
    ):
        try:
            query = text("""
                INSERT INTO patients (
                    first_name,
                    last_name,
                    cin,
                    date_of_birth,
                    gender,
                    username,
                    password
                )
                VALUES (
                    :first_name,
                    :last_name,
                    :cin,
                    :date_of_birth,
                    :gender,
                    :username,
                    :password
                )
                RETURNING patient_id
            """)
            params = {
                "first_name": first_name,
                "last_name": last_name,
                "cin": cin,
                "date_of_birth": date_of_birth,
                "gender": gender,
                "username": username,
                "password": password
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
    def update(
            patient_id: int,
            first_name: str = None,
            last_name: str = None,
            cin: str = None,
            date_of_birth=None,
            gender: str = None,
            username: str = None,
            password: str = None
    ):
        try:
            fields = []
            params = {"patient_id": patient_id}

            if first_name is not None:
                fields.append("first_name = :first_name")
                params["first_name"] = first_name

            if last_name is not None:
                fields.append("last_name = :last_name")
                params["last_name"] = last_name

            if cin is not None:
                fields.append("cin = :cin")
                params["cin"] = cin

            if date_of_birth is not None:
                fields.append("date_of_birth = :date_of_birth")
                params["date_of_birth"] = date_of_birth

            if gender is not None:
                fields.append("gender = :gender")
                params["gender"] = gender

            if username is not None:
                fields.append("username = :username")
                params["username"] = username

            if password is not None:
                fields.append("password = :password")
                params["password"] = password

            #nothing to update
            if not fields:
                return False

            query = text(f"""
                UPDATE patients
                SET {", ".join(fields)}
                WHERE patient_id = :patient_id
            """)

            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(query, parameters=params)
                conn.commit()
                return True

        except Exception as e:
            print(e)
            return False

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
