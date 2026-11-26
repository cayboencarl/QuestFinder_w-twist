/* QuestFinder — map helpers (Leaflet + OpenStreetMap) and the browser Geolocation API. */
(function () {
  "use strict";
  const QF = (window.QF = window.QF || {});

  const tiles = (QF.config && QF.config.tiles) || {};
  const TILE_URL = tiles.url || "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
  const ATTRIBUTION = tiles.attribution || '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

  function pinIcon(kind) {
    // kind: "quest" | "me" | "exact"
    return L.divIcon({
      className: "qf-pin qf-pin-" + kind,
      html: kind === "me" ? '<span class="qf-dot"></span>' : '<span class="qf-drop"></span>',
      iconSize: kind === "me" ? [22, 22] : [30, 40],
      iconAnchor: kind === "me" ? [11, 11] : [15, 38],
      popupAnchor: [0, -34],
    });
  }

  QF.map = {
    create(el, lat, lng, zoom, opts) {
      const map = L.map(el, Object.assign({ zoomControl: true, attributionControl: true }, opts || {}))
        .setView([lat, lng], zoom || 16);
      // The OSM tile policy requires a Referer header: send the site origin.
      L.tileLayer(TILE_URL, {
        maxZoom: 19, attribution: ATTRIBUTION, referrerPolicy: "strict-origin-when-cross-origin",
      }).addTo(map);
      return map;
    },
    pinIcon,

    /**
     * Ask the browser for the current position. Resolves {lat, lng, accuracy}.
     * Tries a quick network/Wi-Fi fix first, then a precise GPS fix.
     */
    locate() {
      const messages = {
        1: "Location permission was blocked. Allow it in your browser settings, or place the pin on the map.",
        2: "Your location is not available right now. Turn on Location in your device settings, or place the pin on the map.",
        3: "Finding your location took too long. Turn on Location in your device settings, or place the pin on the map.",
      };
      if (!("geolocation" in navigator)) {
        return Promise.reject(new Error("This browser cannot share your location. Place the pin on the map instead."));
      }
      const once = (opts) => new Promise((resolve, reject) =>
        navigator.geolocation.getCurrentPosition(
          (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude, accuracy: pos.coords.accuracy }),
          reject, opts));
      return once({ enableHighAccuracy: false, timeout: 8000, maximumAge: 300000 })
        .catch((err) => {
          if (err.code === 1) throw err;  // permission denied: do not ask again
          return once({ enableHighAccuracy: true, timeout: 15000, maximumAge: 0 });
        })
        .catch((err) => { throw new Error(messages[err.code] || "Could not get your location."); });
    },

    /** Ray-casting point-in-polygon. polygon = [[lat, lng], ...]. */
    inside(lat, lng, polygon) {
      let inside = false;
      for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
        const [yi, xi] = polygon[i], [yj, xj] = polygon[j];
        if ((yi > lat) !== (yj > lat) && lng < ((xj - xi) * (lat - yi)) / (yj - yi) + xi) inside = !inside;
      }
      return inside;
    },

    /** Draw the barangay outline on a map. */
    drawBoundary(map, polygon, fit) {
      const layer = L.polygon(polygon, {
        color: "#0E5E4E", weight: 2, dashArray: "6 4", fillColor: "#0E5E4E", fillOpacity: 0.06, interactive: false,
      }).addTo(map);
      if (fit) map.fitBounds(layer.getBounds(), { padding: [12, 12] });
      return layer;
    },

    /**
     * A map where the user sets a single point by dragging the pin or tapping the map.
     * Writes the point into the given hidden inputs and calls onChange(lat, lng).
     * opts.boundary: [[lat, lng], ...] — the pin may only be placed inside it;
     * opts.onReject(): called when the user tries to place it outside.
     */
    picker(el, latInput, lngInput, defaults, onChange, opts) {
      opts = opts || {};
      const boundary = opts.boundary && opts.boundary.length ? opts.boundary : null;
      const ok = (lat, lng) => !boundary || QF.map.inside(lat, lng, boundary);

      let start = latInput.value && lngInput.value
        ? [parseFloat(latInput.value), parseFloat(lngInput.value)]
        : [defaults.lat, defaults.lng];
      if (!ok(start[0], start[1])) start = [defaults.lat, defaults.lng];

      const map = QF.map.create(el, start[0], start[1], defaults.zoom);
      if (boundary) QF.map.drawBoundary(map, boundary, true);
      const marker = L.marker(start, { draggable: true, icon: pinIcon("exact") }).addTo(map);
      let last = start.slice();

      function set(lat, lng, pan) {
        lat = Math.round(lat * 1e6) / 1e6;
        lng = Math.round(lng * 1e6) / 1e6;
        if (!ok(lat, lng)) {
          marker.setLatLng(last);  // snap back to the last valid spot
          if (opts.onReject) opts.onReject(lat, lng);
          return false;
        }
        last = [lat, lng];
        marker.setLatLng(last);
        latInput.value = lat;
        lngInput.value = lng;
        if (pan) map.setView(last, Math.max(map.getZoom(), 17));
        if (onChange) onChange(lat, lng);
        return true;
      }
      marker.on("dragend", () => { const p = marker.getLatLng(); set(p.lat, p.lng, false); });
      map.on("click", (e) => set(e.latlng.lat, e.latlng.lng, false));
      if (latInput.value && lngInput.value) set(start[0], start[1], false);
      return { map, marker, set };
    },
  };
})();
