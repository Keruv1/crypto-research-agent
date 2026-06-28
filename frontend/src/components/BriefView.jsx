import SourceList from "./SourceList.jsx";

function pct(v) {
  if (v === null || v === undefined) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function cls(v) {
  if (v === null || v === undefined) return "";
  return v >= 0 ? "up" : "down";
}

function money(v, digits = 0) {
  if (v === null || v === undefined) return "—";
  return v.toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: digits,
  });
}

const CARDS = [
  { key: "ne_oldu", title: "Ne oldu", tone: "neutral" },
  { key: "bull", title: "Bull", tone: "up" },
  { key: "bear", title: "Bear", tone: "down" },
  { key: "dikkat", title: "Dikkat", tone: "warn" },
];

export default function BriefView({ brief }) {
  const { coin, resolved_id, market, summary, sources } = brief;

  return (
    <div className="brief">
      <div className="brief-head">
        <h2>
          {coin} <span className="muted">/ {resolved_id}</span>
        </h2>
        <div className="price">{market.price_usd != null ? money(market.price_usd, 4) : "—"}</div>
      </div>

      <div className="market-strip">
        <div className="metric">
          <span className="label">24s</span>
          <span className={`val ${cls(market.change_24h)}`}>{pct(market.change_24h)}</span>
        </div>
        <div className="metric">
          <span className="label">7g</span>
          <span className={`val ${cls(market.change_7d)}`}>{pct(market.change_7d)}</span>
        </div>
        <div className="metric">
          <span className="label">30g</span>
          <span className={`val ${cls(market.change_30d)}`}>{pct(market.change_30d)}</span>
        </div>
        <div className="metric">
          <span className="label">Hacim 24s</span>
          <span className="val">{money(market.volume_24h)}</span>
        </div>
        <div className="metric">
          <span className="label">Piyasa Değeri</span>
          <span className="val">{money(market.market_cap)}</span>
        </div>
      </div>

      <div className="cards">
        {CARDS.map((c) => {
          const items = summary?.[c.key] || [];
          return (
            <div className={`card ${c.tone}`} key={c.key}>
              <h3>{c.title}</h3>
              {items.length ? (
                <ul>
                  {items.map((it, i) => (
                    <li key={i}>{it}</li>
                  ))}
                </ul>
              ) : (
                <p className="muted">—</p>
              )}
            </div>
          );
        })}
      </div>

      <div className="sources">
        <h3>Kaynaklar</h3>
        <SourceList sources={sources} />
      </div>
    </div>
  );
}
