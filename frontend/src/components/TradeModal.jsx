import React, { useState } from 'react';

export default function TradeModal({ market, onClose, onTrade }) {
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
