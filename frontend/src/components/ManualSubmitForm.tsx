// frontend/src/components/ManualSubmitForm.tsx
import { useState } from 'react';
import { Plus, Link2, Check, AlertCircle } from 'lucide-react';

interface Props {
  apiUrl: string;
  onSuccess: () => void;
}

export function ManualSubmitForm({ apiUrl, onSuccess }: Props) {
  const [url, setUrl] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    setSuccess(false);

    try {
      const response = await fetch(`${apiUrl}/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to submit');
      }

      setSuccess(true);
      setUrl('');
      onSuccess();
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="manual-submit-form">
      <h3>
        <Link2 size={18} />
        Add Listing Manually
      </h3>
      <p>Paste a Facebook Marketplace, Gumtree, or Carsales URL</p>
      
      <form onSubmit={handleSubmit}>
        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.facebook.com/marketplace/item/123456..."
          required
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Adding...' : <><Plus size={16} /> Add Listing</>}
        </button>
      </form>

      {success && (
        <div className="success-message">
          <Check size={16} /> Listing added successfully! It will appear in search results.
        </div>
      )}
      
      {error && (
        <div className="error-message">
          <AlertCircle size={16} /> {error}
        </div>
      )}
    </div>
  );
}
