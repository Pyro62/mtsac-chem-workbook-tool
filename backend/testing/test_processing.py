"""
Unit tests for assessment_processor.py

Run with:  pytest test_assessment_processor.py -v
"""
import math
import os

import numpy as np
import pandas as pd
import pytest
from fastapi import HTTPException

import sys
from pathlib import Path
# Add the parent directory (backend) to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import processing as ap


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def make_student_row(num_questions, num_correct, earned_pts, zip_grade_id=1234567,
                      percent_correct=50.0):
    """
    Build a pd.Series that mimics a single row of the assessment (ZipGrade) export.
    `earned_pts` is a list of the EarnedPtN values, 1-indexed by position.
    """
    data = {
        "QuizName": "Math Pre-Assessment",
        "QuizClass": np.nan,
        "ZipGradeID": zip_grade_id,
        "NumberCorrect": num_correct,
        "NumbeOfQuestions": num_questions,  # NOTE: typo matches production column name
        "PercentCorrect": percent_correct,
    }
    for i, pts in enumerate(earned_pts, start=1):
        data[f"EarnedPt{i}"] = pts
    return pd.Series(data)


def make_student_info_df(students):
    """
    Build a student_info_df in the same shape as classList.xls (header=None).
    `students` is a list of (raw_name, id) tuples, e.g. ("Robles, Rafael A", "A01234567").
    """
    header_rows = [
        ["Course Information", np.nan, np.nan],
        ["Course Title", "Intro Chem", np.nan],
        ["Term", "Fall 2026", np.nan],
        ["CRN", "20373", np.nan],
        ["Duration", "08/24/2026 - 12/13/2026", np.nan],
        ["Status", "Open", np.nan],
        [np.nan, np.nan, np.nan],
        ["Enrollment Counts", np.nan, np.nan],
        [np.nan, "Maximum", "Actual"],
        ["Enrollment", "24", "24"],
        ["Wait List", "5", "5"],
        ["Cross List", "0", "0"],
        [np.nan, np.nan, np.nan],
        ["Summary Class List", np.nan, np.nan],
        ["Student Name", "ID", "Registration Status"],
    ]
    rows = header_rows + [[name, sid, "**Web Registered**"] for name, sid in students]
    return pd.DataFrame(rows)


@pytest.fixture
def sample_files_dir():
    return os.path.join(os.path.dirname(__file__), "testing_data")


# ---------------------------------------------------------------------------
# get_student_name
# ---------------------------------------------------------------------------

class TestGetStudentName:
    def test_maps_ids_to_formatted_names(self):
        df = make_student_info_df([
            ("Robles, Rafael A", "A01234567"),
            ("Leung, Jenny", "A09876543"),
        ])
        result = ap.get_student_name(df, 2)
        assert result == {
            "A01234567": "Rafael R.",
            "A09876543": "Jenny L.",
        }

    def test_handles_single_student(self):
        df = make_student_info_df([("Smith, John Q", "A01111111")])
        result = ap.get_student_name(df, 1)
        assert result == {"A01111111": "John S."}

    def test_raises_when_more_students_requested_than_rows_exist(self):
        df = make_student_info_df([("Robles, Rafael A", "A01234567")])
        with pytest.raises(HTTPException) as exc_info:
            ap.get_student_name(df, 2)  # asks for 2 but only 1 row exists
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# get_incorrect_questions
# ---------------------------------------------------------------------------

class TestGetIncorrectQuestions:
    def test_identifies_zero_point_questions(self):
        # correct: q1, q4 | incorrect: q2, q3
        row = make_student_row(num_questions=4, num_correct=2, earned_pts=[1, 0, 0, 1])
        assert ap.get_incorrect_questions(row) == [2, 3]

    def test_all_correct_returns_empty_list(self):
        row = make_student_row(num_questions=3, num_correct=3, earned_pts=[1, 1, 1])
        assert ap.get_incorrect_questions(row) == []

    def test_all_incorrect_returns_every_question(self):
        row = make_student_row(num_questions=3, num_correct=0, earned_pts=[0, 0, 0])
        assert ap.get_incorrect_questions(row) == [1, 2, 3]

    def test_single_incorrect_question_mid_quiz(self):
        row = make_student_row(num_questions=5, num_correct=4,
                                earned_pts=[1, 1, 0, 1, 1])
        assert ap.get_incorrect_questions(row) == [3]


# ---------------------------------------------------------------------------
# get_topics_to_review
# ---------------------------------------------------------------------------

