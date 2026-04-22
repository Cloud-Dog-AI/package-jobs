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

from unittest.mock import patch

from cloud_dog_jobs.callbacks.manager import CallbackManager


class _Resp:
    status_code = 200


def test_callback_trigger_success() -> None:
    mgr = CallbackManager()
    mgr.register("job-1", "https://example.com/cb")
    with patch("cloud_dog_jobs.callbacks.manager.httpx.request", return_value=_Resp()) as mock_request:
        assert mgr.trigger("job-1", {"status": "ok"}, retries=0) is True
        mock_request.assert_called_once()
