import pandas
from pandas import DataFrame
from sqlalchemy import text

from models.response_schemas import DiagnosisAgentResponse
from repository.dbconnector import DBConnector


class DiagnosisDAO:
    def __init__(self):
        raise TypeError("cannot instantiate class DiagnosisDAO")

    @staticmethod
    def get(diagnosis_id: int) -> DataFrame:
        engine = DBConnector().get_engine()
        query = text("""
            SELECT 
                d.*,
                dd.id as diagnosis_disorder_id,
                dd.disorder_id,
                dd.percentage,
                dd.explanation,
                array_agg(DISTINCT dds.symptom_id) FILTER (WHERE dds.symptom_id IS NOT NULL) as supporting_symptom_ids,
                array_agg(DISTINCT ddc.symptom_id) FILTER (WHERE ddc.symptom_id IS NOT NULL) as contradicting_symptom_ids
            FROM diagnosis d
            LEFT JOIN diagnosis_disorder dd ON d.id = dd.diagnosis_id
            LEFT JOIN diagnosis_disorder_supporting_symptom dds ON dd.id = dds.diagnosis_disorder_id
            LEFT JOIN diagnosis_disorder_contradicting_symptom ddc ON dd.id = ddc.diagnosis_disorder_id
            WHERE d.id = :diagnosis_id
            GROUP BY d.id, d.patient_id, d.overall_confidence, d.clinical_summary, d.recommended_followup, d.date_of_diagnosis, dd.id
        """)
        return pandas.read_sql(query, engine, params={"diagnosis_id": diagnosis_id})

    @staticmethod
    def get_by_patient_id(patient_id: int) -> DataFrame:
        engine = DBConnector().get_engine()
        query = text("""
            SELECT 
                d.*,
                dd.id as diagnosis_disorder_id,
                dd.disorder_id,
                dd.percentage,
                dd.explanation,
                array_agg(DISTINCT dds.symptom_id) FILTER (WHERE dds.symptom_id IS NOT NULL) as supporting_symptom_ids,
                array_agg(DISTINCT ddc.symptom_id) FILTER (WHERE ddc.symptom_id IS NOT NULL) as contradicting_symptom_ids
            FROM diagnosis d
            LEFT JOIN diagnosis_disorder dd ON d.id = dd.diagnosis_id
            LEFT JOIN diagnosis_disorder_supporting_symptom dds ON dd.id = dds.diagnosis_disorder_id
            LEFT JOIN diagnosis_disorder_contradicting_symptom ddc ON dd.id = ddc.diagnosis_disorder_id
            WHERE d.patient_id = :patient_id
            GROUP BY d.id, d.patient_id, d.overall_confidence, d.clinical_summary, d.recommended_followup, d.date_of_diagnosis, dd.id
            ORDER BY d.date_of_diagnosis DESC
        """)
        return pandas.read_sql(query, engine, params={"patient_id": patient_id})

    @staticmethod
    def create(response: DiagnosisAgentResponse) -> int | None:
        try:
            engine = DBConnector().get_engine()
            with engine.connect() as conn:

                # insert diagnosis
                diag_query = text("""
                    INSERT INTO diagnosis (patient_id, overall_confidence, clinical_summary, recommended_followup, date_of_diagnosis)
                    VALUES (:patient_id, :overall_confidence, :clinical_summary, :recommended_followup, :date_of_diagnosis)
                    RETURNING id
                """)
                result = conn.execute(diag_query, parameters={
                    "patient_id": response.patient_id,
                    "overall_confidence": response.overall_confidence,
                    "clinical_summary": response.clinical_summary,
                    "recommended_followup": response.recommended_followup,
                    "date_of_diagnosis": response.date_of_diagnosis,
                })
                diagnosis_id = result.fetchone()[0]

                # insert each extracted disorder
                for extracted in response.extracted_disorders:
                    dd_query = text("""
                        INSERT INTO diagnosis_disorder (diagnosis_id, disorder_id, percentage, explanation)
                        VALUES (:diagnosis_id, :disorder_id, :percentage, :explanation)
                        RETURNING id
                    """)
                    dd_result = conn.execute(dd_query, parameters={
                        "diagnosis_id": diagnosis_id,
                        "disorder_id": extracted.disorder_id,
                        "percentage": extracted.percentage,
                        "explanation": extracted.explanation,
                    })
                    dd_id = dd_result.fetchone()[0]

                    # insert supporting symptoms
                    for symptom_id in extracted.supporting_symptoms_IDs:
                        conn.execute(text("""
                            INSERT INTO diagnosis_disorder_supporting_symptom (diagnosis_disorder_id, symptom_id)
                            VALUES (:dd_id, :symptom_id)
                        """), parameters={"dd_id": dd_id, "symptom_id": symptom_id})

                    # insert contradicting symptoms
                    for symptom_id in extracted.contradicting_symptoms_IDs:
                        conn.execute(text("""
                            INSERT INTO diagnosis_disorder_contradicting_symptom (diagnosis_disorder_id, symptom_id)
                            VALUES (:dd_id, :symptom_id)
                        """), parameters={"dd_id": dd_id, "symptom_id": symptom_id})

                conn.commit()
                return diagnosis_id

        except Exception as e:
            print(e)
            return None

    @staticmethod
    def delete(diagnosis_id: int) -> bool:
        try:
            engine = DBConnector().get_engine()
            with engine.connect() as conn:
                conn.execute(
                    text("DELETE FROM diagnosis WHERE id = :diagnosis_id"),
                    parameters={"diagnosis_id": diagnosis_id}
                )
                conn.commit()
                return True
        except Exception as e:
            print(e)
            return False