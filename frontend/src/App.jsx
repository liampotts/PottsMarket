import { useEffect, useMemo, useState } from 'react'
import './App.css'

function App() {
  const apiBase = useMemo(() => {
    return import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000'
  }, [])
  const [markets, setMarkets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    title: '',
    slug: '',
    description: '',
    status: 'draft',
  })
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState('')

  const fetchMarkets = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${apiBase}/api/markets/`)
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
                    <span className={`pill pill--${market.status}`}>
                      {market.status}
                    </span>
                  </div>
                  <p>{market.description || 'No description provided.'}</p>
                  <div className="market-card__meta">
                    <span>{market.slug}</span>
                    <span>
                      {new Date(market.created_at).toLocaleDateString()}
                    </span>
                  </div>
                </article>
              ))}
            </div>
          )}
        </section>

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
