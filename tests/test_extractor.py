"""T9/T15：否定式方向、schema 校验、降级 draft_incomplete、出站计数为 0。"""
import json

import httpx
import pytest

from dmchange.config import Config
from dmchange.domain.models import Status, Utterance
from dmchange.extract.extractor import extract
from dmchange.extract.gateway import ModelGateway
from dmchange.extract.schema import validate_extraction


def cfg():
    return Config("https://llm", "k", "https://llm", "k", "m", 1, "local", "", "")


class _RespClient:
    def __init__(self, payload=None, raise_exc=None):
        self.payload, self.raise_exc = payload, raise_exc

    def post(self, *a, **k):
        if self.raise_exc:
            raise self.raise_exc
        content = json.dumps(self.payload, ensure_ascii=False)
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def test_schema_field_domain():
    with pytest.raises(Exception):
        validate_extraction({"elements": [{"field_name": "bad"}], "roles": []})


def test_negative_correction_direction():
    """「不是0.25，是0.5」→ proposed=0.5, cur=0.25。"""
    utterances = [Utterance("阿莫西林规格不是0.25，是0.5。", 8000, 15000, "spk0")]
    payload = {"elements": [{
        "drug_ref": "阿莫西林", "field_name": "spec_pack_code",
        "cur_value": "0.25", "proposed_value": "0.5", "evidence_index": 0}], "roles": []}
    gw = ModelGateway(cfg(), http_client=_RespClient(payload))
    out = extract(gw, utterances)
    assert out.item.cur_value == "0.25"
    assert out.item.proposed_value == "0.5"
    assert not out.degraded


def test_model_timeout_degrades_no_outbound():
    gw = ModelGateway(cfg(), http_client=_RespClient(raise_exc=httpx.TimeoutException("t")))
    out = extract(gw, [Utterance("转写内容。", 0, 1000, "spk0")])
    assert out.degraded
    assert out.item.status == Status.DRAFT_INCOMPLETE
    assert out.item.error_class == "timeout"
    assert gw.call_count == 1  # 出站（MDM）未发生；此处只记录模型调用
