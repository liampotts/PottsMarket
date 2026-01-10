import React, { useState } from 'react';

export default function CreateMarketForm({ onMarketCreated, initialData = null, onCancel = null }) {
    const apiBase = import.meta.env.VITE_API_URL || '/api';
    const [creating, setCreating] = useState(false);
    const [createError, setCreateError] = useState('');

    const [form, setForm] = useState(initialData || {
        title: '',
        slug: '',
        description: '',
        status: 'open',
    });

    const handleChange = (event) => {
        const { name, value } = event.target;
        setForm((prev) => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (event) => {
        event.preventDefault()
        setCreating(true)
        setCreateError('')
        try {
            const url = initialData ? `${apiBase}/markets/${initialData.slug}/` : `${apiBase}/markets/`
            const method = initialData ? 'PUT' : 'POST'

            const response = await fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(form),
                credentials: 'include',
            })
            const data = await response.json()
            if (!response.ok) {
                const message =
                    data?.errors
                        ? Object.values(data.errors).join(' ')
                        : data?.error || 'Failed to save market.'
                throw new Error(message)
            }
            onMarketCreated(data)
            // Reset only if creating new
            if (!initialData) {
                setForm({ title: '', slug: '', description: '', status: 'draft' })
            }
        } catch (err) {
            setCreateError(err.message || 'Unable to save market.')
        } finally {
            setCreating(false)
        }
    }

    return (
        <form className="form" onSubmit={handleSubmit}>
            <label>
                Title
                <input
                    name="title"
                    value={form.title}
                    onChange={handleChange}
                    placeholder="Will the Lakers win the finals?"
                    required
                />
            </label>
            <label>
                Slug (URL friendly)
                <input
                    name="slug"
                    value={form.slug}
                    onChange={handleChange}
                    placeholder="lakers-finals-2025"
                    required
                />
            </label>
            <label>
                Description
                <textarea
                    name="description"
                    value={form.description}
                    onChange={handleChange}
                    placeholder="Short context to help traders decide."
                />
            </label>
            <label>
                Status
                <select name="status" value={form.status} onChange={handleChange}>
                    <option value="draft">Draft</option>
                    <option value="open">Open</option>
                </select>
            </label>
            {createError ? (
                <div className="status error">{createError}</div>
            ) : null}
            <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                <button className="primary" type="submit" disabled={creating}>
                    {creating ? 'Saving...' : (initialData ? 'Update Market' : 'Create Market')}
                </button>
                {onCancel && (
                    <button className="ghost" type="button" onClick={onCancel}>
                        Cancel
                    </button>
                )}
            </div>
        </form>
    );
}
