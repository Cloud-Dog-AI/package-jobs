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

# cloud_dog_jobs — Domain state-machine extensions
"""Registry for job-type specific state extensions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class StateExtension:
    """Represent state extension."""
    job_type: str
    custom_states: set[str]
    custom_transitions: dict[str, set[str]]


class StateExtensionRegistry:
    """Thread-local-free in-process state extension registry."""

    def __init__(self) -> None:
        self._extensions: dict[str, StateExtension] = {}

    def register_state_extension(
        self,
        job_type: str,
        custom_states: set[str],
        custom_transitions: dict[str, set[str]],
    ) -> None:
        """Register state extension."""
        states = set(custom_states)
        transitions = {state: set(targets) for state, targets in custom_transitions.items()}
        for state, targets in transitions.items():
            if state not in states:
                raise ValueError(f"Custom transition source not in custom states: {state}")
            invalid_targets = [target for target in targets if not target]
            if invalid_targets:
                raise ValueError(f"Custom transition target is invalid for {state}")
        self._extensions[job_type] = StateExtension(
            job_type=job_type,
            custom_states=states,
            custom_transitions=transitions,
        )

    def get(self, job_type: str) -> StateExtension | None:
        """Handle get."""
        return self._extensions.get(job_type)

    def clear(self) -> None:
        """Handle clear."""
        self._extensions.clear()


REGISTRY = StateExtensionRegistry()


def register_state_extension(
    job_type: str,
    custom_states: set[str],
    custom_transitions: dict[str, set[str]],
) -> None:
    """Convenience API used by callers and tests."""
    REGISTRY.register_state_extension(job_type, custom_states, custom_transitions)
