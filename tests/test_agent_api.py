from pathlib import Path

import pytest

from novelops_agent.repository import JsonRepository
from scripts.serve_agent_api import AgentService, TargetResolutionError


SEED_DATA = Path(__file__).parents[1] / "seed_data" / "novelops_seed_50.json"


def service_for_resolution() -> AgentService:
    service = AgentService.__new__(AgentService)
    service.repository = JsonRepository(SEED_DATA)
    return service


def test_resolves_novel_from_title_without_id():
    target = service_for_resolution()._resolve_target("", "检查《雾港来信》的结算")
    assert target == {"id": "N001", "title": "雾港来信"}


def test_resolves_novel_id_embedded_in_natural_language():
    target = service_for_resolution()._resolve_target("", "请全面检查N043")
    assert target["id"] == "N043"


def test_policy_lookup_does_not_require_a_novel():
    target = service_for_resolution()._resolve_target("", "番茄第三个月全勤门槛是多少")
    assert target == {"id": "", "title": "制度查询"}


def test_business_audit_without_target_requests_clarification():
    with pytest.raises(TargetResolutionError):
        service_for_resolution()._resolve_target("", "检查这本书的结算异常")
