import pandas
from pandas.core.interchange.dataframe_protocol import DataFrame
from sqlalchemy import text

from repository.dbconnector import DBConnector


class DiagnosticCategoryDAO:
    def __init__(self):
        raise TypeError("cannot instantiate class DiagnosticCategoriesDao")

    @staticmethod
    def get_all()->DataFrame:
        query = text("SELECT * FROM diagnostic_categories")
        engine = DBConnector().get_engine()
        diag_categories_df = pandas.read_sql(query, engine)
        return diag_categories_df

    @staticmethod
    def get(category_id : int):
        query = text("SELECT * FROM diagnostic_categories WHERE category_id = :category_id")
        params = {"category_id": category_id}
        engine = DBConnector().get_engine()
        diag_category_df = pandas.read_sql(query, engine, params=params)
        return diag_category_df


    @staticmethod
    def delete(category_id : int):
        try:
            query = text("DELETE FROM diagnostic_categories WHERE category_id = :category_id")
            params = {"category_id": category_id}
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(query, parameters=params)
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def update(category_id : int, name : str = None, description : str = None):
        try:
            updates = []
            params = {"category_id": category_id}

            if name is not None:
                updates.append("category_name = :name")
                params["name"] = name
            if description is not None:
                updates.append("description = :description")
                params["description"] = description

            if not updates:
                return  # Nothing to update

            query = text(f"UPDATE diagnostic_categories SET {', '.join(updates)} WHERE category_id = :category_id")
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(query, parameters=params)
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def insert(name : str, description : str):
        try:
            query = text("""
                         INSERT INTO diagnostic_categories(category_name, description) 
                         VALUES (:name, :description)
                         RETURNING category_id
                         """)
            params = {"name": name, "description": description}
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                result = conn.execute(query, parameters=params)
                conn.commit()
                return result.fetchone()[0]
        except Exception as e:
            print(e)
            return None



