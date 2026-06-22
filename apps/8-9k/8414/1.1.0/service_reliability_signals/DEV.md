# Service Reliability Signals — Developer Guide

## Architecture Overview
This app derives reliability signals exclusively from log data.
No agents, metrics, or integrations are permitted.

## Macro Layers
1. Base Layer
   - svc_base_search
   - resolve_service

2. Signal Layer
   - svc_failure_detect
   - svc_availability
   - svc_instability
   - svc_sla_risk

3. Interpretation Layer
   - stability score
   - SLA risk levels
   - change impact

## Configuration Philosophy
- All configuration is optional
- Lookups override defaults
- Missing config must never break SPL

## Do-Not-Break Rules
- Do not introduce infrastructure metrics
- Do not depend on ITSI / ES / MLTK
- Do not hide logic inside dashboards
- Do not hardcode service schemas

## Future Extension Points
- Dependency inference
- Configurable scoring weights
- Vertical-specific reliability models
