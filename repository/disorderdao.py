import pandas
from pandas.core.interchange.dataframe_protocol import DataFrame
from sqlalchemy import text

from repository.dbconnector import DBConnector


class DisorderDAO:
    def __init__(self):
        raise TypeError("cannot instantiate class DisorderDAO")

    @staticmethod
    def get_all()->DataFrame:
        query = text("SELECT * FROM disorders ORDER BY category_id, disorder_name")
        engine = DBConnector().get_engine()
        disorders_df = pandas.read_sql(query, engine)
        return disorders_df

    @staticmethod
    def get(disorder_id: int | list[int])->DataFrame:
        if isinstance(disorder_id, list):
            query = text("SELECT * FROM disorders WHERE disorder_id = ANY(:ids)")
            params = {"ids": disorder_id}
        else:
            query = text("SELECT * FROM disorders WHERE disorder_id = :disorder_id")
            params = {"disorder_id": disorder_id}

        engine = DBConnector().get_engine()
        return pandas.read_sql(query, engine, params=params)

    @staticmethod
    def get_by_category(category_id: int)->DataFrame:
        query = text("SELECT * FROM disorders WHERE category_id = :category_id ORDER BY disorder_name")
        params = {"category_id": category_id}
        engine = DBConnector().get_engine()
        disorders_df = pandas.read_sql(query, engine, params=params)
        return disorders_df

    @staticmethod
    def get_by_dsm_code(dsm_code: str):
        query = text("SELECT * FROM disorders WHERE dsm_code = :dsm_code")
        params = {"dsm_code": dsm_code}
        engine = DBConnector().get_engine()
        disorder_df = pandas.read_sql(query, engine, params=params)
        return disorder_df

    @staticmethod
    def get_by_parent(parent_disorder_id: int)->DataFrame:
        """
        Get all subtypes of a parent disorder.

        Args:
            parent_disorder_id: The parent disorder ID

        Returns:
            DataFrame with all subtypes of the parent disorder
        """
        query = text("SELECT * FROM disorders WHERE parent_disorder_id = :parent_disorder_id ORDER BY disorder_name")
        params = {"parent_disorder_id": parent_disorder_id}
        engine = DBConnector().get_engine()
        subtypes_df = pandas.read_sql(query, engine, params=params)
        return subtypes_df

    @staticmethod
    def get_main_disorders()->DataFrame:
        """
        Get all main disorders (not subtypes).

        Returns:
            DataFrame with all main disorders (where is_subtype = FALSE or parent_disorder_id IS NULL)
        """
        query = text(
            "SELECT * FROM disorders WHERE is_subtype = FALSE OR parent_disorder_id IS NULL ORDER BY category_id, disorder_name")
        engine = DBConnector().get_engine()
        main_disorders_df = pandas.read_sql(query, engine)
        return main_disorders_df

    @staticmethod
    def get_subtypes_only()->DataFrame:
        """
        Get all subtypes (not main disorders).

        Returns:
            DataFrame with all subtypes (where is_subtype = TRUE)
        """
        query = text("SELECT * FROM disorders WHERE is_subtype = TRUE ORDER BY parent_disorder_id, disorder_name")
        engine = DBConnector().get_engine()
        subtypes_df = pandas.read_sql(query, engine)
        return subtypes_df

    @staticmethod
    def get_disorder_hierarchy(disorder_id: int):
        """
        Get disorder with its parent (if subtype) or its subtypes (if main disorder).

        Args:
            disorder_id: The disorder ID to get hierarchy for

        Returns:
            Dictionary with 'disorder', 'parent' (if subtype), and 'subtypes' (if main disorder)
        """
        try:
            engine = DBConnector().get_engine()

            # Get the disorder itself
            disorder_query = text("SELECT * FROM disorders WHERE disorder_id = :disorder_id")
            disorder_df = pandas.read_sql(disorder_query, engine, params={"disorder_id": disorder_id})

            if disorder_df.empty:
                return None

            disorder = disorder_df.iloc[0].to_dict()
            result = {"disorder": disorder, "parent": None, "subtypes": []}

            # If it's a subtype, get its parent
            if disorder.get('parent_disorder_id'):
                parent_query = text("SELECT * FROM disorders WHERE disorder_id = :parent_disorder_id")
                parent_df = pandas.read_sql(parent_query, engine,
                                            params={"parent_disorder_id": disorder['parent_disorder_id']})
                if not parent_df.empty:
                    result["parent"] = parent_df.iloc[0].to_dict()

            # Get subtypes if it's a main disorder
            subtypes_query = text("SELECT * FROM disorders WHERE parent_disorder_id = :disorder_id")
            subtypes_df = pandas.read_sql(subtypes_query, engine, params={"disorder_id": disorder_id})
            if not subtypes_df.empty:
                result["subtypes"] = subtypes_df.to_dict('records')

            return result
        except Exception as e:
            print(e)
            return None

    @staticmethod
    def delete(disorder_id: int)->bool:
        try:
            query = text("DELETE FROM disorders WHERE disorder_id = :disorder_id")
            params = {"disorder_id": disorder_id}
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(query, parameters=params)
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def update(disorder_id: int, disorder_name: str = None, dsm_code: str = None,
               minimum_symptoms_required: int = None, category_id: int = None,
               parent_disorder_id: int = None, is_subtype: bool = None)->bool:
        try:
            updates = []
            params = {"disorder_id": disorder_id}

            if disorder_name is not None:
                updates.append("disorder_name = :disorder_name")
                params["disorder_name"] = disorder_name
            if dsm_code is not None:
                updates.append("dsm_code = :dsm_code")
                params["dsm_code"] = dsm_code
            if minimum_symptoms_required is not None:
                updates.append("minimum_symptoms_required = :minimum_symptoms_required")
                params["minimum_symptoms_required"] = minimum_symptoms_required
            if category_id is not None:
                updates.append("category_id = :category_id")
                params["category_id"] = category_id
            if parent_disorder_id is not None:
                updates.append("parent_disorder_id = :parent_disorder_id")
                params["parent_disorder_id"] = parent_disorder_id
            if is_subtype is not None:
                updates.append("is_subtype = :is_subtype")
                params["is_subtype"] = is_subtype

            if not updates:
                return True  # Nothing to update

            query = text(f"UPDATE disorders SET {', '.join(updates)} WHERE disorder_id = :disorder_id")
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(query, parameters=params)
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def insert(category_id: int, disorder_name: str, dsm_code: str = None,
               minimum_symptoms_required: int = None, parent_disorder_id: int = None,
               is_subtype: bool = False):
        try:
            query = text("""
                         INSERT INTO disorders(category_id, disorder_name, dsm_code, minimum_symptoms_required,
                                               parent_disorder_id, is_subtype)
                         VALUES (:category_id, :disorder_name, :dsm_code, :minimum_symptoms_required,
                                 :parent_disorder_id, :is_subtype)
                         RETURNING disorder_id
                         """)
            params = {
                "category_id": category_id,
                "disorder_name": disorder_name,
                "dsm_code": dsm_code,
                "minimum_symptoms_required": minimum_symptoms_required,
                "parent_disorder_id": parent_disorder_id,
                "is_subtype": is_subtype
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
    def get_with_symptom_count(disorder_id: int = None)->DataFrame:
        """
        Get disorder(s) with symptom count.
        Useful for checking if minimum_symptoms_required threshold is met.

        Args:
            disorder_id: Optional specific disorder, otherwise returns all

        Returns:
            DataFrame with disorder info + symptom_count column
        """
        try:
            if disorder_id is not None:
                query = text("""
                             SELECT d.*,
                                    COUNT(s.symptom_id) as symptom_count
                             FROM disorders d
                                      LEFT JOIN symptoms s ON d.disorder_id = s.disorder_id
                             WHERE d.disorder_id = :disorder_id
                             GROUP BY d.disorder_id
                             """)
                params = {"disorder_id": disorder_id}
            else:
                query = text("""
                             SELECT d.*,
                                    COUNT(s.symptom_id) as symptom_count
                             FROM disorders d
                                      LEFT JOIN symptoms s ON d.disorder_id = s.disorder_id
                             GROUP BY d.disorder_id
                             """)
                params = {}

            engine = DBConnector().get_engine()
            disorders_df = pandas.read_sql(query, engine, params=params)
            return disorders_df
        except Exception as e:
            print(e)
            return pandas.DataFrame()