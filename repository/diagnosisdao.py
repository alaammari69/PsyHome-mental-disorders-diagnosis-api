import pandas
from pandas import DataFrame
from sqlalchemy import text

from models.response_schemas import DiagnosisAgentResponse
from repository.dbconnector import DBConnector


class DiagnosisDAO:
    def __init__(self):
        raise TypeError("cannot instantiate class DiagnosisDAO")

    @staticmethod
    def get(diagnosis_id: int) -> dict | None:
        engine = DBConnector().get_engine()
        query = text("""
                     SELECT d.id,
                            d.patient_id,
                            d.overall_confidence,
                            d.clinical_summary,
                            d.recommended_followup,
                            d.date_of_diagnosis,
                            dd.id as diagnosis_disorder_id,
                            dd.disorder_id,
                            dis.disorder_name,
                            dis.dsm_code,
                            dd.percentage,
                            dd.explanation,
                            json_agg(DISTINCT
                            jsonb_build_object('symptom_id', dds.symptom_id, 'symptom_name', ss.symptom_name))
                            FILTER (WHERE dds.symptom_id IS NOT NULL) as supporting_symptoms,
                            json_agg(DISTINCT
                            jsonb_build_object('symptom_id', ddc.symptom_id, 'symptom_name', cs.symptom_name))
                            FILTER (WHERE ddc.symptom_id IS NOT NULL) as contradicting_symptoms
                     FROM diagnosis d
                              LEFT JOIN diagnosis_disorder dd ON d.id = dd.diagnosis_id
                              LEFT JOIN disorders dis ON dd.disorder_id = dis.disorder_id
                              LEFT JOIN diagnosis_disorder_supporting_symptom dds ON dd.id = dds.diagnosis_disorder_id
                              LEFT JOIN symptoms ss ON dds.symptom_id = ss.symptom_id
                              LEFT JOIN diagnosis_disorder_contradicting_symptom ddc
                                        ON dd.id = ddc.diagnosis_disorder_id
                              LEFT JOIN symptoms cs ON ddc.symptom_id = cs.symptom_id
                     WHERE d.id = :diagnosis_id
                     GROUP BY d.id, d.patient_id, d.overall_confidence, d.clinical_summary,
                              d.recommended_followup, d.date_of_diagnosis,
                              dd.id, dis.disorder_name, dis.dsm_code
                     """)
        df = pandas.read_sql(query, engine, params={"diagnosis_id": diagnosis_id})

        if df.empty:
            return None

        first = df.iloc[0]
        result = {
            "id": int(first["id"]),
            "patient_id": int(first["patient_id"]),
            "overall_confidence": float(first["overall_confidence"]),
            "clinical_summary": first["clinical_summary"],
            "recommended_followup": first["recommended_followup"],
            "date_of_diagnosis": str(first["date_of_diagnosis"]),
            "disorders": [
                {
                    "id": int(row["diagnosis_disorder_id"]),
                    "disorder_id": int(row["disorder_id"]),
                    "disorder_name": row["disorder_name"],
                    "dsm_code": row["dsm_code"],
                    "percentage": float(row["percentage"]),
                    "explanation": row["explanation"],
                    "supporting_symptoms": row["supporting_symptoms"] or [],
                    "contradicting_symptoms": row["contradicting_symptoms"] or [],
                }
                for _, row in df.iterrows()
                if pandas.notna(row["diagnosis_disorder_id"])
            ]
        }
        return result

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
            print("ERROR WHILE SAVING DIAGNOSIS")
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