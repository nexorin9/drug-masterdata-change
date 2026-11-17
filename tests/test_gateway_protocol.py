"""T8：ModelGateway 协议兼容 + 超时/错误分类 + 审计元数据。替身只在测试层。"""
import json

import httpx
import pytest

from dmchange.config import Config
from dmchange.domain.errors import Http4xx, Http5xx, ParseError, SchemaInvalid, TimeoutError_
from dmchange.extract.gateway import ModelGateway

VALID_RESP = {
    "choices": [{"message": {"content": json.dumps({
        "elements": [{"drug_ref": "阿莫西林", "field_name": "spec_pack_code",
                      "cur_value": "0.25", "proposed_value": "0.5", "evidence_index": 0}],
        "roles": [],
    })}}]
}


class _FakeClient:
    def __init__(self, resp=None, status=200, raise_exc=None):
        self.resp, self.status, self.raise_exc = resp, status, raise_exc
        self.last = None

    def post(self, url, json=None, headers=None):
        self.last = {"url": url, "json": json, "headers": headers}
        if self.raise_exc:
            raise self.raise_exc
        return httpx.Response(self.status, json=self.resp if self.resp is not None else VALID_RESP)


def cfg():
    return Config("https://llm.example", "key-1234", "https://llm.example", "key-1234",
                  "m", 1.0, "local", "", "")


def test_request_contract():
    fc = _FakeClient()
    gw = ModelGateway(cfg(), http_client=fc)
    gw.call("提取要素")
    assert fc.last["url"] == "https://llm.example/v1/chat/completions"
    assert fc.last["json"]["response_format"] == {"type": "json_object"}
    assert fc.last["headers"]["Authorization"] == "Bearer key-1234"


def test_timeout_class():
    fc = _FakeClient(raise_exc=httpx.TimeoutException("timeout"))
    gw = ModelGateway(cfg(), http_client=fc)
    with pytest.raises(TimeoutError_) as e:
        gw.call("x")
    assert e.value.error_class == "timeout"


def test_http_errors():
    with pytest.raises(Http5xx):
        ModelGateway(cfg(), http_client=_FakeClient(status=500)).call("x")
    with pytest.raises(Http4xx):
        ModelGateway(cfg(), http_client=_FakeClient(status=400)).call("x")


def test_parse_error():
    with pytest.raises(ParseError):
        ModelGateway(cfg(), http_client=_FakeClient(resp={"bad": 1})).call("x")


def test_schema_invalid():
    bad = {"choices": [{"message": {"content": json.dumps({
        "elements": [{"field_name": "bogus_field"}], "roles": []})}}]}
    with pytest.raises(SchemaInvalid):
        ModelGateway(cfg(), http_client=_FakeClient(resp=bad)).call("x")


def test_audit_meta():
    metas = []
    gw = ModelGateway(cfg(), http_client=_FakeClient(), on_meta=metas.append)
    gw.call("x")
    assert len(metas) == 1
    assert metas[0].model == "m" and metas[0].request_id
