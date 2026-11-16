"""The trusted HTTP request budget must not restart inside the model pipeline."""
import time
from test_phase10_assistant_runtime import state


def test_already_expired_request_budget_prevents_provider_call(state):
    _,runtime,provider,_,one,_,_,_=state
    answer=runtime.answer('What does allowance mean?',token=one.token,consent=True,
                          deadline=time.monotonic()-1)
    assert answer.mode=='faq' and provider.calls==[]
