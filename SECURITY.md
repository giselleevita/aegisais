## Security Policy

AegisAIS is a research and operations-focused tool for analyzing **AIS (Automatic Identification System)** maritime data for integrity issues and anomalous vessel behavior. It is **not** a complete maritime security platform and should be deployed as part of a broader defense-in-depth architecture.

### Scope

In scope:

- Detecting **physically impossible** or **internally inconsistent** AIS tracks (e.g. teleportation, impossible speeds/accelerations, heading/COG inconsistencies).
- Highlighting **suspicious vessel behavior** via rule-based alerts and severity scoring.
- Providing an operational UI and API for **analysts** to review, filter, and annotate alerts.

Out of scope:

- Hardening of surrounding infrastructure (network perimeter, authN/Z, OS hardening, TLS termination).
- Protection against actively malicious AIS transmitters beyond the modeled rules.
- Guarantees of completeness for all possible AIS manipulation or spoofing techniques.

### Intended usage

- As a **data integrity and anomaly detection component** in a larger maritime orOSINT stack.
- As an **analyst support tool** for spotting questionable AIS tracks and focusing manual review.
- As a **research and prototyping platform** for new detection rules and features.

If you adapt AegisAIS for production deployment:

- Perform a **system-level threat model** (data sources, ingestion pipeline, storage, users).
- Put AegisAIS behind appropriate **authentication, authorization, and network controls**.
- Monitor and log access to sensitive endpoints and AIS data exports.
- Validate detection rules and thresholds against **your own datasets and operational requirements**.

### Reporting vulnerabilities

If you believe you have found a vulnerability that:

- Allows unauthorized access to AIS data or alert information,
- Breaks integrity guarantees (e.g. silently dropping tracks/alerts),
- Or exposes sensitive deployment details via the API,

please open a **private issue** or contact the maintainer on GitHub instead of disclosing it publicly first. Include:

- A minimal reproducible example (input data, configuration, and observed behavior).
- Backend version (see `pyproject.toml`), Python version, database type, and deployment mode (local/Docker).

Given the research and prototyping nature of the project, response times may vary, but security-impacting reports will be prioritized where possible.

