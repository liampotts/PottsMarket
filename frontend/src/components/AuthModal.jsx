import React from 'react';
import LoginPage from '../pages/LoginPage';
import SignupPage from '../pages/SignupPage';

export default function AuthModal({ isOpen, type, onClose, onSwitchType, onSuccess }) {
    if (!isOpen) return null;

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal auth-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>{type === 'login' ? 'Log In' : 'Sign Up'}</h3>
                    <button className="ghost sm" onClick={onClose}>✕</button>
                </div>

                {type === 'login' ? (
                    <>
                        <LoginPage onLoginSuccess={onSuccess} />
                        <p className="auth-switch">
                            Don't have an account? <button className="text-btn" onClick={() => onSwitchType('signup')}>Sign Up</button>
                        </p>
                    </>
                ) : (
                    <>
                        <SignupPage onSignupSuccess={onSuccess} />
                        <p className="auth-switch">
                            Already have an account? <button className="text-btn" onClick={() => onSwitchType('login')}>Log In</button>
                        </p>
                    </>
                )}
            </div>
        </div>
    );
}
