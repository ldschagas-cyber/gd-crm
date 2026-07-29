export default function PlaceholderPage({ title }) {
  return (
    <>
      <header className="topbar">
        <div className="topbar-title">
          <h1>{title}</h1>
        </div>
      </header>
      <div className="content">
        <p style={{ color: 'var(--ink-dim)' }}>
          Esta tela ainda não foi implementada — ver protótipo aprovado em{' '}
          <code>docs/prototypes/</code>.
        </p>
      </div>
    </>
  )
}
