# Documentation Index

This directory is organized by domain to keep ownership and navigation clear. **Start here** to find the right guide for your task.

## Domain Guides

### 🏗️ Architecture (`architecture/`)

System topology, infrastructure design, deployment patterns, and technical project structure.

- **Use when**: Setting up infrastructure, understanding system topology, reviewing component interactions
- **Key docs**: `ARCHITECTURE.md` (component overview), `PROJECT_STRUCTURE.md` (module organization), `INFRA_BASELINE_KUBERNETES.md` (Kubernetes baseline), `CONSORTIUM_EXECUTION_MODEL.md` (deployment model)

### 🛠️ Operations (`operations/`)

Runtime guides, migration setup, data processing, and operational runbooks.

- **Use when**: Operating the system, importing data, managing databases, running demos
- **Key docs**: `DEMO_GUIDE.md` (demo datasets & scenarios), `DB_MIGRATION_SETUP.md` (database migration), `LARGE_DATASET_GUIDE.md` (performance tuning), `DEMO_GUIDE.md` (interactive walkthrough)

### 🔒 Security (`security/`)

Security scope, threat model, compliance evidence, and incident response procedures.

- **Use when**: Auditing security posture, conducting risk assessment, responding to incidents
- **Key docs**: `SECURITY.md` (scope & limitations), `SECURITY_EVIDENCE_PACK.md` (compliance artifacts), `INCIDENT_RESPONSE_RUNBOOK.md` (incident procedures), `SUPPLY_CHAIN_ASSURANCE.md` (supply chain controls)

### 📦 Product (`product/`)

API specification, feature inventory, interoperability profiles, and capability statements.

- **Use when**: Building integrations, understanding API behavior, discovering features
- **Key docs**: `API_DOCUMENTATION.md` (REST + WebSocket reference), `FEATURES_IMPLEMENTED.md` (feature checklist), `INTEROPERABILITY_PROFILE.md` (standards alignment), `NATO_PARTNER_OUTREACH_TARGET_LIST.md` (market assessment)

### 📋 Governance (`governance/`)

Backlog, audit matrices, issue packs, and implementation tracking.

- **Use when**: Planning feature work, tracking defects, auditing coverage
- **Key docs**: `BUSINESS_LOGIC_IMPLEMENTATION_BACKLOG.md` (backlog), `AUDIT_COVERAGE_MATRIX.md` (test coverage map), `GITHUB_ISSUES_*.md` (packaged issue templates)

### 💰 Funding (`funding/`)

Funding routes, financial models, pilot evidence templates, and business case documentation.

- **Use when**: Pursuing funding, building business cases, documenting evidence
- **Key docs**: `NATO_FUNDABILITY_GAP_ANALYSIS.md` (gap analysis), `NATO_FUNDABILITY_8_WEEK_EXECUTION_BOARD.md` (execution plan), `FUNDING_ROUTE_MATRIX.md` (route assessment), `FUNDING_PILOT_EVIDENCE_TEMPLATE.md` (evidence capture)

---

## Quick Navigation

| Need                          | Domain       | Document                                   |
| ----------------------------- | ------------ | ------------------------------------------ |
| Understand what AegisAIS does | Product      | `FEATURES_IMPLEMENTED.md`                  |
| Deploy to Kubernetes          | Architecture | `INFRA_BASELINE_KUBERNETES.md`             |
| Import a large AIS file       | Operations   | `LARGE_DATASET_GUIDE.md`                   |
| Review security controls      | Security     | `SECURITY.md`                              |
| Plan feature development      | Governance   | `BUSINESS_LOGIC_IMPLEMENTATION_BACKLOG.md` |
| Build API integrations        | Product      | `API_DOCUMENTATION.md`                     |
| Set up database migrations    | Operations   | `DB_MIGRATION_SETUP.md`                    |
| Assess funding opportunities  | Funding      | `NATO_FUNDABILITY_GAP_ANALYSIS.md`         |

---

## Canonical Paths

Use the domain folders as the only authoritative documentation locations.
