import React from 'react';

export default function PublishModal({ isOpen, marketTitle, onConfirm, onCancel }) {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onCancel}>
            <div className="modal confirm-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>Publish Market</h3>
                    <button className="ghost sm" onClick={onCancel}>✕</button>
                </div>
                <div className="modal-body">
                    <p>
                        Are you sure you want to publish <strong>{marketTitle}</strong>?
                    </p>
                    <p style={{ marginTop: '1rem', color: '#666' }}>
                        Once published, the market will be open for trading. This cannot be undone.
                    </p>
                </div>
                <div className="modal-actions">
                    <button className="ghost" onClick={onCancel}>Cancel</button>
                    <button className="primary" onClick={onConfirm}>Publish Market</button>
                </div>
            </div>
        </div>
    );
}
