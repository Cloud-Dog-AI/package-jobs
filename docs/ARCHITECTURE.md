# cloud_dog_jobs Architecture

## Purpose
`cloud_dog_jobs` provides shared queue, worker, scheduling, retry, and job lifecycle primitives for Cloud-Dog Python services.

## Main responsibilities
- enqueue, claim, execute, retry, and complete jobs
- coordinate worker polling and cancellation
- support SQL, Redis, and hybrid backends through common interfaces
- expose admin, progress, and audit integration helpers

## Main components
- queue and backend abstractions
- worker runtime and polling engine
- scheduler and policy modules
- admin and status helpers
- domain models for job requests, states, and results
