"""Runs the P6 ground-truth scenarios under pytest. Scenarios with a known_issue are strict xfails:
they must keep failing until the defect is fixed, and then the suite tells you to delete the note."""
import pytest

from evals.run import run_scenario
from evals.scenarios import SCENARIOS


def _param(s):
    marks = [pytest.mark.xfail(strict=True, reason=s.known_issue)] if s.known_issue else []
    return pytest.param(s, id=s.id, marks=marks)


@pytest.mark.parametrize("scenario", [_param(s) for s in SCENARIOS])
def test_scenario(scenario):
    outcome = run_scenario(scenario)
    failed = [f"{n}: {d}" for n, ok, d in outcome.checks if not ok]
    assert not failed, "; ".join(failed)


def test_there_are_ten_scenarios():
    assert len(SCENARIOS) == 10
    assert len({s.id for s in SCENARIOS}) == 10
