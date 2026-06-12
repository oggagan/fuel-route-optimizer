import { useState } from "react";
import { planRoute } from "./api";
import CityAutocomplete from "./components/CityAutocomplete";
import MapView from "./components/MapView";
import "leaflet/dist/leaflet.css";
import "./App.css";

const EXAMPLES = [
  { start: "Dallas, TX", finish: "Chicago, IL" },
  { start: "Los Angeles, CA", finish: "Phoenix, AZ" },
  { start: "New York, NY", finish: "Atlanta, GA" },
];

export default function App() {
  const [startCity, setStartCity] = useState(null);
  const [finishCity, setFinishCity] = useState(null);
  const [startText, setStartText] = useState("");
  const [finishText, setFinishText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  const [activeStop, setActiveStop] = useState(null);
  const [flyTo, setFlyTo] = useState(null);

  function buildPayload() {
    const payload = {
      start: startCity?.label || startText.trim(),
      finish: finishCity?.label || finishText.trim(),
    };
    if (startCity) {
      payload.start_label = startCity.label;
      payload.start_lat = startCity.lat;
      payload.start_lon = startCity.lon;
    }
    if (finishCity) {
      payload.finish_label = finishCity.label;
      payload.finish_lat = finishCity.lat;
      payload.finish_lon = finishCity.lon;
    }
    return payload;
  }

  async function runRoute(payload) {
    setLoading(true);
    setError("");
    setResult(null);
    setActiveStop(null);
    setFlyTo(null);
    try {
      const data = await planRoute(payload);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e) {
    e.preventDefault();
    const payload = buildPayload();
    if (!payload.start || !payload.finish) {
      setError("Please choose a start and finish city.");
      return;
    }
    runRoute(payload);
  }

  function swap() {
    setStartCity(finishCity);
    setFinishCity(startCity);
    setStartText(finishText);
    setFinishText(startText);
  }

  function useExample(ex) {
    const s = { label: ex.start };
    const f = { label: ex.finish };
    setStartCity(null);
    setFinishCity(null);
    setStartText(ex.start);
    setFinishText(ex.finish);
    runRoute({ start: ex.start, finish: ex.finish });
    void s;
    void f;
  }

  const cheapest =
    result?.fuel_stops?.length
      ? Math.min(...result.fuel_stops.map((s) => s.price_per_gallon))
      : null;

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
          <div className="fields">
            <CityAutocomplete
              id="start"
              label="Start"
              value={startCity}
              onChange={setStartCity}
              onText={setStartText}
              placeholder="Search a city…"
            />
            <button
              type="button"
              className="swap"
              onClick={swap}
              title="Swap start and finish"
              aria-label="Swap start and finish"
            >
              ⇅
            </button>
            <CityAutocomplete
              id="finish"
              label="Finish"
              value={finishCity}
              onChange={setFinishCity}
              onText={setFinishText}
              placeholder="Search a city…"
            />
          </div>

          <button type="submit" className="go" disabled={loading}>
            {loading ? (
              <>
                <span className="spinner" /> Planning route…
              </>
            ) : (
              "Find cheapest route"
            )}
          </button>
        </form>

        <div className="examples">
          <span className="examples-label">Try:</span>
          {EXAMPLES.map((ex, i) => (
            <button key={i} className="chip" onClick={() => useExample(ex)} disabled={loading}>
              {ex.start.split(",")[0]} → {ex.finish.split(",")[0]}
            </button>
          ))}
        </div>

        {error && <div className="error">{error}</div>}

        {!result && !error && !loading && (
          <div className="hint">
            Pick a start and finish, then we map the drive and the cheapest fuel
            stops along the way.
          </div>
        )}

        {result && (
          <div className="results">
            <div className="route-line">
              <span className="dot start" /> {result.start.label}
              <span className="route-arrow">→</span>
              <span className="dot finish" /> {result.finish.label}
            </div>

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
                  onClick={() => setFlyTo({ lat: s.lat, lon: s.lon, i })}
                >
                  <span className="stop-num">{i + 1}</span>
                  <div className="stop-body">
                    <div className="stop-head">
                      <span className="stop-name">{s.name}</span>
                      <span
                        className={
                          "stop-price" + (s.price_per_gallon === cheapest ? " best" : "")
                        }
                      >
                        ${s.price_per_gallon.toFixed(3)}/gal
                      </span>
                    </div>
                    <div className="stop-sub">
                      {s.city}, {s.state} &middot; mile {s.mile_marker} &middot; ${s.leg_cost}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}

        <footer className="foot">Built by Gagandeep Singh</footer>
      </aside>

      <main className="map-wrap">
        <MapView result={result} activeStop={activeStop} flyTo={flyTo} />
        {loading && <div className="map-overlay">Planning your route…</div>}
      </main>
    </div>
  );
}
