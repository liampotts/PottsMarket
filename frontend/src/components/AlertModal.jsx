import React from 'react';

export default function AlertModal({ isOpen, title, message, onClose }) {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal confirm-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>{title || 'Alert'}</h3>
                    <button className="ghost sm" onClick={onClose}>✕</button>
                </div>
                <div className="modal-body">
                    <p>{message}</p>
                </div>
                <div className="modal-actions">
                    <button className="primary" onClick={onClose}>OK</button>
                </div>
            </div>
        </div>
    );
}
