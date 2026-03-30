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

import pytest

from cloud_dog_jobs.worker.handlers import HandlerRegistry


def test_handler_registry_register_get() -> None:
    reg = HandlerRegistry()

    def handler(ctx):
        return {"ok": True}

    reg.register("email", handler)
    assert reg.get("email") is handler

    with pytest.raises(KeyError):
        reg.get("missing")
