# Security policy

## Supported versions

| Version | Supported |
| --- | --- |
| 0.6.1 | Yes |
| 0.5.1 | Yes |
| 0.5.0 and earlier | No — affected; upgrade to 0.5.1 or newer |

## Report a vulnerability

Please report suspected vulnerabilities privately through [GitHub Security Advisories](https://github.com/Doctacon/buoy/security/advisories/new). Do not open a public issue containing exploit details, credentials, private source data, or affected-user information.

Include the affected version, reproduction conditions, observed impact, and any
suggested mitigation. Share the smallest safe reproduction you can; do not
include third-party credentials or private repository content. Maintainers will
acknowledge the report through the private advisory and coordinate disclosure
there.

## Scope reminders

Buoy reads public sources, local documents, local embedding models, a local DuckDB ledger, and—only on explicitly live commands—a Turbopuffer API key. Reports involving credential exposure, source-boundary bypass, unsafe artifact/state mutation, or unauthorized remote operations are especially useful.
