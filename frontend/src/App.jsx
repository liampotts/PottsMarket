import { useEffect, useState } from 'react'
import './App.css'
import { AuthProvider, useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import CreateMarketForm from './components/CreateMarketForm'
import Dashboard from './pages/Dashboard'

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

function Navbar({ onOpenAuth, setView }) {
  const { user, logout } = useAuth();

  return (
    <nav className="navbar">
      <div className="navbar-brand" onClick={() => setView('feed')} style={{ cursor: 'pointer' }}>PottsMarket</div>
      <div className="navbar-actions">
        {user ? (
          <>
            <button className="text-btn" onClick={() => setView('dashboard')}>Dashboard</button>
            <span className="navbar-balance" style={{ marginRight: '1rem', fontWeight: 'bold' }}>
              ${user.balance !== undefined ? user.balance.toFixed(2) : '...'}
            </span>
            <span className="navbar-user">Hello, {user.username}</span>
            <button className="btn-secondary" onClick={logout}>Logout</button>
          </>
        ) : (
          <button className="btn-primary" onClick={() => onOpenAuth('login')}>Login / Signup</button>
        )}
      </div>
    </nav>
  );
}

function MainApp() {
  const apiBase = import.meta.env.VITE_API_URL || '/api'
  const { user, refreshUser } = useAuth()
  const [markets, setMarkets] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [activeTradeMarket, setActiveTradeMarket] = useState(null)

  // Auth Modal State
  const [authModalType, setAuthModalType] = useState(null); // 'login' or 'signup'
  const [editingMarket, setEditingMarket] = useState(null);
  const [currentView, setCurrentView] = useState('feed'); // 'feed' | 'dashboard'

  const fetchMarkets = async () => {
    setLoading(true)
    setError('')
    try {
      const response = await fetch(`${apiBase}/markets/`, { credentials: 'include' })
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

  const handleTradeSubmit = async (slug, outcomeId, amount) => {
    const response = await fetch(`${apiBase}/markets/${slug}/trade/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        outcome_id: outcomeId,
        amount: amount,
      }),
      credentials: 'include',
    })
    const data = await response.json()
    if (!response.ok) throw new Error(data.error || 'Trade failed')

    // Refresh markets to update prices
    fetchMarkets()
    refreshUser() // Update balance
    return data
  }
  const handleResolve = async (slug, outcomeId) => {
    try {
      const response = await fetch(`${apiBase}/markets/${slug}/resolve/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ outcome_id: outcomeId }),
        credentials: 'include',
      })
      if (!response.ok) throw new Error('Failed to resolve')
      alert('Market resolved!')
      fetchMarkets()
    } catch (err) {
      alert(err.message)
    }
  }

  const handleRedeem = async (slug) => {
    try {
      const response = await fetch(`${apiBase}/markets/${slug}/redeem/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
        credentials: 'include',
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.message || 'Failed to redeem')

      if (data.payout > 0) {
        alert(`Redeemed $${data.payout.toFixed(2)}!`)
      } else {
        alert(data.message || 'No winnings to redeem.')
      }
      fetchMarkets()
      refreshUser() // Update balance
    } catch (err) {
      alert(err.message)
    }
  }

  const handleDelete = async (slug) => {
    console.log('Delete clicked for:', slug);
    if (!window.confirm('Are you sure you want to delete this market? This action cannot be undone.')) {
      console.log('Delete cancelled');
      return;
    }

    try {
      console.log('Sending delete request...');
      const response = await fetch(`${apiBase}/markets/${slug}/delete/`, {
        method: 'DELETE',
        credentials: 'include',
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to delete market');
      }
      alert('Market deleted.');
      fetchMarkets();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleAuthSuccess = () => {
    setAuthModalType(null);
  };

  return (
    <div className="page">
      <Navbar onOpenAuth={setAuthModalType} setView={setCurrentView} />

      <header className="hero">
        <div className="hero__content">
          <div className="badge">Prediction markets</div>
          <h1>PottsMarket</h1>
          <p>
            Launch bold questions, trade conviction, and track the pulse of
            sentiment in real time.
          </p>
        </div>
      </header>

      <main className="grid">
        {currentView === 'dashboard' ? (
          <Dashboard user={user} onEditMarket={(market) => {
            setEditingMarket(market);
            // Optionally switch back to feed if we want them to see the list?
            // Or handle edit modal here. Logic below handles edit modal globally if editingMarket is set.
          }} />
        ) : (
          <>
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

                              {/* Admin Resolve Action (Simulated) */}
                              {market.status !== 'resolved' && (
                                <button className="text-btn" onClick={() => {
                                  if (confirm(`Resolve this market as ${outcome.name} WON?`)) {
                                    handleResolve(market.slug, outcome.id)
                                  }
                                }}>🏆 Win</button>
                              )}
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="market-card__actions">
                        {market.status === 'open' && (
                          <button className="secondary sm" onClick={() => {
                            if (user) {
                              setActiveTradeMarket(market);
                            } else {
                              setAuthModalType('login');
                            }
                          }}>Trade</button>
                        )}

                        {market.status === 'resolved' && (
                          <button className="primary sm" onClick={() => handleRedeem(market.slug)}>Redeem Winnings</button>
                        )}

                        {user && market.created_by === user.username && (
                          <div style={{ display: 'flex', gap: '0.5rem', marginLeft: 'auto' }}>
                            {market.status === 'draft' && (
                              <button className="primary sm" onClick={() => {
                                if (confirm('Publish this market? It will be open for trading.')) {
                                  // Quick publish action reusing the update endpoint
                                  fetch(`${apiBase}/markets/${market.slug}/`, {
                                    method: 'PUT',
                                    headers: { 'Content-Type': 'application/json' },
                                    body: JSON.stringify({ ...market, status: 'open' }),
                                    credentials: 'include',
                                  })
                                    .then(res => {
                                      if (res.ok) {
                                        alert('Market published!');
                                        fetchMarkets();
                                      } else {
                                        alert('Failed to publish.');
                                      }
                                    })
                                }
                              }}>Publish</button>
                            )}
                            <button className="text-btn" onClick={() => setEditingMarket(market)}>Edit</button>
                            <button className="text-btn delete-btn" onClick={() => handleDelete(market.slug)} style={{ color: 'red' }}>
                              Delete
                            </button>
                          </div>
                        )}
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

            {/* Edit Market Modal */}
            {editingMarket && (
              <div className="modal-overlay">
                <div className="modal">
                  <div className="modal-header">
                    <h3>Edit Market</h3>
                    <button className="ghost sm" onClick={() => setEditingMarket(null)}>✕</button>
                  </div>
                  <CreateMarketForm
                    initialData={editingMarket}
                    onCancel={() => setEditingMarket(null)}
                    onMarketCreated={(updatedMarket) => {
                      // Update local state
                      setMarkets(prev => prev.map(m => m.id === updatedMarket.id ? updatedMarket : m));
                      setEditingMarket(null);
                      alert('Market updated!');
                    }}
                  />
                </div>
              </div>
            )}

            {/* Auth Modal */}
            {
              authModalType && (
                <div className="modal-overlay" onClick={() => setAuthModalType(null)}>
                  <div className="modal auth-modal" onClick={e => e.stopPropagation()}>
                    <div className="modal-header">
                      <h3>{authModalType === 'login' ? 'Log In' : 'Sign Up'}</h3>
                      <button className="ghost sm" onClick={() => setAuthModalType(null)}>✕</button>
                    </div>

                    {authModalType === 'login' ? (
                      <>
                        <LoginPage onLoginSuccess={handleAuthSuccess} />
                        <p className="auth-switch">
                          Don't have an account? <button className="text-btn" onClick={() => setAuthModalType('signup')}>Sign Up</button>
                        </p>
                      </>
                    ) : (
                      <>
                        <SignupPage onSignupSuccess={handleAuthSuccess} />
                        <p className="auth-switch">
                          Already have an account? <button className="text-btn" onClick={() => setAuthModalType('login')}>Log In</button>
                        </p>
                      </>
                    )}
                  </div>
                </div>
              )
            }

            <section className="panel panel--accent">
              <div className="panel__header">
                <div>
                  <h2>Create a market</h2>
                  <p>Post to `api/markets/` to spin up a new idea.</p>
                </div>
              </div>

              {user ? (
                <CreateMarketForm onMarketCreated={(newMarket) => {
                  setMarkets((prev) => [newMarket, ...prev]);
                  alert('Market created successfully!');
                }} />
              ) : (
                <div className="status">
                  <p>You must be logged in to create a market.</p>
                  <button className="primary sm" onClick={() => setAuthModalType('login')}>Log In</button>
                </div>
              )}
            </section>
          </>
        )}
      </main>

      <footer className="footer">
        <span>Built for fast signals and sharper predictions.</span>
      </footer>
    </div >
  )
}

export default function App() {
  return (
    <AuthProvider>
      <MainApp />
    </AuthProvider>
  )
}
