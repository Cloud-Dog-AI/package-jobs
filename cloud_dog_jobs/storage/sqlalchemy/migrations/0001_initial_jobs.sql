-- cloud_dog_jobs initial SQL migration (baseline)
-- Creates jobs table and core indexes for queue scans and admin lookups.

CREATE TABLE IF NOT EXISTS jobs (
  job_id VARCHAR(64) PRIMARY KEY,
  job_type VARCHAR(128) NOT NULL,
  queue_name VARCHAR(128) NOT NULL,
  payload JSON NOT NULL,
  meta JSON NOT NULL,
  status VARCHAR(32) NOT NULL,
  priority INTEGER NOT NULL,
  claimed_by VARCHAR(256),
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS job_callbacks (
  job_id VARCHAR(64) PRIMARY KEY,
  callback_url VARCHAR(512) NOT NULL,
  method VARCHAR(16) NOT NULL,
  headers JSON NOT NULL,
  retry_policy JSON NOT NULL,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  last_error VARCHAR(512),
  created_at TIMESTAMP NOT NULL,
  updated_at TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_priority_created ON jobs(priority DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_jobs_queue ON jobs(queue_name);
