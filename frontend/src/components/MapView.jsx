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

// Default marker icons do not load under bundlers without this fix.
import markerIcon from "leaflet/dist/images/marker-icon.png";
import markerIcon2x from "leaflet/dist/images/marker-icon-2x.png";
import markerShadow from "leaflet/dist/images/marker-shadow.png";

L.Icon.Default.mergeOptions({
  iconUrl: markerIcon,
  iconRetinaUrl: markerIcon2x,
  shadowUrl: markerShadow,
});

function FitBounds({ route }) {
  const map = useMap();
  useEffect(() => {
    if (route && route.length) {
      map.fitBounds(route, { padding: [40, 40] });
    }
  }, [route, map]);
  return null;
}

const US_CENTER = [39.5, -98.35];

export default function MapView({ result, activeStop }) {
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
        <Marker key={i} position={[s.lat, s.lon]}>
          <Popup>
            <strong>{s.name}</strong>
            <br />
            {s.city}, {s.state}
            <br />${s.price_per_gallon.toFixed(3)}/gal &middot; mile {s.mile_marker}
          </Popup>
        </Marker>
      ))}
      {activeStop != null && stops[activeStop] && (
        <CircleMarker
          center={[stops[activeStop].lat, stops[activeStop].lon]}
          radius={16}
          pathOptions={{ color: "#f59e0b", weight: 3, fillOpacity: 0.15 }}
        />
      )}
    </MapContainer>
  );
}
