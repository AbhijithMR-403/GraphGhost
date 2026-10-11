import { useEffect, useRef, useState } from 'react'
import Spot from './Spot.jsx'
import './App.css'

// In development Vite proxies /api to the FastAPI server (see vite.config.js).
const API_URL = import.meta.env.VITE_API_URL ?? '/api'
const HISTORY_TURNS = 6
const INSTAGRAM_URL = /(https?:\/\/(?:www\.)?instagram\.com\/[^\s)]+)/g

const SUGGESTIONS = [
  'Where can I eat a good burrito?',
  'Best biryani spots',
  'Cheap breakfast places',
  'Something spicy near me',
]

// Turn any Instagram link in plain text into a clickable link.
function linkify(text) {
  return text.split(INSTAGRAM_URL).map((part, index) =>
    index % 2 === 1 ? (
      <a key={index} href={part} target="_blank" rel="noopener noreferrer">
        {part}
      </a>
    ) : (
      part
    ),
  )
}

async function askChatbot(message, history) {
  const response = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message, history }),
  })
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(data.detail || `Request failed (${response.status})`)
  }
  return data
}

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }, [messages, loading])

  async function send(text) {
    const message = text.trim()
    if (!message || loading) return

    const history = messages
      .filter((m) => !m.error)
      .slice(-HISTORY_TURNS)
      .map((m) => ({ role: m.role, content: m.text }))

    setMessages((current) => [...current, { role: 'user', text: message }])
    setInput('')
    setLoading(true)

    try {
      const data = await askChatbot(message, history)
      setMessages((current) => [
        ...current,
        { role: 'assistant', text: data.answer, spots: data.spots },
      ])
    } catch (error) {
      setMessages((current) => [
        ...current,
        { role: 'assistant', text: error.message, error: true, spots: [] },
      ])
    } finally {
      setLoading(false)
    }
  }

  function onSubmit(event) {
    event.preventDefault()
    send(input)
  }

  function onKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      send(input)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <span className="logo" aria-hidden="true" />
        <h1>Food spots</h1>
      </header>

      <main className="thread" aria-live="polite">
        {messages.length === 0 && (
          <section className="empty">
            <h2>What are you craving?</h2>
            <p>Ask for a dish or a place. Answers come from the Reels you saved.</p>
            <div className="chips">
              {SUGGESTIONS.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  className="chip"
                  onClick={() => send(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </section>
        )}

        {messages.map((message, index) => (
          <article key={index} className={`message ${message.role}`}>
            <p className={message.error ? 'text error' : 'text'}>
              {linkify(message.text)}
            </p>
            {message.spots?.map((spot) => (
              <Spot key={spot.code} spot={spot} />
            ))}
          </article>
        ))}

        {loading && (
          <article className="message assistant" aria-label="Thinking">
            <p className="text typing">
              <span />
              <span />
              <span />
            </p>
          </article>
        )}
        <div ref={endRef} />
      </main>

      <form className="composer" onSubmit={onSubmit}>
        <textarea
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={onKeyDown}
          placeholder="Ask for a place or a dish"
          aria-label="Your question"
          rows={1}
          maxLength={1000}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  )
}

export default App
