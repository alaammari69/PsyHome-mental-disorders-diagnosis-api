import ast

import numpy as np
import pandas
from pandas import DataFrame
from sqlalchemy import text, bindparam

from repository.dbconnector import DBConnector


class SymptomDAO:
    def __init__(self):
        raise TypeError("cannot instantiate class SymptomDAO")

    @staticmethod
    def get_all()->DataFrame:
        query = text("SELECT * FROM symptoms ORDER BY disorder_id")
        engine = DBConnector().get_engine()
        symptoms_df = pandas.read_sql(query, engine)

        # convert string embeddings to numpy arrays
        symptoms_df['embedding'] = symptoms_df['embedding'].apply(
            lambda x: np.array(ast.literal_eval(x), dtype=np.float32) if isinstance(x, str) else (
                np.array(x, dtype=np.float32) if x is not None else None)
        )

        return symptoms_df

    @staticmethod
    def get(symptom_id: int)->DataFrame:
        query = text("SELECT * FROM symptoms WHERE symptom_id = :symptom_id")
        params = {"symptom_id": symptom_id}
        engine = DBConnector().get_engine()
        symptom_df = pandas.read_sql(query, engine, params=params)

        symptom_df['embedding'] = symptom_df['embedding'].apply(
            lambda x: np.array(ast.literal_eval(x), dtype=np.float32) if isinstance(x, str) else (
                np.array(x, dtype=np.float32) if x is not None else None)
        )

        return symptom_df

    @staticmethod
    def get_many(symptom_ids: list[int]) -> DataFrame:
        query = text("""
                     SELECT *
                     FROM symptoms
                     WHERE symptom_id IN :symptom_ids
                     """).bindparams(bindparam("symptom_ids", expanding=True))

        params = {"symptom_ids": symptom_ids}
        engine = DBConnector().get_engine()
        symptom_df = pandas.read_sql(query, engine, params=params)

        symptom_df['embedding'] = symptom_df['embedding'].apply(
            lambda x: np.array(ast.literal_eval(x), dtype=np.float32)
            if isinstance(x, str)
            else (np.array(x, dtype=np.float32) if x is not None else None)
        )

        return symptom_df

    @staticmethod
    def get_by_disorder(disorder_id: int)->DataFrame:
        query = text("SELECT * FROM symptoms WHERE disorder_id = :disorder_id")
        params = {"disorder_id": disorder_id}
        engine = DBConnector().get_engine()
        symptoms_df = pandas.read_sql(query, engine, params=params)

        return symptoms_df

    @staticmethod
    def delete(symptom_id: int)->bool:
        try:
            query = text("DELETE FROM symptoms WHERE symptom_id = :symptom_id")
            params = {"symptom_id": symptom_id}
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(query, parameters=params)
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def update(symptom_id: int, disorder_id: int = None,symptom_name: str = None, symptom_description: str = None, embedding: list = None)->bool:
        try:
            updates = []
            params = {"symptom_id": symptom_id}
            if disorder_id is not None:
                updates.append("disorder_id = :disorder_id")
                params["disorder_id"] = disorder_id
            if symptom_name is not None:
                updates.append("symptom_name = :symptom_name")
                params["symptom_name"] = symptom_name
            if symptom_description is not None:
                updates.append("symptom_description = :symptom_description")
                params["symptom_description"] = symptom_description
            if embedding is not None:
                updates.append("embedding = :embedding")
                params["embedding"] = embedding

            if not updates:
                return True  # Nothing to update

            query = text(f"UPDATE symptoms SET {', '.join(updates)} WHERE symptom_id = :symptom_id")
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(query, parameters=params)
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def insert(disorder_id: int, symptom_name: str, symptom_description: str, embedding: list = None):
        try:
            query = text("""
                         INSERT INTO symptoms(disorder_id, symptom_name, symptom_description, embedding)
                         VALUES (:disorder_id, :symptom_name, :symptom_description, :embedding)
                         RETURNING symptom_id
                         """)
            params = {
                "disorder_id": disorder_id,
                "symptom_name": symptom_name,
                "symptom_description": symptom_description,
                "embedding": embedding if embedding is not None else None
            }
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                result = conn.execute(query, parameters=params)
                conn.commit()
                return result.fetchone()[0]
        except Exception as e:
            print(e)
            return None


