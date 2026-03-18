# System Overview

## What the System Is

AegisAIS is an AIS data integrity and anomaly detection tool for maritime data analysis. It ingests AIS position reports, maintains vessel track history, and detects physically impossible or internally inconsistent movement patterns.

The platform is positioned as:

- a research and operations-focused AIS analysis tool
- an analyst support system for reviewing suspicious tracks and alerts
- a component within a broader maritime or OSINT stack

It is explicitly not described as a complete maritime security platform.

## Problem It Solves

AegisAIS addresses a narrow but operationally important problem: identifying questionable AIS data before analysts or downstream systems rely on it.

It focuses on:

- impossible or inconsistent AIS tracks
- suspicious vessel behavior surfaced through rule-based alerts
- efficient analyst review of anomalies through a UI and API

## Product Model

The current product model is a combined application layer and analyst workflow tool:

- backend API for ingestion, replay, detection, alert management, and export
- web frontend for review, filtering, visualization, and vessel investigation
- research platform for testing and evolving anomaly-detection rules

Operationally, the system is intended to sit behind stronger platform controls and be embedded into a larger environment rather than operate as a standalone security product.

## User Personas

The source material supports three primary user groups:

| Persona | Primary Need | Current Fit |
| --- | --- | --- |
| Maritime analysts | Review questionable AIS tracks and investigate alerts | Strong |
| Research and prototyping teams | Experiment with rules, thresholds, and workflows | Strong |
| Operations teams integrating AIS integrity checks into a wider stack | Use AegisAIS as a subsystem rather than a full platform | Partial |

## Core Workflows

## 1. AIS Data Ingestion and Replay

- AIS data is provided through file upload or direct file-path replay.
- Supported formats include CSV, DAT, and compressed variants.
- Large files can be processed in streaming mode.
- Replay can be run at configurable speedup values.

## 2. Detection and Alert Generation

- The system evaluates AIS inputs against rule-based detection logic.
- Alerts are generated for physically impossible or suspicious patterns.
- Alerts carry severity scoring and supporting evidence.
- Cooldown logic is used to reduce duplicate alert generation.

## 3. Analyst Review

- Analysts review alerts through the web UI or API.
- Alerts can be filtered by type, severity, status, and time range.
- Analysts can annotate and update alert status.
- Vessel-level investigation is supported through track history and vessel details views.

## 4. Visualization and Export

- Vessel positions, tracks, and alerts can be visualized on a map.
- Filtered alert sets can be exported as CSV or JSON.
- Historical track views support context during investigation.

## Business Value Model

The business value described in the source material is concentrated in analyst efficiency and data trust:

- reduce manual effort by surfacing questionable AIS records early
- improve confidence in downstream maritime analysis
- provide an operational UI for triage and annotation
- accelerate research and prototyping of new maritime anomaly rules

## Maturity Assessment

| Area | Assessment |
| --- | --- |
| Core detection capability | Functional |
| Analyst workflow | Functional with meaningful UI support |
| Large dataset handling | Partially prepared, PostgreSQL and streaming recommended |
| Operational hardening | Incomplete |
| Security posture | Incomplete for production deployment |
| Platform maturity | Research and operations tool, not production-complete platform |

The materials consistently position AegisAIS as a useful operational component and prototype platform, but not as a production-complete, defense-in-depth system.

## Strengths vs Risks

| Strengths | Risks |
| --- | --- |
| Clear problem definition around AIS integrity and anomaly detection | Authentication exists in code, but production hardening is incomplete |
| Modular monolith architecture keeps feature logic centralized | Infrastructure hardening is explicitly out of scope |
| Functional analyst UI with alert review, track history, export, and map workflows | Integration testing and performance testing are missing |
| Support for streaming and PostgreSQL for larger datasets | SQLite remains the default for smaller setups despite clear scale limits |
| Detection, annotation, and replay workflows are already connected | Backup, monitoring, cleanup scheduling, and retention remain incomplete |
| Several critical reliability fixes are documented as completed | Real-time AIS feed support is not implemented |

## Current Position

AegisAIS is best understood as an operationally useful AIS anomaly-detection component with a credible analyst workflow and meaningful technical progress, but with material gaps in security, operational resilience, testing, and scale readiness that prevent it from being treated as a fully production-hardened platform.
