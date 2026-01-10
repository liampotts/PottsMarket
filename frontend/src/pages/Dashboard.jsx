
import React, { useEffect, useState } from 'react';

export default function Dashboard({ user, onEditMarket }) {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchPortfolio = async () => {
            const apiBase = import.meta.env.VITE_API_URL || '/api';
            try {
                const res = await fetch(`${apiBase}/portfolio/`);
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
        return <div className="status">Please log in to view your dashboard.</div>;
    }

    if (loading) {
        return <div className="status">Loading dashboard...</div>;
    }

    if (!stats) {
        return <div className="status">Failed to load data.</div>;
    }

    return (
        <div className="dashboard">
            <header className="dashboard-header">
                <h1>Welcome, {stats.username}</h1>
                <div className="stats-row">
                    <div className="stat-card">
                        <label>Net Worth</label>
                        <div className="value">${(parseFloat(stats.total_value) || 0).toFixed(2)}</div>
                    </div>
                    <div className="stat-card">
                        <label>Positions</label>
                        <div className="value">{stats.positions.length}</div>
                    </div>
                    <div className="stat-card">
                        <label>Markets Created</label>
                        <div className="value">{stats.created_markets.length}</div>
                    </div>
                </div>
            </header>

            <section className="dashboard-section">
                <h2>My Positions</h2>
                {stats.positions.length === 0 ? (
                    <p>No active positions. Go trade!</p>
                ) : (
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>Market</th>
                                <th>Outcome</th>
                                <th>Shares</th>
                                <th>Current Price</th>
                                <th>Value</th>
                            </tr>
                        </thead>
                        <tbody>
                            {stats.positions.map(pos => (
                                <tr key={pos.id}>
                                    <td>{pos.market_title}</td>
                                    <td>{pos.outcome_name}</td>
                                    <td>{parseFloat(pos.shares).toFixed(2)}</td>
                                    <td>{parseFloat(pos.current_price).toFixed(2)}</td>
                                    <td>${parseFloat(pos.value).toFixed(2)}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </section>

            <section className="dashboard-section">
                <h2>My Markets</h2>
                {stats.created_markets.length === 0 ? (
                    <p>You haven't created any markets yet.</p>
                ) : (
                    <div className="market-list-compact">
                        {stats.created_markets.map(market => (
                            <div key={market.id} className="market-item-compact">
                                <div className="market-info">
                                    <span className={`status-badge ${market.status}`}>{market.status}</span>
                                    <strong>{market.title}</strong>
                                </div>
                                <div className="market-actions">
                                    <button className="text-btn sm" onClick={() => onEditMarket(market)}>Overview</button>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </section>
        </div>
    );
}
