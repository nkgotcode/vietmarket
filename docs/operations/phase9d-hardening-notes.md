# Phase 9D Hardening Notes

This repository now includes:
- scheduled Nomad evaluation cycle job: `vietmarket-supervisor-evaluation-cycle`
- delivery-events API/page surfaces
- operator approval write path in `POST /api/brain/approvals`

Verification:
- `node --test tests/phase9d_hardening_smoke.test.mjs`
- `nomad job plan deploy/nomad/jobs/vietmarket-supervisor-daily-cycle.nomad.hcl`
- `nomad job plan deploy/nomad/jobs/vietmarket-supervisor-evaluation-cycle.nomad.hcl`
