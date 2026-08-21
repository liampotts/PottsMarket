import { useCallback, useEffect, useMemo, useState } from 'react'
import './ClaimLab.css'


const toDatetimeLocal = (value) => {
  if (!value) return ''
  const date = new Date(value)
  const offset = date.getTimezoneOffset()
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 16)
}

const defaultClaim = () => {
  const now = Date.now()
  return {
    statement: '',
    excerpt: '',
    rationale: '',
    resolution_criteria: '',
    resolution_source_url: '',
    closes_at: toDatetimeLocal(new Date(now + 14 * 86_400_000)),
    resolves_at: toDatetimeLocal(new Date(now + 90 * 86_400_000)),
    confidence: 1,
    status: 'suggested',
  }
}

function ClaimEditor({ claim, onSave, onPublish, busy }) {
  const [draft, setDraft] = useState({
    ...claim,
    closes_at: toDatetimeLocal(claim.closes_at),
    resolves_at: toDatetimeLocal(claim.resolves_at),
  })

  useEffect(() => {
    setDraft({
      ...claim,
      closes_at: toDatetimeLocal(claim.closes_at),
      resolves_at: toDatetimeLocal(claim.resolves_at),
    })
  }, [claim])

  const payload = (status = draft.status) => ({
    ...draft,
    status,
    closes_at: new Date(draft.closes_at).toISOString(),
    resolves_at: new Date(draft.resolves_at).toISOString(),
    confidence: Number(draft.confidence),
  })

  const setField = (field, value) => setDraft((current) => ({ ...current, [field]: value }))

  return (
    <article className="claim-editor">
      <div className="claim-editor__header">
        <div>
          <span className={`lab-status lab-status--${claim.status}`}>{claim.status}</span>
          <span className="claim-method">{claim.extraction_method}</span>
        </div>
        <span className="claim-confidence">{Math.round(Number(claim.confidence) * 100)}% extraction confidence</span>
      </div>

      <label>
        Binary market question
        <textarea
          value={draft.statement}
          onChange={(event) => setField('statement', event.target.value)}
          rows="2"
        />
      </label>

      <div className="claim-editor__source">
        <label>
          Transcript excerpt
          <textarea
            value={draft.excerpt}
            onChange={(event) => setField('excerpt', event.target.value)}
            rows="3"
          />
        </label>
        {claim.excerpt_start_seconds !== null && claim.excerpt_start_seconds !== undefined && (
          <span>Starts near {Math.floor(claim.excerpt_start_seconds / 60)}:{String(claim.excerpt_start_seconds % 60).padStart(2, '0')}</span>
        )}
      </div>

      <label>
        Why this is forecastable
        <textarea
          value={draft.rationale}
          onChange={(event) => setField('rationale', event.target.value)}
          rows="2"
        />
      </label>

      <label>
        Objective resolution criteria
        <textarea
          value={draft.resolution_criteria}
          onChange={(event) => setField('resolution_criteria', event.target.value)}
          rows="4"
        />
      </label>

      <label>
        Public resolution source
        <input
          type="url"
          value={draft.resolution_source_url}
          onChange={(event) => setField('resolution_source_url', event.target.value)}
        />
      </label>

      <div className="claim-editor__dates">
        <label>
          Trading closes
          <input
            type="datetime-local"
            value={draft.closes_at}
            onChange={(event) => setField('closes_at', event.target.value)}
          />
        </label>
        <label>
          Resolves by
          <input
            type="datetime-local"
            value={draft.resolves_at}
            onChange={(event) => setField('resolves_at', event.target.value)}
          />
        </label>
        <label>
          Extraction confidence
          <input
            type="number"
            min="0"
            max="1"
            step="0.05"
            value={draft.confidence}
            onChange={(event) => setField('confidence', event.target.value)}
          />
        </label>
      </div>

      {claim.market ? (
        <div className="claim-published">Published as <strong>{claim.market.slug}</strong></div>
      ) : (
        <div className="claim-editor__actions">
          <button className="ghost sm" disabled={busy} onClick={() => onSave(claim.id, payload('suggested'))}>Save draft</button>
          <button className="ghost sm" disabled={busy} onClick={() => onSave(claim.id, payload('rejected'))}>Reject</button>
          <button className="secondary sm" disabled={busy} onClick={() => onSave(claim.id, payload('approved'))}>Approve</button>
          {claim.status === 'approved' && (
            <button className="primary sm" disabled={busy} onClick={() => onPublish(claim.id)}>Publish market</button>
          )}
        </div>
      )}
    </article>
  )
}

