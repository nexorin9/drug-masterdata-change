"""T9：schema.py 的 pydantic 校验细节。"""
import pytest

from dmchange.extract.schema import ExtractionModel, validate_extraction
from pydantic import ValidationError


def test_valid():
    m = validate_extraction({"elements": [], "roles": [{"speaker": "spk0", "role": "药事岗"}]})
    assert isinstance(m, ExtractionModel)


def test_from_json_string():
    m = validate_extraction('{"elements": [], "roles": []}')
    assert m.elements == []


def test_evidence_index_default():
    m = validate_extraction({"elements": [{"field_name": "name_code"}], "roles": []})
    assert m.elements[0].evidence_index == -1


def test_non_json_text():
    with pytest.raises(Exception):
        validate_extraction("not json at all")
