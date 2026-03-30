# Polymarket Automated Trading System

An agent-based portfolio management framework for Polymarket prediction markets.

## Architecture

```
Agent_Orchestrator  (Portfolio Manager / Lead)
        |
        ├──> Agent_PolyScout   (Market Analysis)
        |
        ├──> Agent_Risk_Engine  (Risk Validation)
        |
        └──> Executioner        (Trade Execution)
```

## Rules

1. Every trade proposed by `Agent_PolyScout` **must** pass `Agent_Risk_Engine` validation before execution.
2. Maintain portfolio delta-neutrality where possible.
3. All final trade decisions are emitted as strict JSON consumed by the Executioner.

## Modules

| File | Role |
|------|------|
| `orchestrator.py` | `Agent_Orchestrator` — coordinates all agents, maintains portfolio log |
| `polyscout.py` | `Agent_PolyScout` — fetches and scores market opportunities |
| `risk_engine.py` | `Agent_Risk_Engine` — validates trades against risk limits |
| `executioner.py` | Parses orchestrator JSON and submits orders |
| `portfolio.py` | Portfolio state model and delta tracker |
| `config.py` | Shared configuration and constants |

## Trade Decision Format

```json
{
  "decision_id": "uuid4",
  "timestamp": "ISO-8601",
  "market_id": "string",
  "outcome": "YES | NO",
  "size_usdc": 0.0,
  "limit_price": 0.0,
  "risk_approved": true,
  "orchestrator_notes": "string"
}
```

## Getting Started

```bash
pip install -r requirements.txt
python orchestrator.py
```
