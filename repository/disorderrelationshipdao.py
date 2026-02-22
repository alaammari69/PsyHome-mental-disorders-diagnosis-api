import pandas
from sqlalchemy import text

from repository.dbconnector import DBConnector


#NOT TESTYD YET !!!
class DisorderRelationshipDAO:
    def __init__(self):
        raise TypeError("cannot instantiate class DisorderRelationshipDAO")

    @staticmethod
    def get_all():
        query = text("SELECT * FROM disorder_relationships ORDER BY disorder_id_1, disorder_id_2")
        engine = DBConnector().get_engine()
        relationships_df = pandas.read_sql(query, engine)
        return relationships_df

    @staticmethod
    def get(relationship_id: int):
        query = text("SELECT * FROM disorder_relationships WHERE relationship_id = :relationship_id")
        params = {"relationship_id": relationship_id}
        engine = DBConnector().get_engine()
        relationship_df = pandas.read_sql(query, engine, params=params)
        return relationship_df

    @staticmethod
    def get_by_disorder(disorder_id: int):
        """
        Get all relationships where the disorder is either disorder_id_1 or disorder_id_2.

        Args:
            disorder_id: The disorder ID to find relationships for

        Returns:
            DataFrame with all relationships involving this disorder
        """
        query = text("""
                     SELECT *
                     FROM disorder_relationships
                     WHERE disorder_id_1 = :disorder_id
                        OR disorder_id_2 = :disorder_id
                     ORDER BY relationship_type
                     """)
        params = {"disorder_id": disorder_id}
        engine = DBConnector().get_engine()
        relationships_df = pandas.read_sql(query, engine, params=params)
        return relationships_df

    @staticmethod
    def get_by_type(disorder_id: int, relationship_type: str):
        """
        Get relationships of a specific type for a disorder.

        Args:
            disorder_id: The disorder ID
            relationship_type: Type of relationship (differential, comorbid, etc.)

        Returns:
            DataFrame with filtered relationships
        """
        query = text("""
                     SELECT *
                     FROM disorder_relationships
                     WHERE (disorder_id_1 = :disorder_id OR disorder_id_2 = :disorder_id)
                       AND relationship_type = :relationship_type
                     """)
        params = {"disorder_id": disorder_id, "relationship_type": relationship_type}
        engine = DBConnector().get_engine()
        relationships_df = pandas.read_sql(query, engine, params=params)
        return relationships_df

    @staticmethod
    def get_related_disorders(disorder_id: int, relationship_type: str = None):
        """
        Get all disorders related to a given disorder, with optional type filter.
        Returns the related disorder IDs and names.

        Args:
            disorder_id: The disorder ID to find relations for
            relationship_type: Optional filter by relationship type

        Returns:
            DataFrame with related disorder info
        """
        if relationship_type is not None:
            query = text("""
                         SELECT dr.relationship_id,
                                dr.relationship_type,
                                dr.relationship_note,
                                CASE
                                    WHEN dr.disorder_id_1 = :disorder_id THEN dr.disorder_id_2
                                    ELSE dr.disorder_id_1
                                    END as related_disorder_id,
                                CASE
                                    WHEN dr.disorder_id_1 = :disorder_id THEN d2.disorder_name
                                    ELSE d1.disorder_name
                                    END as related_disorder_name,
                                CASE
                                    WHEN dr.disorder_id_1 = :disorder_id THEN d2.dsm_code
                                    ELSE d1.dsm_code
                                    END as related_disorder_code
                         FROM disorder_relationships dr
                                  JOIN disorders d1 ON dr.disorder_id_1 = d1.disorder_id
                                  JOIN disorders d2 ON dr.disorder_id_2 = d2.disorder_id
                         WHERE (dr.disorder_id_1 = :disorder_id OR dr.disorder_id_2 = :disorder_id)
                           AND dr.relationship_type = :relationship_type
                         ORDER BY related_disorder_name
                         """)
            params = {"disorder_id": disorder_id, "relationship_type": relationship_type}
        else:
            query = text("""
                         SELECT dr.relationship_id,
                                dr.relationship_type,
                                dr.relationship_note,
                                CASE
                                    WHEN dr.disorder_id_1 = :disorder_id THEN dr.disorder_id_2
                                    ELSE dr.disorder_id_1
                                    END as related_disorder_id,
                                CASE
                                    WHEN dr.disorder_id_1 = :disorder_id THEN d2.disorder_name
                                    ELSE d1.disorder_name
                                    END as related_disorder_name,
                                CASE
                                    WHEN dr.disorder_id_1 = :disorder_id THEN d2.dsm_code
                                    ELSE d1.dsm_code
                                    END as related_disorder_code
                         FROM disorder_relationships dr
                                  JOIN disorders d1 ON dr.disorder_id_1 = d1.disorder_id
                                  JOIN disorders d2 ON dr.disorder_id_2 = d2.disorder_id
                         WHERE dr.disorder_id_1 = :disorder_id
                            OR dr.disorder_id_2 = :disorder_id
                         ORDER BY dr.relationship_type, related_disorder_name
                         """)
            params = {"disorder_id": disorder_id}

        engine = DBConnector().get_engine()
        related_df = pandas.read_sql(query, engine, params=params)
        return related_df

    @staticmethod
    def delete(relationship_id: int):
        try:
            query = text("DELETE FROM disorder_relationships WHERE relationship_id = :relationship_id")
            params = {"relationship_id": relationship_id}
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(query, parameters=params)
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def update(relationship_id: int, relationship_type: str = None, relationship_note: str = None):
        try:
            updates = []
            params = {"relationship_id": relationship_id}

            if relationship_type is not None:
                # Validate relationship_type
                valid_types = DisorderRelationshipDAO.get_relationship_types()
                if relationship_type not in valid_types:
                    print(f"Invalid relationship_type '{relationship_type}'. Must be one of: {valid_types}")
                    return False
                updates.append("relationship_type = :relationship_type")
                params["relationship_type"] = relationship_type

            if relationship_note is not None:
                updates.append("relationship_note = :relationship_note")
                params["relationship_note"] = relationship_note

            if not updates:
                return True  # Nothing to update

            query = text(
                f"UPDATE disorder_relationships SET {', '.join(updates)} WHERE relationship_id = :relationship_id")
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(query, parameters=params)
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False

    @staticmethod
    def insert(disorder_id_1: int, disorder_id_2: int, relationship_type: str, relationship_note: str = None):
        try:
            # Validate relationship_type
            valid_types = DisorderRelationshipDAO.get_relationship_types()
            if relationship_type not in valid_types:
                print(f"Invalid relationship_type '{relationship_type}'. Must be one of: {valid_types}")
                return None

            # Validate disorders are different
            if disorder_id_1 == disorder_id_2:
                print("Cannot create relationship: disorder_id_1 and disorder_id_2 must be different")
                return None

            query = text("""
                         INSERT INTO disorder_relationships(disorder_id_1, disorder_id_2, relationship_type, relationship_note)
                         VALUES (:disorder_id_1, :disorder_id_2, :relationship_type, :relationship_note)
                         RETURNING relationship_id
                         """)
            params = {
                "disorder_id_1": disorder_id_1,
                "disorder_id_2": disorder_id_2,
                "relationship_type": relationship_type,
                "relationship_note": relationship_note
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
    def get_relationship_types():
        """
        Get all valid relationship types from the database constraint.
        Useful for validation and UI dropdowns.

        Returns:
            List of valid relationship type strings
        """
        return [
            'differential',
            'comorbid',
            'specifier_of',
            'subtype_of'
        ]

    @staticmethod
    def relationship_exists(disorder_id_1: int, disorder_id_2: int, relationship_type: str):
        """
        Check if a relationship already exists between two disorders.

        Args:
            disorder_id_1: First disorder ID
            disorder_id_2: Second disorder ID
            relationship_type: Type of relationship

        Returns:
            Boolean indicating if relationship exists
        """
        query = text("""
                     SELECT COUNT(*) as count
                     FROM disorder_relationships
                     WHERE disorder_id_1 = :disorder_id_1
                       AND disorder_id_2 = :disorder_id_2
                       AND relationship_type = :relationship_type
                     """)
        params = {
            "disorder_id_1": disorder_id_1,
            "disorder_id_2": disorder_id_2,
            "relationship_type": relationship_type
        }
        engine = DBConnector().get_engine()
        result_df = pandas.read_sql(query, engine, params=params)
        return result_df['count'].iloc[0] > 0 if not result_df.empty else False