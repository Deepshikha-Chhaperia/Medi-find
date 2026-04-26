import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import type { SearchResult } from "@/types/medifind";
import { useNavigate } from "react-router-dom";

// Fix Leaflet default icon path in Vite
delete (L.Icon.Default.prototype as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

interface Props {
  results: SearchResult[];
  center?: [number, number];
  zoom?: number;
  showUserLocation?: boolean;
  userLocation?: { lat: number; lng: number } | null;
  radiusKm?: number;
  className?: string;
}

function scoreToColor(score: number): string {
  if (score >= 0.75) return "#1DB8A6"; // teal — high match
  if (score >= 0.5)  return "#F59E0B"; // amber — medium
  return "#EF4444";                    // red — low
}

export function MapView({
  results,
  center,
  zoom = 10,
  showUserLocation = false,
  userLocation = null,
  radiusKm = 0,
  className = "h-full w-full",
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!containerRef.current) return;
    if (mapRef.current) {
      mapRef.current.remove();
      mapRef.current = null;
    }

    // Determine map centre
    const defaultCenter: [number, number] = center ??
      (userLocation ? [userLocation.lat, userLocation.lng] :
      results[0] ? [results[0].lat, results[0].lng] : [20.5937, 78.9629]);

    const map = L.map(containerRef.current, {
      center: defaultCenter,
      zoom,
      zoomControl: false,
    });

    // Tile layer (light)
    L.tileLayer("https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://carto.com">CartoDB</a>',
      maxZoom: 19,
    }).addTo(map);

    L.control.zoom({ position: "bottomright" }).addTo(map);

    // ── User location marker ──────────────────────────────────────────────
    if (showUserLocation && userLocation) {
      const userIcon = L.divIcon({
        html: `<div style="
          width:16px;height:16px;border-radius:50%;
          background:#3B82F6;border:3px solid white;
          box-shadow:0 0 0 4px rgba(59,130,246,0.3);
        "></div>`,
        className: "",
        iconSize: [16, 16],
        iconAnchor: [8, 8],
      });
      L.marker([userLocation.lat, userLocation.lng], { icon: userIcon })
        .addTo(map)
        .bindPopup("<b>📍 Your location</b>");

      // Radius circle
      if (radiusKm > 0) {
        L.circle([userLocation.lat, userLocation.lng], {
          radius: radiusKm * 1000,
          color: "#3B82F6",
          fillColor: "#3B82F6",
          fillOpacity: 0.04,
          weight: 1.5,
          dashArray: "6 4",
        }).addTo(map);
      }
    }

    // ── Facility markers ──────────────────────────────────────────────────
    const bounds: [number, number][] = [];

    results.forEach((r) => {
      if (!r.lat || !r.lng) return;
      bounds.push([r.lat, r.lng]);

      const color = scoreToColor(r.match_score);
      const size = r.match_confidence === "High" ? 14 : r.match_confidence === "Medium" ? 11 : 9;

      const icon = L.divIcon({
        html: `<div style="
          width:${size}px;height:${size}px;border-radius:50%;
          background:${color};border:2.5px solid white;
          box-shadow:0 2px 8px ${color}66;
          transition:transform 0.15s;
        "></div>`,
        className: "",
        iconSize: [size, size],
        iconAnchor: [size / 2, size / 2],
      });

      const popup = L.popup({ maxWidth: 280, minWidth: 220 }).setContent(`
        <div style="font-family:Inter,sans-serif;padding:12px">
          <div style="font-size:11px;color:#64748b;margin-bottom:4px">
            ${r.facility_type || ""}
            ${r.emergency_24x7 ? '<span style="color:#DC2626;font-weight:600;margin-left:4px">24/7</span>' : ""}
          </div>
          <div style="font-size:15px;font-weight:600;color:#0f172a;margin-bottom:2px">${r.facility_name}</div>
          <div style="font-size:12px;color:#64748b;margin-bottom:8px">${r.city || ""}, ${r.state || ""}</div>
          ${r.distance_km > 0 ? `<div style="font-size:12px;color:#64748b;margin-bottom:6px">📍 ${r.distance_km} km away</div>` : ""}
          <div style="font-size:12px;margin-bottom:8px">
            <span style="background:${color}20;color:${color};padding:2px 8px;border-radius:4px;font-weight:600">
              ${r.match_confidence} match · ${Math.round(r.match_score * 100)}%
            </span>
          </div>
          <div style="display:flex;gap:8px;margin-top:8px">
            <a href="tel:${r.contact_phone}" style="flex:1;text-align:center;background:#0f172a;color:white;padding:6px 8px;border-radius:6px;font-size:12px;font-weight:500;text-decoration:none">📞 Call</a>
            <a href="${r.directions_url}" target="_blank" style="flex:1;text-align:center;border:1px solid #e2e8f0;color:#0f172a;padding:6px 8px;border-radius:6px;font-size:12px;font-weight:500;text-decoration:none">🗺️ Directions</a>
          </div>
          <button onclick="window.location.href='/facility/${r.facility_id}'"
            style="width:100%;margin-top:6px;background:transparent;border:none;color:#1DB8A6;font-size:12px;cursor:pointer;font-weight:500;padding:4px">
            View full profile →
          </button>
        </div>
      `);

      L.marker([r.lat, r.lng], { icon }).addTo(map).bindPopup(popup);
    });

    // Auto-fit bounds to all markers + user location
    if (bounds.length > 1) {
      if (userLocation && showUserLocation) {
        bounds.push([userLocation.lat, userLocation.lng]);
      }
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 13 });
    } else if (bounds.length === 1) {
      map.setView(bounds[0], 13);
    }

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [results, center, zoom, userLocation, showUserLocation, radiusKm]);

  return <div ref={containerRef} className={className} />;
}