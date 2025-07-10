#!/usr/bin/env python3
"""
Validate that GitHub workflows using github/codeql-action/analyze
have correct permissions configuration.

This script ensures that:
1. Jobs using github/codeql-action/analyze have security-events: write at job level
2. security-events: write is NOT defined at the root level for such workflows
"""

import glob
import os
import sys
import yaml
from pathlib import Path

def validate_codeql_permissions():
  """Validate CodeQL workflow permissions"""
  error_count = 0
  workflows_dir = Path('.github/workflows')

  if not workflows_dir.exists():
    print("ERROR: .github/workflows directory not found", file=sys.stderr)
    return 1

  # Find all workflow files
  workflow_files = list(workflows_dir.glob('*.yml')) + list(workflows_dir.glob('*.yaml'))

  for workflow_file in workflow_files:
    try:
      with open(workflow_file, 'r') as f:
        workflow = yaml.safe_load(f)

      if not workflow or 'jobs' not in workflow:
        continue

      # Check if any job uses github/codeql-action/analyze
      codeql_jobs = []
      for job_name, job_config in workflow['jobs'].items():
        if 'steps' in job_config:
          for step in job_config['steps']:
            if isinstance(step, dict) and 'uses' in step:
              if 'github/codeql-action/analyze' in step['uses']:
                codeql_jobs.append(job_name)
                break

      if not codeql_jobs:
        continue  # No CodeQL analyze jobs in this workflow

      print(f"Found CodeQL analyze workflow: {workflow_file}")
      print(f"  Jobs using github/codeql-action/analyze: {', '.join(codeql_jobs)}")

      # Check root-level permissions
      root_permissions = workflow.get('permissions', {})
      if isinstance(root_permissions, dict) and 'security-events' in root_permissions:
        if root_permissions['security-events'] == 'write':
          print(f"ERROR: {workflow_file} has security-events: write at root level", file=sys.stderr)
          print("  Root-level security-events: write should be moved to job level", file=sys.stderr)
          error_count += 1

      # Check job-level permissions for CodeQL jobs
      for job_name in codeql_jobs:
        job_config = workflow['jobs'][job_name]
        job_permissions = job_config.get('permissions', {})

        if not isinstance(job_permissions, dict):
          print(f"ERROR: {workflow_file} job '{job_name}' has invalid permissions format", file=sys.stderr)
          error_count += 1
          continue

        if 'security-events' not in job_permissions:
          print(f"ERROR: {workflow_file} job '{job_name}' missing security-events permission", file=sys.stderr)
          error_count += 1
        elif job_permissions['security-events'] != 'write':
          print(f"ERROR: {workflow_file} job '{job_name}' has security-events: {job_permissions['security-events']}, should be 'write'", file=sys.stderr)
          error_count += 1
        else:
          print(f"  OK Job '{job_name}' has correct security-events: write permission")

    except yaml.YAMLError as e:
      print(f"ERROR: Failed to parse {workflow_file}: {e}", file=sys.stderr)
      error_count += 1
    except Exception as e:
      print(f"ERROR: Failed to process {workflow_file}: {e}", file=sys.stderr)
      error_count += 1

  if error_count == 0:
    print("OK All CodeQL workflows have correct permissions configuration")
  else:
    print(f"ERROR Found {error_count} permission configuration errors", file=sys.stderr)

  return error_count

if __name__ == '__main__':
  sys.exit(validate_codeql_permissions())
