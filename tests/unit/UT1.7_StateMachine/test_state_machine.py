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

from cloud_dog_jobs.domain.state_machine import JobStateMachine


def test_state_machine_transitions() -> None:
    sm = JobStateMachine()
    assert sm.can_transition("queued", "running")
    assert not sm.can_transition("succeeded", "running")
    assert sm.transition("running", "succeeded") == "succeeded"
    # failed can transition to dead_lettered/archived (W28A-656), so not terminal
    assert not sm.is_terminal("failed")
    assert sm.is_terminal("archived")
    assert sm.is_retryable("retry_wait")
