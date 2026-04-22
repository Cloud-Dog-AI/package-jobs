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

# cloud_dog_jobs — Job state machine
"""State machine rules and transition validation."""

from __future__ import annotations

from dataclasses import dataclass

from cloud_dog_jobs.extensions.state_extensions import REGISTRY, register_state_extension as _register_state_extension


DEFAULT_TRANSITIONS: dict[str, set[str]] = {
    # --- Core states (PS-75 JQ4.1) ---
    "queued": {"scheduled", "running", "dispatched", "cancelled", "timeout"},
    "scheduled": {"queued", "running", "dispatched", "cancelled", "timeout"},
    "running": {"succeeded", "failed", "retry_wait", "cancelled", "paused", "blocked", "timeout", "ttl_expired"},
    "retry_wait": {"queued", "running", "failed", "cancelled", "timeout", "dead_lettered"},
    "paused": {"running", "cancelled", "timeout", "ttl_expired"},
    "succeeded": {"archived"},
    "failed": {"dead_lettered", "archived"},
    "cancelled": {"archived"},
    "timeout": {"retry_wait", "failed", "dead_lettered", "archived"},
    "ttl_expired": {"archived"},
    # --- Extended states (PS-75 JQ4, W28A-655) ---
    "created": {"validated", "cancelled"},
    "validated": {"queued", "failed"},
    "dispatched": {"running", "cancelled", "timeout"},
    "blocked": {"running", "cancelled", "timeout", "failed"},
    "dead_lettered": {"archived"},
    "archived": set(),
}


@dataclass(slots=True)
class JobStateMachine:
    """Configurable state machine for job lifecycle enforcement."""

    transitions: dict[str, set[str]]

    def __init__(self, transitions: dict[str, set[str]] | None = None) -> None:
        base = transitions or DEFAULT_TRANSITIONS
        self.transitions = {state: set(targets) for state, targets in base.items()}

    def register_state_extension(
        self,
        job_type: str,
        custom_states: set[str],
        custom_transitions: dict[str, set[str]],
    ) -> None:
        """Register domain-specific states and transitions for a job type."""
        _register_state_extension(job_type, custom_states, custom_transitions)

    def _merged_transitions_for(self, job_type: str | None) -> dict[str, set[str]]:
        merged = {state: set(targets) for state, targets in self.transitions.items()}
        if not job_type:
            return merged
        extension = REGISTRY.get(job_type)
        if extension is None:
            return merged
        for state in extension.custom_states:
            merged.setdefault(state, set())
        for state, targets in extension.custom_transitions.items():
            merged.setdefault(state, set()).update(targets)
        return merged

    def can_transition(self, from_state: str, to_state: str, *, job_type: str | None = None) -> bool:
        """Return whether transition is allowed."""
        transitions = self._merged_transitions_for(job_type)
        return to_state in transitions.get(from_state, set())

    def transition(self, from_state: str, to_state: str, *, job_type: str | None = None) -> str:
        """Validate and apply transition."""
        if not self.can_transition(from_state, to_state, job_type=job_type):
            raise ValueError(f"Invalid transition: {from_state} -> {to_state}")
        return to_state

    def is_terminal(self, state: str, *, job_type: str | None = None) -> bool:
        """Return whether the state is terminal."""
        transitions = self._merged_transitions_for(job_type)
        return len(transitions.get(state, set())) == 0

    def is_retryable(self, state: str) -> bool:
        """Return whether failed/retry_wait states allow retry logic."""
        return state in {"failed", "retry_wait", "timeout"}
