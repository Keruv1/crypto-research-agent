export default function SourceList({ sources }) {
  if (!sources || sources.length === 0) {
    return <p className="muted">Kaynak bulunamadı.</p>;
  }

  return (
    <ul className="source-list">
      {sources.map((s, i) => (
        <li key={s.url || i}>
          <a href={s.url} target="_blank" rel="noopener noreferrer">
            {s.title}
          </a>
          <span className="source-meta">
            {s.source}
            {s.published ? ` · ${s.published}` : ""}
          </span>
        </li>
      ))}
    </ul>
  );
}
