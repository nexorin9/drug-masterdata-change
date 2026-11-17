"""T24：话轮聚合、角色候选、未判定显式标注、要素角色关联、五类边界。"""
from dmchange.domain.models import Utterance
from dmchange.extract.roles import aggregate_turns, assign_roles, infer_role, attach_roles_to_evidence
from dmchange.domain.models import Evidence


def test_aggregate_turns():
    us = [Utterance("一", 0, 1000, "spk0"), Utterance("二", 1000, 2000, "spk0"),
          Utterance("三", 2000, 3000, "spk1")]
    turns = aggregate_turns(us)
    assert len(turns) == 2 and len(turns[0].utterances) == 2


def test_role_cue():
    turns = assign_roles([Utterance("我们药学部要改目录", 0, 1000, "spk0")])
    assert turns[0].role == "药事岗"


def test_unresolved_not_guessed():
    turns = assign_roles([Utterance("嗯，这个。", 0, 1000, "spk0")])
    assert turns[0].role == "未判定"


def test_both_claim_pharmacy():
    turns = assign_roles([Utterance("我们药学部，目录", 0, 1000, "spk0"),
                          Utterance("我们药学部，目录", 1001, 2000, "spk1")])
    assert all(t.role in ("药事岗", "未判定") for t in turns)


def test_attach_role_to_evidence():
    us = [Utterance("我们科室打电话", 0, 5000, "spk0")]
    turns = assign_roles(us)
    ev = [Evidence("spk0", 1000, 2000, "原话")]
    attach_roles_to_evidence(ev, turns)
    assert ev[0].role in ("临床科室", "未判定")
