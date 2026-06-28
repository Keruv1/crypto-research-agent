import { useState } from "react";

export default function SearchBar({ onSearch, loading }) {
  const [value, setValue] = useState("");

  const submit = () => {
    const coin = value.trim();
    if (coin) onSearch(coin);
  };

  return (
    <div className="searchbar">
      <input
        type="text"
        placeholder="Coin gir (örn. XRP, BTC, ETH)…"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && submit()}
        disabled={loading}
        autoFocus
      />
      <button onClick={submit} disabled={loading || !value.trim()}>
        {loading ? "Araştırılıyor…" : "Araştır"}
      </button>
    </div>
  );
}
