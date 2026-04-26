/**
 * Client-side reverse geocoding using Nominatim.
 * Returns the city/area name from coordinates.
 * Caches results in sessionStorage to avoid repeated calls.
 */

const CACHE_KEY = "medifind_geocache";

type GeoCache = Record<string, { city: string; state: string; display: string }>;

function getCache(): GeoCache {
  try {
    return JSON.parse(sessionStorage.getItem(CACHE_KEY) || "{}");
  } catch {
    return {};
  }
}

function setCache(cache: GeoCache) {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(cache));
  } catch {
    // ignore
  }
}

export async function reverseGeocode(lat: number, lng: number): Promise<{ city: string; state: string; display: string }> {
  const key = `${lat.toFixed(3)},${lng.toFixed(3)}`;
  const cache = getCache();
  if (cache[key]) return cache[key];

  try {
    const res = await fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json&zoom=10`,
      {
        headers: { "User-Agent": "MediFind/1.0 (hackathon)" },
      }
    );
    const data = await res.json();
    const addr = data.address || {};
    const city = addr.city || addr.town || addr.village || addr.suburb || "";
    const state = addr.state || "";
    const result = { city, state, display: data.display_name || `${city}, ${state}` };
    const newCache = { ...cache, [key]: result };
    setCache(newCache);
    return result;
  } catch {
    return { city: "", state: "", display: "" };
  }
}

export function buildDirectionsUrl(lat: number, lng: number): string {
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lng}`;
}

export function buildWhatsAppShare(facilityName: string, address: string, phone: string, directionsUrl: string): string {
  const msg = encodeURIComponent(
    `🏥 *${facilityName}*\n📍 ${address}\n📞 ${phone}\n🗺️ Directions: ${directionsUrl}\n\n_Found via MediFind_`
  );
  return `https://wa.me/?text=${msg}`;
}
