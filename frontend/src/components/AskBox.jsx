import { useState } from "react";
import { askQuestion } from "../api/client.js";

export default function AskBox({ coin }) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const ask = async () => {
    const q = question.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await askQuestion(coin, q);
      setResult(data);
    } catch (e) {
      setError(
        e?.response?.data?.detail || "Soru yanıtlanamadı. Backend çalışıyor mu?"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="askbox">
      <h3>{coin} hakkında soru sor</h3>
      <div className="ask-input">
        <input
          type="text"
          placeholder="örn. SEC davası ne durumda?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          disabled={loading}
        />
        <button onClick={ask} disabled={loading || !question.trim()}>
          {loading ? "…" : "Sor"}
        </button>
      </div>

      {loading && <div className="skeleton ask-skeleton" />}
      {error && <p className="error">{error}</p>}

      {result && (
        <div className="ask-result">
          <p className="answer">{result.answer}</p>
          {result.sources?.length > 0 && (
            <ol className="ask-sources">
              {result.sources.map((s) => (
                <li key={s.ref}>
                  <a href={s.url} target="_blank" rel="noopener noreferrer">
                    [{s.ref}] {s.title}
                  </a>
                </li>
              ))}
            </ol>
          )}
          {result.note && <p className="note muted">{result.note}</p>}
        </div>
      )}
    </div>
  );
}
