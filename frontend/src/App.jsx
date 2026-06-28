import { useState } from "react";
import SearchBar from "./components/SearchBar.jsx";
import BriefView from "./components/BriefView.jsx";
import AskBox from "./components/AskBox.jsx";
import { getBrief } from "./api/client.js";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [brief, setBrief] = useState(null);
  const [error, setError] = useState(null);

  const search = async (coin) => {
    setLoading(true);
    setError(null);
    setBrief(null);
    try {
      const data = await getBrief(coin);
      setBrief(data);
    } catch (e) {
      setError(
        e?.response?.data?.detail ||
          "Brief üretilemedi. Backend (http://localhost:8000) çalışıyor mu ve API anahtarı tanımlı mı?"
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <header>
        <h1>🔎 Crypto Research Agent</h1>
        <p className="tagline">
          Coin gir → güncel haber + piyasa verisinden tarafsız, kaynaklı araştırma özeti.
          Yatırım tavsiyesi değildir.
        </p>
      </header>

      <SearchBar onSearch={search} loading={loading} />

      {loading && (
        <div className="brief">
          <div className="skeleton skeleton-strip" />
          <div className="cards">
            {[0, 1, 2, 3].map((i) => (
              <div className="skeleton skeleton-card" key={i} />
            ))}
          </div>
        </div>
      )}

      {error && <div className="error-box">{error}</div>}

      {brief && !loading && (
        <>
          <BriefView brief={brief} />
          <AskBox coin={brief.coin} />
        </>
      )}

      {!brief && !loading && !error && (
        <div className="empty">
          Başlamak için yukarıya bir coin sembolü gir (örn. <code>XRP</code>).
        </div>
      )}

      <footer className="muted">
        Araştırma aracı · karar senin · al/sat tavsiyesi yok
      </footer>
    </div>
  );
}
