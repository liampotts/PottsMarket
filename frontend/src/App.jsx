import { useEffect, useState } from 'react'
import './App.css'
import { AuthProvider, useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import SignupPage from './pages/SignupPage'
import CreateMarketForm from './components/CreateMarketForm'
import ConfirmModal from './components/ConfirmModal'
import ResolveModal from './components/ResolveModal'
import PublishModal from './components/PublishModal'
import TradeModal from './components/TradeModal'
import AuthModal from './components/AuthModal'
import LedgerModal from './components/LedgerModal'
import CommentsModal from './components/CommentsModal'
import EditMarketModal from './components/EditMarketModal'
import Dashboard from './pages/Dashboard'

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
  const [deleteConfirm, setDeleteConfirm] = useState(null); // slug of market to delete
  const [activeLedger, setActiveLedger] = useState(null); // { market, ledger } for ledger modal
  const [activeComments, setActiveComments] = useState(null); // { slug, market, comments } for comments modal
  const [resolvingMarket, setResolvingMarket] = useState(null); // { slug, outcomeId, marketTitle, outcomeName }
  const [publishingMarket, setPublishingMarket] = useState(null); // market object to publish

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
    try {
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
    } finally {
      setDeleteConfirm(null);
    }
  };

  const fetchLedger = async (slug, title) => {
    try {
      const response = await fetch(`${apiBase}/markets/${slug}/ledger/`, { credentials: 'include' });
      if (!response.ok) throw new Error('Failed to load ledger');
      const data = await response.json();
      setActiveLedger({ market: title, ledger: data.ledger, totalBettors: data.total_bettors });
    } catch (err) {
      alert(err.message);
    }
  };

  const fetchComments = async (slug, title) => {
    try {
      const response = await fetch(`${apiBase}/markets/${slug}/comments/`, { credentials: 'include' });
      if (!response.ok) throw new Error('Failed to load comments');
      const data = await response.json();
      setActiveComments({ slug, market: title, comments: data.comments });
    } catch (err) {
      alert(err.message);
    }
  };

  const postComment = async (text) => {
    try {
      const response = await fetch(`${apiBase}/markets/${activeComments.slug}/comments/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
        credentials: 'include',
      });
      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.error || 'Failed to post comment');
      }
      const comment = await response.json();
      setActiveComments(prev => ({
        ...prev,
        comments: [comment, ...prev.comments]
      }));
    } catch (err) {
      alert(err.message);
    }
  };

  const handlePublish = async (market) => {
    try {
      const response = await fetch(`${apiBase}/markets/${market.slug}/`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...market, status: 'open' }),
        credentials: 'include',
      });
      if (response.ok) {
        alert('Market published!');
        fetchMarkets();
      } else {
        alert('Failed to publish.');
      }
    } catch (err) {
      alert(err.message);
    } finally {
      setPublishingMarket(null);
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
                                  setResolvingMarket({
                                    slug: market.slug,
                                    outcomeId: outcome.id,
                                    marketTitle: market.title,
                                    outcomeName: outcome.name
                                  });
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

                        <button className="ghost sm" onClick={() => fetchLedger(market.slug, market.title)}>
                          📊 Ledger
                        </button>

                        <button className="ghost sm" onClick={() => fetchComments(market.slug, market.title)}>
                          💬 Comments
                        </button>

                        {market.status === 'resolved' && (
                          <button className="primary sm" onClick={() => handleRedeem(market.slug)}>Redeem Winnings</button>
                        )}

                        {user && (market.created_by === user.username || user.is_staff) && (
                          <div style={{ display: 'flex', gap: '0.5rem', marginLeft: 'auto' }}>
                            {market.status === 'draft' && (
                              <button className="primary sm" onClick={() => setPublishingMarket(market)}>Publish</button>
                            )}
                            <button className="text-btn" onClick={() => setEditingMarket(market)}>Edit</button>
                            <button className="text-btn delete-btn" onClick={() => setDeleteConfirm(market.slug)} style={{ color: 'red' }}>
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

            <section className="panel panel--accent">
              <div className="panel__header">
                <div>
                  <h2>Create a market</h2>
                  <p>Launch a new prediction market for others to trade.</p>
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

      {/* Modal Components */}
      {activeTradeMarket && (
        <TradeModal
          market={activeTradeMarket}
          onClose={() => setActiveTradeMarket(null)}
          onTrade={handleTradeSubmit}
        />
      )}

      <LedgerModal
        isOpen={!!activeLedger}
        marketTitle={activeLedger?.market}
        totalBettors={activeLedger?.totalBettors}
        ledger={activeLedger?.ledger}
        onClose={() => setActiveLedger(null)}
      />

      <CommentsModal
        isOpen={!!activeComments}
        marketTitle={activeComments?.market}
        comments={activeComments?.comments}
        user={user}
        onClose={() => setActiveComments(null)}
        onPostComment={postComment}
      />

      <ConfirmModal
        isOpen={!!deleteConfirm}
        title="Delete Market"
        message="Are you sure you want to delete this market? This action cannot be undone."
        onConfirm={() => handleDelete(deleteConfirm)}
        onCancel={() => setDeleteConfirm(null)}
      />

      <ResolveModal
        isOpen={!!resolvingMarket}
        marketTitle={resolvingMarket?.marketTitle}
        outcomeName={resolvingMarket?.outcomeName}
        onConfirm={() => {
          handleResolve(resolvingMarket.slug, resolvingMarket.outcomeId);
          setResolvingMarket(null);
        }}
        onCancel={() => setResolvingMarket(null)}
      />

      <PublishModal
        isOpen={!!publishingMarket}
        marketTitle={publishingMarket?.title}
        onConfirm={() => handlePublish(publishingMarket)}
        onCancel={() => setPublishingMarket(null)}
      />

      <EditMarketModal
        isOpen={!!editingMarket}
        market={editingMarket}
        onClose={() => setEditingMarket(null)}
        onMarketUpdated={(updatedMarket) => {
          setMarkets(prev => prev.map(m => m.id === updatedMarket.id ? updatedMarket : m));
          setEditingMarket(null);
          alert('Market updated!');
        }}
      />

      <AuthModal
        isOpen={!!authModalType}
        type={authModalType}
        onClose={() => setAuthModalType(null)}
        onSwitchType={setAuthModalType}
        onSuccess={handleAuthSuccess}
      />

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
