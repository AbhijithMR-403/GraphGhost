// The model's price_information is free-form: a string, a list of strings, a list of
// {item, price, evidence} objects, or an object like {mentioned, specific_price, evidence}.
// This turns any of them into short readable lines and never shows the raw JSON.

const ITEM_KEYS = ['item', 'name', 'dish', 'food']
const AMOUNT_KEYS = ['price', 'specific_price', 'amount', 'cost']
const NOTE_KEYS = ['mentioned', 'description', 'offer', 'details', 'note']
const HIDDEN_KEYS = new Set(['evidence', 'confidence', 'source'])

function firstPresent(entry, keys) {
  return keys.map((key) => entry[key]).find((value) => value != null && value !== '')
}

function asText(value) {
  return typeof value === 'object' ? priceLines(value).join(', ') : String(value).trim()
}

function describe(entry) {
  const item = firstPresent(entry, ITEM_KEYS)
  const amount = firstPresent(entry, AMOUNT_KEYS)
  const note = firstPresent(entry, NOTE_KEYS)

  const head =
    item != null && amount != null ? `${asText(item)} - ${asText(amount)}` : asText(amount ?? item ?? '')
  const parts = [head, note != null ? asText(note) : ''].filter(Boolean)
  if (parts.length) return parts.join(' - ')

  // Unknown shape: show the plain text values, still skipping the quoted evidence.
  return Object.entries(entry)
    .filter(([key, value]) => !HIDDEN_KEYS.has(key) && ['string', 'number'].includes(typeof value))
    .map(([, value]) => String(value).trim())
    .filter(Boolean)
    .join(' - ')
}

export function priceLines(value) {
  if (value == null || value === '') return []
  if (Array.isArray(value)) return [...new Set(value.flatMap(priceLines))]
  if (typeof value === 'object') return [describe(value)].filter(Boolean)
  return [String(value).trim()].filter(Boolean)
}
