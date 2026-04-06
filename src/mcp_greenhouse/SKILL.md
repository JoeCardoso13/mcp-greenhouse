---
name: mcp-greenhouse-service
description: Guides tool selection for polling Greenhouse job boards, normalizing job data, and checking job metadata coverage.
---

## Tools

| Tool | Use when... |
|------|-------------|
| `get_job_board` | You need the company name or board-level intro content for a board token |
| `list_company_jobs` | You want the current set of public jobs for a board |
| `get_job_details` | You already have a Greenhouse `job_id` and need the full posting |
| `list_departments` | You need Greenhouse's department grouping for the board |
| `list_offices` | You need office-based grouping for the board |
| `normalize_job_data` | You want a stable downstream-friendly job schema for storage or diffing |
| `inspect_job_attributes` | You want to know whether salary, experience level, or workplace-type data is present |
| `list_new_or_updated_jobs` | You are polling a board and need to find newly posted or changed jobs since the last snapshot |

## Context Reuse

- Reuse the same `board_token` across all calls in a workflow.
- Take `job_id` values from `list_company_jobs`, `list_departments`, or `list_offices` when calling `get_job_details` or `inspect_job_attributes`.
- Use `current_snapshot` from `list_new_or_updated_jobs` as the next run's `previous_snapshot`.
- Use `normalize_job_data` output when you need stable fields like title, location, URL, updated timestamp, departments, and offices.

## Workflows

### 1. Poll a Target Company for New Roles
1. Call `list_new_or_updated_jobs` with the target `board_token` and the last stored `previous_snapshot`.
2. Review `new_jobs` and `updated_jobs`.
3. Persist the returned `current_snapshot` for the next poll cycle.

### 2. Normalize Jobs for Storage
1. Call `normalize_job_data` with `include_content=true`.
2. Store the normalized records keyed by `job_id`.
3. Use the normalized `metadata`, `departments`, and `offices` fields for downstream enrichment.

### 3. Check Metadata Coverage for a Role
1. Call `get_job_details` if you need the full posting body.
2. Call `inspect_job_attributes` for the same `job_id`.
3. Use the report to determine whether salary, experience-level, or workplace-type signals are present or missing.
