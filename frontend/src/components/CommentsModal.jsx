import React, { useState } from 'react';

export default function CommentsModal({ isOpen, marketTitle, comments, user, onClose, onPostComment }) {
    if (!isOpen) return null;

    // Move input state inside the modal
    const [text, setText] = useState('');

    const handlePost = () => {
        if (!text.trim()) return;
        onPostComment(text);
        setText('');
    };

    return (
        <div className="modal-overlay" onClick={onClose}>
            <div className="modal comments-modal" onClick={e => e.stopPropagation()}>
                <div className="modal-header">
                    <h3>💬 Discussion</h3>
                    <button className="ghost sm" onClick={onClose}>✕</button>
                </div>
                <div className="modal-body">
                    <p className="comments-title">{marketTitle}</p>

                    {user && (
                        <div className="comment-input-wrapper">
                            <input
                                type="text"
                                placeholder="Add a comment..."
                                value={text}
                                onChange={(e) => setText(e.target.value)}
                                onKeyDown={(e) => { if (e.key === 'Enter') handlePost(); }}
                                maxLength={1000}
                            />
                            <button className="primary sm" onClick={handlePost}>Post</button>
                        </div>
                    )}

                    {!comments || comments.length === 0 ? (
                        <div className="empty-state">
                            <p>No comments yet. Be the first!</p>
                        </div>
                    ) : (
                        <div className="comments-list">
                            {comments.map((comment) => (
                                <div key={comment.id} className="comment-item">
                                    <div className="comment-header">
                                        <span className="comment-avatar">{comment.username.charAt(0).toUpperCase()}</span>
                                        <span className="comment-username">{comment.username}</span>
                                        <span className="comment-time">{new Date(comment.created_at).toLocaleDateString()}</span>
                                    </div>
                                    <p className="comment-text">{comment.text}</p>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
