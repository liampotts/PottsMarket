import React from 'react';

export default function LedgerModal({ isOpen, marketTitle, totalBettors, ledger, onClose }) {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal ledger-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>📊 Trading Ledger</h3>
                    <button className="ghost sm" onClick={onClose}>✕</button>
                </div>
                <div className="modal-body">
                    <p className="ledger-title">{marketTitle}</p>
                    <p className="ledger-stats">{totalBettors} trader{totalBettors !== 1 ? 's' : ''}</p>

                    {!ledger || ledger.length === 0 ? (
                        <div className="empty-state">
                            <p>No bets placed yet</p>
                        </div>
                    ) : (
                        <div className="ledger-list">
                            {ledger.map((entry, idx) => (
                                <div key={idx} className="ledger-entry">
                                    <div className="ledger-user">
                                        <span className="user-avatar">{entry.username.charAt(0).toUpperCase()}</span>
                                        <span className="username">{entry.username}</span>
                                    </div>
                                    <div className="ledger-bet">
                                        <span className={`outcome-badge ${entry.outcome.toLowerCase()}`}>{entry.outcome}</span>
                                        <span className="shares">{entry.shares.toFixed(2)} shares</span>
                                        <span className="value">${entry.value.toFixed(2)}</span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
