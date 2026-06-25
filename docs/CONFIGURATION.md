# cloud_dog_jobs Configuration

## Typical inputs
Common consumer settings include:
- backend type
- queue name
- database or Redis connection details
- worker poll interval
- retry policy and timeout values
- concurrency limits
- retention and purge settings

## Guidance
- treat backend credentials as Vault-backed secrets
- keep queue names stable across worker and service runtimes
- set timeouts and retention through config, not source constants
