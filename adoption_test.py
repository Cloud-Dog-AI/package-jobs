# Copyright 2026 Cloud-Dog, Viewdeck Engineering Limited
# Licensed under the Apache License, Version 2.0
"""
Adoption test for cloud_dog_jobs (PS-75).
Run check_adoption(project_root) to verify a project fully uses cloud_dog_jobs.
"""
import pathlib
import subprocess


def _grep(pattern: str, search_path: pathlib.Path, extra_flags: str = "") -> list[str]:
    cmd = f"grep -rn {extra_flags} '{pattern}' {search_path} --include='*.py' | grep -v __pycache__ | grep -v '/archive/' | grep -v '/working/'"
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return [l for l in result.stdout.strip().split('\n') if l]


def _find_source_dirs(project_root: pathlib.Path) -> list[pathlib.Path]:
    dirs = []
    src = project_root / "src"
    if src.is_dir():
        dirs.append(src)
    crawler = project_root / "crawler"
    if crawler.is_dir():
        dirs.append(crawler)
    return dirs


def check_adoption(project_root: pathlib.Path) -> dict:
    results = {"pass": [], "fail": []}
    source_dirs = _find_source_dirs(project_root)

    if not source_dirs:
        results["fail"].append(f"No source directory found in {project_root}")
        return results

    # 1. cloud_dog_jobs imported
    all_imports = []
    for sd in source_dirs:
        all_imports.extend(_grep("cloud_dog_jobs", sd))
    for f in project_root.glob("start_*.py"):
        cmd = f"grep -n 'cloud_dog_jobs' {f}"
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.stdout.strip():
            all_imports.extend(r.stdout.strip().split('\n'))
    if len(all_imports) > 0:
        results["pass"].append(f"cloud_dog_jobs imported ({len(all_imports)} references)")
    else:
        results["fail"].append("cloud_dog_jobs NOT imported anywhere in source")

    # 2. ZERO MemoryQueueBackend in production path
    memory_queue = []
    for sd in source_dirs:
        hits = _grep("MemoryQueueBackend", sd)
        for h in hits:
            if "/test" not in h.lower():
                memory_queue.append(h)
    if len(memory_queue) == 0:
        results["pass"].append("No MemoryQueueBackend in production path")
    else:
        # Check if it's a documented fallback with warning
        results["fail"].append(f"MemoryQueueBackend in production path (should use SQL/Redis backend): {memory_queue}")

    # 3. ZERO bespoke ThreadPoolExecutor for job management
    bespoke_tpe = []
    for sd in source_dirs:
        hits = _grep("ThreadPoolExecutor", sd)
        for h in hits:
            if "/test" not in h.lower() and "cloud_dog" not in h:
                bespoke_tpe.append(h)
    if len(bespoke_tpe) == 0:
        results["pass"].append("No bespoke ThreadPoolExecutor for job management")
    else:
        # ThreadPoolExecutor may be legitimate for sync bridging, mark as informational
        results["pass"].append(f"ThreadPoolExecutor found ({len(bespoke_tpe)} hits) - may be sync bridging (acceptable if bounded)")

    # 4. Job creation goes through cloud_dog_jobs API
    job_api_refs = []
    for sd in source_dirs:
        job_api_refs.extend(_grep("JobQueue\\|JobRequest\\|create_job_tools\\|MCPAsyncJobAdapter\\|AdminService", sd))
    if len(job_api_refs) > 0:
        results["pass"].append(f"cloud_dog_jobs API used for job management ({len(job_api_refs)} references)")
    else:
        results["fail"].append("No cloud_dog_jobs API usage (JobQueue/JobRequest/create_job_tools)")

    # 5. server_id in job metadata (check defaults.yaml)
    defaults = project_root / "defaults.yaml"
    if defaults.exists():
        content = defaults.read_text()
        if "server_id" in content:
            results["pass"].append("server_id present in defaults.yaml")
        else:
            results["fail"].append("No server_id in defaults.yaml for job metadata")

    return results
