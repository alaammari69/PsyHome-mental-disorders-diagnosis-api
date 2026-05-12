import os

import pandas
from pandas import DataFrame
from sqlalchemy import text
from cryptography.fernet import Fernet

from repository.dbconnector import DBConnector
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'core' ,'.env'))

_cipher = Fernet(os.getenv("DB_ENCRYPTION_KEY"))

class PsychiatristDAO:
    def __init__(self):
        raise TypeError("cannot instantiate class PsychiatristDAO")

    @staticmethod
    def get_all():
        query = text("SELECT * FROM psychiatrists ORDER BY id")
        engine = DBConnector().get_engine()
        data = pandas.read_sql(query, engine)
        _decrypt(data)
        return data

    @staticmethod
    def get(psych_id: int):
        query = text("SELECT * FROM psychiatrists WHERE id = :id")
        params = {"id": psych_id}
        engine = DBConnector().get_engine()
        data = pandas.read_sql(query, engine, params=params)
        _decrypt(data)
        return data

    @staticmethod
    def get_by_email_password(email: str, password: str):
        all_psy = PsychiatristDAO.get_all()
        data = all_psy[(all_psy["email"] == email) & (all_psy["password"] == password)]
        return data

    @staticmethod
    def insert(
        first_name: str,
        last_name: str,
        cin: str,
        email: str,
        password: str,
        date_of_birth,
        phone: str = None,
        address: str = None,
        specialization: str = None,
        psy_type: str = None
    ):
        try:
            query = text("""
                INSERT INTO psychiatrists (
                    first_name,
                    last_name,
                    cin,
                    email,
                    password,
                    date_of_birth,
                    phone,
                    address,
                    specialization,
                    psy_type
                )
                VALUES (
                    :first_name,
                    :last_name,
                    :cin,
                    :email,
                    :password,
                    :date_of_birth,
                    :phone,
                    :address,
                    :specialization,
                    :psy_type
                )
                RETURNING id
            """)
            params = {
                "first_name": _encrypt_string(first_name),
                "last_name": _encrypt_string(last_name),
                "cin": _encrypt_string(cin),
                "email": _encrypt_string(email),
                "password": _encrypt_string(password),
                "date_of_birth": date_of_birth,
                "phone": _encrypt_string(phone),
                "address": _encrypt_string(address),
                "specialization": _encrypt_string(specialization),
                "psy_type": _encrypt_string(psy_type)
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
        psych_id: int,
        first_name: str = None,
        last_name: str = None,
        cin: str = None,
        email: str = None,
        password: str = None,
        date_of_birth=None,
        phone: str = None,
        address: str = None,
        specialization: str = None,
        account_verified: bool = None,
        psy_type: str = None
    ):
        try:
            query = text("""
                UPDATE psychiatrists
                SET
                    first_name = COALESCE(:first_name, first_name),
                    last_name = COALESCE(:last_name, last_name),
                    cin = COALESCE(:cin, cin),
                    email = COALESCE(:email, email),
                    password = COALESCE(:password, password),
                    date_of_birth = COALESCE(:date_of_birth, date_of_birth),
                    phone = COALESCE(:phone, phone),
                    address = COALESCE(:address, address),
                    specialization = COALESCE(:specialization, specialization),
                    account_verified = COALESCE(:account_verified, account_verified),
                    psy_type = COALESCE(:psy_type, psy_type),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = :id
            """)

            params = {
                "id": psych_id,
                "first_name": _encrypt_string(first_name),
                "last_name": _encrypt_string(last_name),
                "cin": _encrypt_string(cin),
                "email": _encrypt_string(email),
                "password": _encrypt_string(password),
                "date_of_birth": date_of_birth,
                "phone": _encrypt_string(phone),
                "address": _encrypt_string(address),
                "specialization": _encrypt_string(specialization),
                "account_verified": account_verified,
                "psy_type": _encrypt_string(psy_type)
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
    def delete(psych_id: int):
        try:
            query = text("DELETE FROM psychiatrists WHERE id = :id")
            params = {"id": psych_id}
            engine = DBConnector().get_engine()

            with engine.connect() as conn:
                conn.execute(query, parameters=params)
                conn.commit()
                return True

        except Exception as e:
            print(e)
            return False

def _decrypt(data: DataFrame) -> None:
    columns_to_decrypt = [
        "first_name", "last_name", "cin", "email", "password",
        "phone", "address", "specialization", "psy_type"
    ]

    for col in columns_to_decrypt:
        data[col] = data[col].apply(
            lambda val: _cipher.decrypt(str(val).encode()).decode() if val is not None else None
        )

def _encrypt_string(string: str)->str|None:
    if string is None:
        return None
    return _cipher.encrypt(string.encode()).decode()

def _decrypt_string(string: str)->str|None:
    if string is None:
        return None
    return _cipher.decrypt(str(string).encode()).decode()