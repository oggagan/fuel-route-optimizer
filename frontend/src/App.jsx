import { useState } from "react";
import { planRoute } from "./api";
import MapView from "./components/MapView";
import "leaflet/dist/leaflet.css";
import "./App.css";

export default function App() {
  const [start, setStart] = useState("Dallas, TX");
  const [finish, setFinish] = useState("Chicago, IL");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [activeStop, setActiveStop] = useState(null);

  async function onSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError("");
    setResult(null);
    setActiveStop(null);
    try {
      const data = await planRoute(start.trim(), finish.trim());
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <aside className="panel">
        <header className="brand">
          <span className="logo">⛽</span>
          <div>
            <h1>Fuel Route Optimizer</h1>
            <p>Cheapest fuel stops for a 500-mile-range truck at 10 MPG.</p>
          </div>
        </header>

        <form onSubmit={onSubmit} className="form">
          <label>
            Start
            <input
              value={start}
              onChange={(e) => setStart(e.target.value)}
              placeholder="City, State"
              required
            />
          </label>
          <label>
            Finish
            <input
              value={finish}
              onChange={(e) => setFinish(e.target.value)}
              placeholder="City, State"
              required
            />
          </label>
          <button type="submit" disabled={loading}>
            {loading ? "Planning route…" : "Find cheapest route"}
          </button>
        </form>

        {error && <div className="error">{error}</div>}

        {result && (
          <div className="results">
            <div className="summary">
              <div className="stat">
                <span className="stat-value">{result.total_distance_miles}</span>
                <span className="stat-label">miles</span>
              </div>
              <div className="stat">
                <span className="stat-value">{result.total_gallons}</span>
                <span className="stat-label">gallons</span>
              </div>
              <div className="stat highlight">
                <span className="stat-value">${result.total_fuel_cost.toFixed(2)}</span>
                <span className="stat-label">fuel cost</span>
              </div>
            </div>

            <h2>
              {result.fuel_stops.length} fuel stop
              {result.fuel_stops.length === 1 ? "" : "s"}
            </h2>
            {result.fuel_stops.length === 0 && (
              <p className="muted">
                The trip is within a single 500-mile tank, so no fuel stop is needed.
              </p>
            )}
            <ul className="stops">
              {result.fuel_stops.map((s, i) => (
                <li
                  key={i}
                  className={activeStop === i ? "active" : ""}
                  onMouseEnter={() => setActiveStop(i)}
                  onMouseLeave={() => setActiveStop(null)}
                >
                  <div className="stop-head">
                    <span className="stop-name">{s.name}</span>
                    <span className="stop-price">${s.price_per_gallon.toFixed(3)}/gal</span>
                  </div>
                  <div className="stop-sub">
                    {s.city}, {s.state} &middot; mile {s.mile_marker} &middot; ${s.leg_cost}
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        <footer className="foot">Built by Gagandeep Singh</footer>
      </aside>

      <main className="map-wrap">
        <MapView result={result} activeStop={activeStop} />
      </main>
    </div>
  );
}
