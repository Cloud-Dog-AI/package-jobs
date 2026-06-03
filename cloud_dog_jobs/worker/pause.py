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

# cloud_dog_jobs — Pause controls
"""Simple pause/resume controls for cooperative handlers."""

from threading import Event


class PauseController:
    """Pause and resume control primitive."""

    def __init__(self) -> None:
        self._paused = Event()

    def pause_task(self) -> None:
        """Handle pause task."""
        self._paused.set()

    def resume_task(self) -> None:
        """Handle resume task."""
        self._paused.clear()

    def is_paused(self) -> bool:
        """Return whether paused."""
        return self._paused.is_set()
