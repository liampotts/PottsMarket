import React from 'react';

export default function ResolveModal({ isOpen, marketTitle, outcomeName, onConfirm, onCancel }) {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onCancel}>
            <div className="modal confirm-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>Confirm Resolution</h3>
                    <button className="ghost sm" onClick={onCancel}>✕</button>
                </div>
                <div className="modal-body">
                    <p>
                        Are you sure you want to resolve <strong>{marketTitle}</strong>?
                    </p>
                    <p style={{ marginTop: '1rem', fontSize: '1.1rem' }}>
                        Winning Outcome: <strong className={`outcome-badge ${outcomeName === 'YES' ? 'yes' : 'no'}`}>{outcomeName}</strong>
                    </p>
                    <p style={{ marginTop: '1rem', fontSize: '0.9rem', color: '#666' }}>
                        This action cannot be undone. Payouts will be calculated immediately.
                    </p>
                </div>
                <div className="modal-actions">
                    <button className="ghost" onClick={onCancel}>Cancel</button>
                    <button className="primary" onClick={onConfirm}>Resolve Market</button>
                </div>
            </div>
        </div>
    );
}
