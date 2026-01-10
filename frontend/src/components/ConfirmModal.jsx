import React from 'react';

export default function ConfirmModal({ isOpen, title, message, onConfirm, onCancel }) {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onCancel}>
            <div className="modal confirm-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>{title || 'Confirm'}</h3>
                    <button className="ghost sm" onClick={onCancel}>✕</button>
                </div>
                <div className="modal-body">
                    <p>{message}</p>
                </div>
                <div className="modal-actions">
                    <button className="ghost" onClick={onCancel}>Cancel</button>
                    <button className="primary danger" onClick={onConfirm}>Confirm</button>
                </div>
            </div>
        </div>
    );
}
