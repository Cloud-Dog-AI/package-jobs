# cloud_dog_jobs Examples

## Submit a job
```python
from cloud_dog_jobs.domain.models import JobRequest

request = JobRequest(job_type="example", queue_name="default", payload={"x": 1})
job_id = await queue.submit(request)
```
