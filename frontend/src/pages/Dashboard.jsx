
import React, { useEffect, useState } from 'react';
import './Dashboard.css';

export default function Dashboard({ user, onEditMarket }) {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchPortfolio = async () => {
            const apiBase = import.meta.env.VITE_API_URL || '/api';
            try {
                const res = await fetch(`${apiBase}/portfolio/`, { credentials: 'include' });
                if (res.ok) {
                    const data = await res.json();
                    setStats(data);
                }
            } catch (err) {
                console.error("Failed to load portfolio", err);
            } finally {
                setLoading(false);
            }
        };

        if (user) {
            fetchPortfolio();
        }
    }, [user]);

    if (!user) {
        return (
            <div className="dashboard-empty">
                <div className="empty-icon">🔐</div>
                <h2>Please log in to view your dashboard</h2>
                <p>Track your positions, balances, and market performance.</p>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="dashboard-loading">
                <div className="loading-spinner"></div>
                <p>Loading your portfolio...</p>
            </div>
        );
    }

    if (!stats) {
        return (
            <div className="dashboard-empty">
                <div className="empty-icon">⚠️</div>
                <h2>Failed to load data</h2>
                <p>Please try refreshing the page.</p>
            </div>
        );
    }

    const cashBalance = parseFloat(user.balance) || 0;
    const positionsValue = parseFloat(stats.total_value) || 0;
    const totalNetWorth = cashBalance + positionsValue;

    return (
        <div className="dashboard">
            <header className="dashboard-header">
                <div className="welcome-section">
                    <div className="avatar">{stats.username.charAt(0).toUpperCase()}</div>
                    <div>
                        <h1>Welcome back, {stats.username}</h1>
                        <p className="subtitle">Here's your portfolio overview</p>
                    </div>
                </div>
            </header>

            <div className="stats-grid">
                <div className="stat-card cash">
                    <div className="stat-icon">💵</div>
                    <div className="stat-content">
                        <label>Cash Balance</label>
                        <div className="stat-value">${cashBalance.toFixed(2)}</div>
                    </div>
                </div>
                <div className="stat-card positions-value">
                    <div className="stat-icon">📈</div>
                    <div className="stat-content">
                        <label>Positions Value</label>
                        <div className="stat-value">${positionsValue.toFixed(2)}</div>
                    </div>
                </div>
                <div className="stat-card net-worth">
                    <div className="stat-icon">🏆</div>
                    <div className="stat-content">
                        <label>Total Net Worth</label>
                        <div className="stat-value highlight">${totalNetWorth.toFixed(2)}</div>
                    </div>
                </div>
                <div className="stat-card activity">
                    <div className="stat-icon">📊</div>
                    <div className="stat-content">
                        <label>Active Positions</label>
                        <div className="stat-value">{stats.positions.length}</div>
                    </div>
                </div>
            </div>

            <div className="dashboard-grid">
                <section className="dashboard-section positions-section">
                    <div className="section-header">
                        <h2>📋 My Positions</h2>
                        <span className="badge">{stats.positions.length}</span>
                    </div>
                    {stats.positions.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-icon">🎯</div>
                            <p>No active positions yet</p>
                            <span>Start trading to build your portfolio!</span>
                        </div>
                    ) : (
                        <div className="positions-list">
                            {stats.positions.map(pos => (
                                <div key={pos.id} className="position-card">
                                    <div className="position-main">
                                        <div className="position-title">{pos.market_title}</div>
                                        <div className="position-outcome">
                                            <span className="outcome-badge">{pos.outcome_name}</span>
                                        </div>
                                    </div>
                                    <div className="position-details">
                                        <div className="detail">
                                            <label>Shares</label>
                                            <span>{parseFloat(pos.shares).toFixed(2)}</span>
                                        </div>
                                        <div className="detail">
                                            <label>Price</label>
                                            <span>${parseFloat(pos.current_price).toFixed(2)}</span>
                                        </div>
                                        <div className="detail value">
                                            <label>Value</label>
                                            <span className="value-amount">${parseFloat(pos.value).toFixed(2)}</span>
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </section>

                <section className="dashboard-section markets-section">
                    <div className="section-header">
                        <h2>🏪 My Markets</h2>
                        <span className="badge">{stats.created_markets.length}</span>
                    </div>
                    {stats.created_markets.length === 0 ? (
                        <div className="empty-state">
                            <div className="empty-icon">💡</div>
                            <p>No markets created yet</p>
                            <span>Create your first prediction market!</span>
                        </div>
                    ) : (
                        <div className="markets-list">
                            {stats.created_markets.map(market => (
                                <div key={market.id} className="market-card-mini">
                                    <div className="market-card-content">
                                        <span className={`status-pill ${market.status}`}>{market.status}</span>
                                        <div className="market-title">{market.title}</div>
                                    </div>
                                    <button className="view-btn" onClick={() => onEditMarket(market)}>
                                        View →
                                    </button>
                                </div>
                            ))}
                        </div>
                    )}
                </section>
            </div>
        </div>
    );
}
