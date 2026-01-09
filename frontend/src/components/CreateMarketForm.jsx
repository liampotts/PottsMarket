import React, { useState } from 'react';

export default function CreateMarketForm({ onMarketCreated }) {
    const apiBase = '/api';
    const [creating, setCreating] = useState(false);
    const [createError, setCreateError] = useState('');

    const [form, setForm] = useState({
        title: '',
        slug: '',
        description: '',
        status: 'draft',
    });

    const handleChange = (event) => {
        const { name, value } = event.target;
        setForm((prev) => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async (event) => {
        event.preventDefault();
        setCreating(true);
        setCreateError('');
        try {
            const response = await fetch(`${apiBase}/markets/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(form),
            });
            const data = await response.json();
            if (!response.ok) {
                const message =
                    data?.errors
                        ? Object.values(data.errors).join(' ')
                        : data?.error || 'Failed to create market.';
                throw new Error(message);
            }

            onMarketCreated(data);
            setForm({ title: '', slug: '', description: '', status: 'draft' });
        } catch (err) {
            setCreateError(err.message || 'Unable to create market.');
        } finally {
            setCreating(false);
        }
    };

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
            <button className="primary" type="submit" disabled={creating}>
                {creating ? 'Creating...' : 'Create market'}
            </button>
        </form>
    );
}
