import { useState } from 'react'
import { priceLines } from './price.js'

function placeOf(spot) {
  for (const place of spot.places ?? []) {
    const parts = [place.locality || place.location_name, place.district].filter(Boolean)
    const line = [...new Set(parts)].join(', ')
    if (line) return line
  }
  return ''
}

// One recommended place: details, plus its Instagram Reel link and an inline preview.
function Spot({ spot }) {
  const [showPreview, setShowPreview] = useState(false)
  const place = placeOf(spot)
  const prices = priceLines(spot.price_information)
  const shortUrl = spot.url.replace(/^https?:\/\/(www\.)?/, '')

  return (
    <section className="spot">
      <div className="spot-head">
        <h3>{spot.restaurant_name || 'Unnamed spot'}</h3>
        {place && <span className="place">{place}</span>}
      </div>

      {spot.food_items?.length > 0 && (
        <ul className="tags">
          {spot.food_items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}

      {prices.length === 1 && <p className="detail">Price: {prices[0]}</p>}
      {prices.length > 1 && (
        <div className="detail">
          Price
          <ul className="prices">
            {prices.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      )}
      {spot.reason && <p className="detail">{spot.reason}</p>}
      {spot.needs_verification && (
        <p className="note">Details may need verification.</p>
      )}

      <div className="reel">
        <a href={spot.url} target="_blank" rel="noopener noreferrer" className="reel-link">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
            <rect x="3" y="3" width="18" height="18" rx="5" fill="none" stroke="currentColor" strokeWidth="2" />
            <circle cx="12" cy="12" r="4" fill="none" stroke="currentColor" strokeWidth="2" />
            <circle cx="17.2" cy="6.8" r="1.2" fill="currentColor" />
          </svg>
          <span>{shortUrl}</span>
        </a>
        <button
          type="button"
          className="ghost"
          aria-expanded={showPreview}
          onClick={() => setShowPreview((open) => !open)}
        >
          {showPreview ? 'Hide' : 'Preview'}
        </button>
      </div>

      {showPreview && (
        <>
          <iframe
            className="embed"
            src={`${spot.url}embed`}
            title={`Reel from ${spot.restaurant_name || spot.code}`}
            loading="lazy"
            allow="encrypted-media"
          />
          <p className="note center">Blank? Instagram may block the preview. Use the link above.</p>
        </>
      )}
    </section>
  )
}

export default Spot
