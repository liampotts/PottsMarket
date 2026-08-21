# Claim Lab implementation plan

## Product objective

Turn public media into auditable play-money prediction markets. A source-backed
market must preserve the original source, transcript excerpt, objective
resolution contract, review decision, immutable trades, and initial model prior.

The first release is invitation-only. It is an editorial system, not an
autonomous publisher: a human must approve every candidate before it becomes an
open market.

## User journey

1. An invited editor submits a public YouTube URL.
2. A background worker retrieves metadata and an available English transcript.
   If YouTube blocks the hosting region, the editor can paste the public
   transcript and send it through the same worker and audit trail.
3. An OpenAI-compatible Qwen endpoint extracts up to five falsifiable claims.
4. When no endpoint is configured, a conservative heuristic suggests only clear
   future-facing language; editors can always create a claim manually.
5. The editor rewrites the question, transcript excerpt, close and resolution
   dates, resolution criteria, and resolution source.
6. Approval unlocks publishing. Publishing creates a funded binary CPMM market,
   provenance evidence, and a neutral model forecast snapshot.
7. The public market card displays its source and resolution contract.

## Architecture

```text
React Claim Lab
      |
      v
Django review API -----> PostgreSQL audit trail
      |
      v
Redis broker -----> Celery worker -----> YouTube transcript + Qwen/vLLM
                                           |
                                           v
                                  Source / Document / Claim
```

PostgreSQL remains authoritative. Redis is disposable queue infrastructure.
Kafka and Qdrant are deferred until continuous multi-source ingestion and
evidence retrieval justify their operational cost.

## Data contracts

- `Source`: canonical URL, provider metadata, owner, processing state and error.
- `Document`: normalized transcript, timestamped segments and content hash.
- `Claim`: question, cited excerpt, objective contract, deadlines, review state
  and published market.
- `Evidence`: timestamped, hashed public material attached to a claim.
- `Trade`: immutable execution record alongside the current aggregate position.
- `ForecastSnapshot`: human or agent probability at a point in time.
- `ResolutionProposal`: evidence-backed proposed outcome pending review.
- `ForecasterScore`: calibration rollup for future Brier/log-score leaderboards.

## Access and safety

- `CLAIM_LAB_ENABLED` is the global feature flag.
- Django staff, superusers, and members of `CLAIM_LAB_GROUP` can enter.
- Published claims are immutable through the Claim Lab API.
- The product remains play-money; no deposits or withdrawals are introduced.
- The model never publishes or resolves a market. It proposes structured work
  for a human editor.

## Rollout gates

1. Backend tests cover access, ingestion persistence, transcript recovery,
   manual claims, approval, publication, provenance and immutable trade creation.
2. Frontend lint/build and browser walkthroughs cover the complete journey and
   the datacenter-caption failure state.
3. Railway runs separate web, PostgreSQL, Redis and Celery worker services.
4. Vercel and Railway deploy the same merged commit successfully.
5. Production health, feature access and a temporary queue smoke test pass; the
   smoke record is removed after verification.

## Production operating notes

- Railway's worker is connected to the private Redis broker and registers
  `markets.tasks.process_source` at startup.
- Automated YouTube transcripts remain the preferred route. Hosting-provider IP
  blocks are treated as an expected recoverable state, not a silent failure.
- A supplied transcript is capped at 200,000 characters, hidden from source API
  serialization while queued, normalized into reviewable segments, and replaced
  by its content hash and provider metadata after processing.
- Until a Qwen/vLLM endpoint is configured, the UI says “Editorial fallback
  active” and uses conservative heuristics plus manual editorial claims.

## Alpha measurements

- Median source-to-draft latency under 60 seconds.
- At least 70% of model candidates accepted without a major rewrite.
- Every published market has a public resolution source and cited excerpt.
- Zero autonomous publications or resolutions.
- First cohort: 30 invited forecasters and 50 markets from 20 sources.

## Next expansion

After the editorial loop has real usage, add article/RSS adapters, Qdrant-backed
evidence discovery, scheduled resolution proposals, Brier-score dashboards and
creator/topic calibration pages. Kafka is reserved for the point where event
volume or replay requirements exceed Redis/Celery.