function ManualClaimForm({ source, onCreate, busy }) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState(defaultClaim)
  const setField = (field, value) => setDraft((current) => ({ ...current, [field]: value }))

  const submit = async (event) => {
    event.preventDefault()
    const created = await onCreate(source.id, {
      ...draft,
      closes_at: new Date(draft.closes_at).toISOString(),
      resolves_at: new Date(draft.resolves_at).toISOString(),
      confidence: Number(draft.confidence),
    })
    if (created) {
      setDraft(defaultClaim())
      setOpen(false)
    }
  }

  if (!open) {
    return <button className="ghost sm" onClick={() => setOpen(true)}>Add a claim manually</button>
  }

  return (
    <form className="manual-claim" onSubmit={submit}>
      <h4>Create an editorial claim</h4>
      <label>Binary market question<input required value={draft.statement} onChange={(event) => setField('statement', event.target.value)} /></label>
      <label>Transcript excerpt<textarea rows="2" value={draft.excerpt} onChange={(event) => setField('excerpt', event.target.value)} /></label>
      <label>Why it is forecastable<textarea rows="2" value={draft.rationale} onChange={(event) => setField('rationale', event.target.value)} /></label>
      <label>Resolution criteria<textarea required rows="3" value={draft.resolution_criteria} onChange={(event) => setField('resolution_criteria', event.target.value)} /></label>
      <label>Resolution source<input required type="url" value={draft.resolution_source_url} onChange={(event) => setField('resolution_source_url', event.target.value)} /></label>
      <div className="claim-editor__dates">
        <label>Trading closes<input required type="datetime-local" value={draft.closes_at} onChange={(event) => setField('closes_at', event.target.value)} /></label>
        <label>Resolves by<input required type="datetime-local" value={draft.resolves_at} onChange={(event) => setField('resolves_at', event.target.value)} /></label>
      </div>
      <div className="claim-editor__actions">
        <button type="button" className="ghost sm" onClick={() => setOpen(false)}>Cancel</button>
        <button className="primary sm" disabled={busy}>Create claim</button>
      </div>
    </form>
  )
}