class TestGetTopicsToReview:
    def test_maps_questions_to_expected_topics(self):
        # 4 questions -> topic_count = 2 -> q1,q3 => topic 1 ("2.1"); q2,q4 => topic 2 ("2.2")
        row = make_student_row(num_questions=4, num_correct=0, earned_pts=[0, 0, 0, 0])
        result = ap.get_topics_to_review([1, 2], row)
        assert result == ["2.1: Positive and Negative Numbers",
                           "2.2: Number Line and Place Values"]

    def test_duplicate_questions_map_to_same_topic_deduped(self):
        # q1 and q3 both fall under topic "2.1" -> should only appear once
        row = make_student_row(num_questions=4, num_correct=0, earned_pts=[0, 0, 0, 0])
        result = ap.get_topics_to_review([1, 3], row)
        assert result == ["2.1: Positive and Negative Numbers"]

    def test_empty_incorrect_list_returns_empty(self):
        row = make_student_row(num_questions=4, num_correct=4, earned_pts=[1, 1, 1, 1])
        assert ap.get_topics_to_review([], row) == []

    def test_results_sorted_numerically_not_lexicographically(self):
        # With 34 questions, topic_count = 17, so we can reach "2.10" and beyond,
        # which would sort incorrectly ("2.10" < "2.2") under plain string sort.
        row = make_student_row(num_questions=34, num_correct=0,
                                earned_pts=[0] * 34)
        # question 10 -> topic_num 10 -> "2.10"; question 2 -> topic_num 2 -> "2.2"
        result = ap.get_topics_to_review([10, 2], row)
        assert result == ["2.2: Number Line and Place Values",
                           "2.10: Solving Simple Algebraic Equations"]

    def test_unknown_topic_key_falls_back_to_placeholder(self):
        # 40 questions -> topic_count = 20 -> topic keys beyond "2.17" aren't in TOPIC_MAP
        row = make_student_row(num_questions=40, num_correct=0, earned_pts=[0] * 40)
        result = ap.get_topics_to_review([18], row)
        assert result == ["2.18: Unknown Topic"]


# ---------------------------------------------------------------------------
# get_stu_id
# ---------------------------------------------------------------------------

class TestGetStuId:
    def test_returns_zip_grade_id_when_present(self):
        row = make_student_row(num_questions=2, num_correct=2, earned_pts=[1, 1],
                                zip_grade_id=1234567)
        assert ap.get_stu_id(row, 0) == 1234567

    def test_returns_temp_id_when_zip_grade_id_missing(self):
        row = make_student_row(num_questions=2, num_correct=2, earned_pts=[1, 1],
                                zip_grade_id=np.nan)
        assert ap.get_stu_id(row, 4) == "Temp ID #5"


# ---------------------------------------------------------------------------
# get_stu_score
# ---------------------------------------------------------------------------

class TestGetStuScore:
    def test_formats_percent_correct(self):
        row = make_student_row(num_questions=2, num_correct=1, earned_pts=[1, 0],
                                percent_correct=31.3)
        assert ap.get_stu_score(row) == "31.3%"

    def test_defaults_to_zero_percent_when_missing(self):
        row = make_student_row(num_questions=2, num_correct=1, earned_pts=[1, 0],
                                percent_correct=np.nan)
        assert ap.get_stu_score(row) == "0%"


# ---------------------------------------------------------------------------
# get_class_data
# ---------------------------------------------------------------------------

class TestGetClassData:
    def test_computes_average_and_topic_counts(self):
        result_dict = {
            "A01": {"name": "A A.", "score": "50.0%",
                    "topics_to_review": ["2.1: Positive and Negative Numbers"]},
            "A02": {"name": "B B.", "score": "70.0%",
                    "topics_to_review": ["2.1: Positive and Negative Numbers",
                                         "2.2: Number Line and Place Values"]},
        }
        class_data = ap.get_class_data(result_dict)

        assert class_data["average"] == 60.0

        missed_topics = dict(class_data["missed_topics"])
        assert missed_topics["2.1"] == 2
        assert missed_topics["2.2"] == 1
        # untouched topics should still be present, with a count of 0
        assert missed_topics["2.17"] == 0

    def test_missed_topics_sorted_descending(self):
        result_dict = {
            "A01": {"name": "A A.", "score": "0%",
                    "topics_to_review": ["2.3: Number Sense"]},
            "A02": {"name": "B B.", "score": "0%",
                    "topics_to_review": ["2.3: Number Sense"]},
            "A03": {"name": "C C.", "score": "0%",
                    "topics_to_review": ["2.1: Positive and Negative Numbers"]},
        }
        class_data = ap.get_class_data(result_dict)
        top_topic, top_count = class_data["missed_topics"][0]
        assert top_topic == "2.3"
        assert top_count == 2

    def test_single_student_average_equals_their_score(self):
        result_dict = {
            "A01": {"name": "A A.", "score": "83.5%", "topics_to_review": []},
        }
        class_data = ap.get_class_data(result_dict)
        assert class_data["average"] == 83.5


# ---------------------------------------------------------------------------
# validate_test_df
# ---------------------------------------------------------------------------

class TestValidateTestDf:
    def test_passes_with_required_columns(self):
        df = pd.DataFrame(columns=["QuizName", "QuizClass", "ZipGradeID", "Other"])
        ap.validate_test_df(df)  # should not raise

    def test_raises_when_missing_required_column(self):
        df = pd.DataFrame(columns=["QuizName", "ZipGradeID"])  # missing QuizClass
        with pytest.raises(HTTPException) as exc_info:
            ap.validate_test_df(df)
        assert exc_info.value.status_code == 400

    def test_raises_on_completely_wrong_file(self):
        df = pd.DataFrame(columns=["Foo", "Bar"])
        with pytest.raises(HTTPException):
            ap.validate_test_df(df)


