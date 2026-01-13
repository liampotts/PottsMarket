import React from 'react';
import CreateMarketForm from './CreateMarketForm';

export default function EditMarketModal({ isOpen, market, onClose, onMarketUpdated }) {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay">
            <div className="modal">
                <div className="modal-header">
                    <h3>Edit Market</h3>
                    <button className="ghost sm" onClick={onClose}>✕</button>
                </div>
                <CreateMarketForm
                    initialData={market}
                    onCancel={onClose}
                    onMarketCreated={onMarketUpdated}
                />
            </div>
        </div>
    );
}