export default function ClaimLab({ apiBase, config, onMarketPublished }) {
  const [sources, setSources] = useState([])
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const hasActiveJobs = useMemo(
    () => sources.some((source) => ['queued', 'processing'].includes(source.status)),
    [sources],
  )

  const loadSources = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    try {
      const response = await fetch(`${apiBase}/claim-lab/sources/`, { credentials: 'include' })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Could not load Claim Lab sources.')
      setSources(data.sources)
      setError('')
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      if (!silent) setLoading(false)
    }
  }, [apiBase])

  useEffect(() => {
    loadSources()
  }, [loadSources])

  useEffect(() => {
    if (!hasActiveJobs) return undefined
    const timer = window.setInterval(() => loadSources(true), 3000)
    return () => window.clearInterval(timer)
  }, [hasActiveJobs, loadSources])

  const submitSource = async (event) => {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const response = await fetch(`${apiBase}/claim-lab/sources/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
        credentials: 'include',
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Could not queue the source.')
      setUrl('')
      await loadSources(true)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  const retrySource = async (sourceId) => {
    setBusy(true)
    try {
      const response = await fetch(`${apiBase}/claim-lab/sources/${sourceId}/retry/`, {
        method: 'POST',
        credentials: 'include',
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Could not retry ingestion.')
      await loadSources(true)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  const saveClaim = async (claimId, payload) => {
    setBusy(true)
    setError('')
    try {
      const response = await fetch(`${apiBase}/claim-lab/claims/${claimId}/`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include',
      })
      const data = await response.json()
      if (!response.ok) {
        const details = data.errors ? Object.values(data.errors).join(' ') : data.error
        throw new Error(details || 'Could not save the claim.')
      }
      await loadSources(true)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  const createClaim = async (sourceId, payload) => {
    setBusy(true)
    setError('')
    try {
      const response = await fetch(`${apiBase}/claim-lab/sources/${sourceId}/claims/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        credentials: 'include',
      })
      const data = await response.json()
      if (!response.ok) {
        const details = data.errors ? Object.values(data.errors).join(' ') : data.error
        throw new Error(details || 'Could not create the claim.')
      }
      await loadSources(true)
      return true
    } catch (requestError) {
      setError(requestError.message)
      return false
    } finally {
      setBusy(false)
    }
  }

  const publishClaim = async (claimId) => {
    setBusy(true)
    setError('')
    try {
      const response = await fetch(`${apiBase}/claim-lab/claims/${claimId}/publish/`, {
        method: 'POST',
        credentials: 'include',
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Could not publish the market.')
      await loadSources(true)
      onMarketPublished(data.market)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="claim-lab">
      <div className="claim-lab__hero">
        <div>
          <span className="badge">Invitation-only alpha</span>
          <h1>Claim Lab</h1>
          <p>Turn public media into falsifiable, source-backed prediction markets with a human review gate.</p>
        </div>
        <div className="claim-lab__model">
          <span>Extraction engine</span>
          <strong>{config.model}</strong>
          <small>{config.llm_configured ? 'Qwen endpoint connected' : 'Editorial fallback active'}</small>
        </div>
      </div>

      <form className="source-intake" onSubmit={submitSource}>
        <label htmlFor="source-url">Public YouTube URL</label>
        <div>
          <input
            id="source-url"
            type="url"
            required
            placeholder="https://www.youtube.com/watch?v=..."
            value={url}
            onChange={(event) => setUrl(event.target.value)}
          />
          <button className="primary" disabled={busy}>Extract claims</button>
        </div>
        <p>Transcripts are stored with source attribution. Nothing publishes without explicit approval.</p>
      </form>

      {error && <div className="status error claim-lab__error">{error}</div>}

      {loading ? (
        <div className="status">Loading the editorial queue...</div>
      ) : sources.length === 0 ? (
        <div className="claim-lab__empty">
          <h3>The queue is empty</h3>
          <p>Submit a video containing a concrete future-facing claim to create the first source-backed market.</p>
        </div>
      ) : (
        <div className="source-list">
          {sources.map((source) => (
            <section className="source-card" key={source.id}>
              <div className="source-card__header">
                <div>
                  <div className="source-card__eyebrow">
                    <span className={`lab-status lab-status--${source.status}`}>{source.status.replace('_', ' ')}</span>
                    <span>{source.author || 'Unknown channel'}</span>
                  </div>
                  <h2>{source.title || 'Reading transcript…'}</h2>
                  <a href={source.url} target="_blank" rel="noreferrer">Open original source ↗</a>
                </div>
                <span className="source-card__count">{source.claim_count} claims</span>
              </div>

              {source.error && (
                <div className="status error">
                  {source.error}
                  <button className="ghost sm" disabled={busy} onClick={() => retrySource(source.id)}>Retry</button>
                </div>
              )}

              {['queued', 'processing'].includes(source.status) && (
                <div className="processing-line"><span />Extracting the transcript and candidate claims…</div>
              )}

              {source.metadata?.llm_warning && (
                <div className="status">The model endpoint was unavailable, so editorial fallback extraction was used.</div>
              )}

              <div className="source-card__claims">
                {source.claims.map((claim) => (
                  <ClaimEditor
                    key={claim.id}
                    claim={claim}
                    onSave={saveClaim}
                    onPublish={publishClaim}
                    busy={busy}
                  />
                ))}
              </div>

              {['ready', 'needs_review'].includes(source.status) && (
                <ManualClaimForm source={source} onCreate={createClaim} busy={busy} />
              )}
            </section>
          ))}
        </div>
      )}
    </section>
  )
}
