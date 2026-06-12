import { useEffect } from "react";
import {
  MapContainer,
  TileLayer,
  Polyline,
  Marker,
  Popup,
  CircleMarker,
  useMap,
} from "react-leaflet";
import L from "leaflet";

function numberedIcon(n, active) {
  return L.divIcon({
    className: "fuel-pin-wrap",
    html: `<div class="fuel-pin${active ? " active" : ""}"><span>${n}</span></div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

function FitBounds({ route }) {
  const map = useMap();
  useEffect(() => {
    if (route && route.length) {
      map.fitBounds(route, { padding: [40, 40] });
    }
  }, [route, map]);
  return null;
}

function FlyTo({ target }) {
  const map = useMap();
  useEffect(() => {
    if (target) {
      map.flyTo([target.lat, target.lon], 9, { duration: 0.8 });
    }
  }, [target, map]);
  return null;
}

const US_CENTER = [39.5, -98.35];

export default function MapView({ result, activeStop, flyTo }) {
  const route = result?.route || [];
  const stops = result?.fuel_stops || [];

  return (
    <MapContainer center={US_CENTER} zoom={4} className="map" zoomControl={true}>
      <TileLayer
        attribution='&copy; OpenStreetMap contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {route.length > 0 && (
        <>
          <Polyline positions={route} pathOptions={{ color: "#6366f1", weight: 5, opacity: 0.85 }} />
          <FitBounds route={route} />
          <CircleMarker
            center={[result.start.lat, result.start.lon]}
            radius={9}
            pathOptions={{ color: "#fff", weight: 2, fillColor: "#10b981", fillOpacity: 1 }}
          >
            <Popup>Start: {result.start.label}</Popup>
          </CircleMarker>
          <CircleMarker
            center={[result.finish.lat, result.finish.lon]}
            radius={9}
            pathOptions={{ color: "#fff", weight: 2, fillColor: "#ef4444", fillOpacity: 1 }}
          >
            <Popup>Finish: {result.finish.label}</Popup>
          </CircleMarker>
        </>
      )}
      {stops.map((s, i) => (
        <Marker key={i} position={[s.lat, s.lon]} icon={numberedIcon(i + 1, activeStop === i)}>
          <Popup>
            <strong>{s.name}</strong>
            <br />
            {s.city}, {s.state}
            <br />${s.price_per_gallon.toFixed(3)}/gal &middot; mile {s.mile_marker}
          </Popup>
        </Marker>
      ))}
      <FlyTo target={flyTo} />
    </MapContainer>
  );
}