# ---------------------------------------------------------------------------
# validate_student_df
# ---------------------------------------------------------------------------

class TestValidateStudentDf:
    def test_passes_with_all_expected_labels(self):
        df = make_student_info_df([("Robles, Rafael A", "A01234567")])
        ap.validate_student_df(df)  # should not raise

    def test_raises_when_expected_labels_missing(self):
        df = pd.DataFrame({0: ["Course Information", "Course Title"]})
        with pytest.raises(HTTPException) as exc_info:
            ap.validate_student_df(df)
        assert exc_info.value.status_code == 400


# ---------------------------------------------------------------------------
# process_assessment (integration, in-memory)
# ---------------------------------------------------------------------------

class TestProcessAssessmentInMemory:
    def _build_test_df(self, rows):
        return pd.DataFrame(rows)

    def test_end_to_end_two_students(self):
        student_info_df = make_student_info_df([
            ("Robles, Rafael A", "A01234567"),
            ("Leung, Jenny", "A09876543"),
        ])

        row1 = make_student_row(num_questions=4, num_correct=2,
                                 earned_pts=[1, 0, 0, 1],
                                 zip_grade_id=1234567, percent_correct=50.0)
        row2 = make_student_row(num_questions=4, num_correct=4,
                                 earned_pts=[1, 1, 1, 1],
                                 zip_grade_id=9876543, percent_correct=100.0)
        test_df = pd.DataFrame([row1, row2])

        result = ap.process_assessment(test_df, student_info_df)

        assert set(result.keys()) == {"A01234567", "A09876543"}
        assert result["A01234567"]["name"] == "Rafael R."
        assert result["A01234567"]["score"] == "50.0%"
        assert result["A01234567"]["topics_to_review"] == [
            "2.1: Positive and Negative Numbers",
            "2.2: Number Line and Place Values",
        ]
        assert result["A09876543"]["name"] == "Jenny L."
        assert result["A09876543"]["score"] == "100.0%"
        assert result["A09876543"]["topics_to_review"] == []

    def test_without_student_info_uses_placeholder_name(self):
        row1 = make_student_row(num_questions=2, num_correct=2,
                                 earned_pts=[1, 1], zip_grade_id=1234567,
                                 percent_correct=100.0)
        test_df = pd.DataFrame([row1])

        result = ap.process_assessment(test_df, student_info_df=None)

        assert result["A01234567"]["name"] == "Chemistry Student"

    def test_mismatched_files_raise_http_exception(self):
        # student_info_df only knows about one student, but assessment has two rows
        student_info_df = make_student_info_df([("Robles, Rafael A", "A01234567")])

        row1 = make_student_row(num_questions=2, num_correct=2, earned_pts=[1, 1],
                                 zip_grade_id=1234567)
        row2 = make_student_row(num_questions=2, num_correct=2, earned_pts=[1, 1],
                                 zip_grade_id=9999999)
        test_df = pd.DataFrame([row1, row2])

        with pytest.raises(HTTPException) as exc_info:
            ap.process_assessment(test_df, student_info_df)
        assert exc_info.value.status_code == 400

    def test_invalid_assessment_file_raises_before_processing(self):
        bad_test_df = pd.DataFrame({"NotAQuizColumn": [1, 2]})
        with pytest.raises(HTTPException):
            ap.process_assessment(bad_test_df, None)


# ---------------------------------------------------------------------------
# process_assessment (integration, real uploaded sample files)
# ---------------------------------------------------------------------------

class TestProcessAssessmentWithSampleFiles:
    def test_loads_and_processes_real_sample_files(self, sample_files_dir):
        student_info_df = pd.read_excel(
            os.path.join(sample_files_dir, "classList.xls"), header=None
        )
        test_df = pd.read_excel(
            os.path.join(sample_files_dir, "newAssessment.xlsx")
        )

        result = ap.process_assessment(test_df, student_info_df)

        # One result entry per row in the assessment export
        assert len(result) == test_df.shape[0]

        for student_id, info in result.items():
            assert student_id.startswith("A0")
            assert "name" in info and info["name"] != ""
            assert info["score"].endswith("%")
            assert isinstance(info["topics_to_review"], list)

    def test_class_data_from_real_sample_files(self, sample_files_dir):
        student_info_df = pd.read_excel(
            os.path.join(sample_files_dir, "classList.xls"), header=None
        )
        test_df = pd.read_excel(
            os.path.join(sample_files_dir, "newAssessment.xlsx")
        )

        result = ap.process_assessment(test_df, student_info_df)
        class_data = ap.get_class_data(result)

        assert isinstance(class_data["average"], float)
        assert 0.0 <= class_data["average"] <= 100.0
        assert len(class_data["missed_topics"]) == len(ap.TOPIC_MAP)
        # descending order check
        counts = [c for _, c in class_data["missed_topics"]]
        assert counts == sorted(counts, reverse=True)
