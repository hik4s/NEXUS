# Intelligence architecture

NEXUS Intelligence is designed as a layered system:

1. Rules engine — deterministic, auditable business rules.
2. Analytics — SQL/Python calculations and KPI pipelines.
3. ML — forecasts and anomaly detection where data quality supports it.
4. LLM — natural language interpretation and controlled tool calling.
5. Action engine — user-approved operational actions with audit trails.

The LLM is not the financial source of truth. Verified NEXUS data and deterministic calculations are.
