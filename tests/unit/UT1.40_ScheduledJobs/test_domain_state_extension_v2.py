# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import pytest

from cloud_dog_jobs.domain.state_machine import JobStateMachine


def test_register_state_extension_and_validate_transitions() -> None:
    sm = JobStateMachine()
    sm.register_state_extension(
        "notification",
        custom_states={"delivery_pending", "delivery_sent"},
        custom_transitions={
            "delivery_pending": {"delivery_sent", "failed"},
            "delivery_sent": {"succeeded"},
        },
    )

    assert sm.can_transition("queued", "running", job_type="notification") is True
    assert sm.can_transition("delivery_pending", "delivery_sent", job_type="notification") is True
    assert sm.can_transition("delivery_sent", "succeeded", job_type="notification") is True
    assert sm.can_transition("delivery_sent", "queued", job_type="notification") is False


def test_multiple_job_types_get_independent_extensions() -> None:
    sm = JobStateMachine()
    sm.register_state_extension(
        "sql",
        custom_states={"validating", "executing"},
        custom_transitions={"validating": {"executing"}, "executing": {"succeeded", "failed"}},
    )
    sm.register_state_extension(
        "notify",
        custom_states={"delivery_pending"},
        custom_transitions={"delivery_pending": {"succeeded", "failed"}},
    )

    assert sm.can_transition("validating", "executing", job_type="sql") is True
    assert sm.can_transition("validating", "executing", job_type="notify") is False


def test_invalid_custom_transition_source_rejected() -> None:
    sm = JobStateMachine()
    with pytest.raises(ValueError, match="source"):
        sm.register_state_extension(
            "bad",
            custom_states={"a"},
            custom_transitions={"missing": {"a"}},
        )
