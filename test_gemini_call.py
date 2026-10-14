import pytest
from google.genai import errors

from gemini_call import generate_with_retry


class FakeClient:
    """Pretends to be the Gemini client. Each call gives the next prepared outcome: a reply or an error."""

    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0
        self.models = self

    def generate_content(self, model, contents, config):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def api_error(code):
    return errors.APIError(code, {"error": {"code": code, "message": "fake", "status": "FAKE"}})


def no_wait(seconds):
    pass


def test_a_good_reply_is_returned_without_retrying():
    client = FakeClient(["good reply"])
    result = generate_with_retry(client, "m", "prompt", None, sleep=no_wait)
    assert result == "good reply"
    assert client.calls == 1


def test_a_quota_error_is_retried_and_then_succeeds():
    client = FakeClient([api_error(429), "good reply"])
    result = generate_with_retry(client, "m", "prompt", None, sleep=no_wait)
    assert result == "good reply"
    assert client.calls == 2


def test_it_gives_up_after_the_maximum_number_of_attempts():
    client = FakeClient([api_error(503)] * 4)
    with pytest.raises(errors.APIError):
        generate_with_retry(client, "m", "prompt", None, max_attempts=4, sleep=no_wait)
    assert client.calls == 4


def test_an_error_that_waiting_cannot_fix_is_not_retried():
    client = FakeClient([api_error(400), "good reply"])
    with pytest.raises(errors.APIError):
        generate_with_retry(client, "m", "prompt", None, sleep=no_wait)
    assert client.calls == 1