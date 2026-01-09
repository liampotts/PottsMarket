import { useEffect, useState } from 'react'
import './App.css'

// Simple modal for trading
function TradeModal({ market, onClose, onTrade }) {
  const [outcomeId, setOutcomeId] = useState(market.outcomes[0]?.id || '')
  const [amount, setAmount] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleTrade = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      await onTrade(market.slug, outcomeId, amount)
      onClose()
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const selectedOutcome = market.outcomes.find(o => String(o.id) === String(outcomeId))

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="modal-header">
          <h3>Trade: {market.title}</h3>
          <button className="ghost sm" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={handleTrade} className="form">
          <label>
            Outcome
            <select value={outcomeId} onChange={e => setOutcomeId(e.target.value)}>
              {market.outcomes.map(o => (
                <option key={o.id} value={o.id}>{o.name} (${Number(o.price).toFixed(2)})</option>
              ))}
            </select>
          </label>

          <div className="price-display">
            Current Price: <strong>{selectedOutcome?.name} = {Number(selectedOutcome?.price || 0).toFixed(2)}</strong>
          </div>

          <label>
            Amount (USD)
            <input
              type="number"
              value={amount}
              onChange={e => setAmount(e.target.value)}
              placeholder="10.00"
              step="0.01"
              min="0.1"
              required
            />
          </label>

          {error && <div className="status error">{error}</div>}

          <div className="modal-actions">
            <button type="button" className="ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="primary" disabled={loading}>
              {loading ? 'Buying...' : `Buy ${selectedOutcome?.name}`}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

function App() {
  const apiBase = '/api'
  const [markets, setMarkets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTradeMarket, setActiveTradeMarket] = useState(null)

  const [form, setForm] = useState({
    title: '',
    slug: '',
    description: '',
    status: 'draft',
  })

  const handleTradeSubmit = async (slug, outcomeId, amount) => {
    const response = await fetch(`${apiBase}/markets/${slug}/trade/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        outcome_id: outcomeId,
        amount: amount,
        user_id: 1 // Demo user
      })
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || 'Trade failed')

    // Refresh markets to update prices
    fetchMarkets()
    return data
  }
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')

  const fetchMarkets = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${apiBase}/markets/`)
      if (!response.ok) {
        throw new Error('Failed to load markets.')
      }
      const data = await response.json()
      setMarkets(data)
    } catch (err) {
      setError(err.message || 'Something went wrong.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMarkets()
  }, [])

  const handleChange = (event) => {
    const { name, value } = event.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setCreating(true)
    setCreateError('')
    try {
      const response = await fetch(`${apiBase}/api/markets/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      const data = await response.json()
      if (!response.ok) {
        const message =
          data?.errors
            ? Object.values(data.errors).join(' ')
            : data?.error || 'Failed to create market.'
        throw new Error(message)
      }
      setMarkets((prev) => [data, ...prev])
      setForm({ title: '', slug: '', description: '', status: 'draft' })
    } catch (err) {
      setCreateError(err.message || 'Unable to create market.')
    } finally {
      setCreating(false)
    }
  }

  return (
    <div className="page">
      <header className="hero">
        <div className="hero__content">
          <div className="badge">Prediction markets</div>
          <h1>PottsMarket</h1>
          <p>
            Launch bold questions, trade conviction, and track the pulse of
            sentiment in real time.
          </p>
          <div className="hero__actions">
            <button className="primary">Explore markets</button>
            <button className="ghost">View leaderboard</button>
          </div>
        </div>
        <div className="hero__card">
          <div className="hero__card-header">
            <span>Now trading</span>
            <span className="pill">Open</span>
          </div>
          <h3>Will BTC close above $100k this year?</h3>
          <div className="hero__price">
            <div>
              <span>YES</span>
              <strong>0.62</strong>
            </div>
            <div>
              <span>NO</span>
              <strong>0.38</strong>
            </div>
          </div>
          <div className="hero__meta">Volume $2.4m · 12,482 traders</div>
        </div>
      </header>

      <main className="grid">
        <section className="panel">
          <div className="panel__header">
            <div>
              <h2>Markets</h2>
              <p>Live markets from the backend API.</p>
            </div>
            <button className="ghost" onClick={fetchMarkets}>
              Refresh
            </button>
          </div>
          {loading ? (
            <div className="status">Loading markets...</div>
          ) : error ? (
            <div className="status error">{error}</div>
          ) : markets.length === 0 ? (
            <div className="status empty">
              No markets yet. Create one to get started.
            </div>
          ) : (
            <div className="market-list">
              {markets.map((market) => (
                <article className="market-card" key={market.id}>
                  <div className="market-card__top">
                    <h3>{market.title}</h3>
                    <div className="badges">
                      <span className={`pill pill--${market.status}`}>{market.status}</span>
                    </div>
                  </div>
                  <p>{market.description || 'No description provided.'}</p>

                  {market.outcomes && market.outcomes.length > 0 && (
                    <div className="outcomes-grid">
                      {market.outcomes.map(outcome => (
                        <div key={outcome.id} className="outcome-row">
                          <span className="outcome-name">{outcome.name}</span>
                          <span className="outcome-price">{Number(outcome.price || 0).toFixed(2)}</span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="market-card__actions">
                    <button className="secondary sm" onClick={() => setActiveTradeMarket(market)}>Trade</button>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

        {activeTradeMarket && (
          <TradeModal
            market={activeTradeMarket}
            onClose={() => setActiveTradeMarket(null)}
            onTrade={handleTradeSubmit}
          />
        )}

        <section className="panel panel--accent">
          <div className="panel__header">
            <div>
              <h2>Create a market</h2>
              <p>Post to `api/markets/` to spin up a new idea.</p>
            </div>
          </div>
          <form className="form" onSubmit={handleSubmit}>
            <label>
              Title
              <input
                name="title"
                value={form.title}
                onChange={handleChange}
                placeholder="Will the Lakers win the finals?"
              />
            </label>
            <label>
              Slug
              <input
                name="slug"
                value={form.slug}
                onChange={handleChange}
                placeholder="lakers-finals-2025"
              />
            </label>
            <label>
              Description
              <textarea
                name="description"
                value={form.description}
                onChange={handleChange}
                placeholder="Short context to help traders decide."
              />
            </label>
            <label>
              Status
              <select name="status" value={form.status} onChange={handleChange}>
                <option value="draft">Draft</option>
                <option value="open">Open</option>
                <option value="closed">Closed</option>
                <option value="resolved">Resolved</option>
              </select>
            </label>
            {createError ? (
              <div className="status error">{createError}</div>
            ) : null}
            <button className="primary" type="submit" disabled={creating}>
              {creating ? 'Creating...' : 'Create market'}
            </button>
          </form>
        </section>
      </main>

      <footer className="footer">
        <span>Built for fast signals and sharper predictions.</span>
      </footer>
    </div>
  )
}

export default App
