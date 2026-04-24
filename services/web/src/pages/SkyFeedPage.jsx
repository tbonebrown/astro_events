import { useDeferredValue, useEffect, useState } from "react";

import {
  fetchSkyEventDetail,
  fetchSkyEventExplanation,
  fetchSkyFeed
} from "../api";

const DEFAULT_LOCATION = {
  lat: 41.8781,
  lon: -87.6298,
  label: "Chicago fallback"
};

const FILTERS = {
  type: [
    { value: "", label: "All events" },
    { value: "meteor_shower", label: "Meteor showers" },
    { value: "planetary_conjunction", label: "Conjunctions" },
    { value: "planet_visibility", label: "Planet guides" },
    { value: "iss_pass", label: "ISS passes" },
    { value: "lunar_phase", label: "Moon phases" },
    { value: "supermoon", label: "Supermoons" },
    { value: "eclipse", label: "Eclipses" },
    { value: "comet", label: "Comets" }
  ],
  days: [
    { value: "7", label: "Next 7 days" },
    { value: "14", label: "Next 14 days" },
    { value: "30", label: "Next 30 days" }
  ],
  visibility: [
    { value: "", label: "All visibility" },
    { value: "moderate", label: "Moderate+" },
    { value: "great", label: "Great only" }
  ]
};

function readFavorites() {
  try {
    const stored = window.localStorage.getItem("sky-feed:favorites");
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function persistFavorites(favorites) {
  try {
    window.localStorage.setItem("sky-feed:favorites", JSON.stringify(favorites));
  } catch {
    // Ignore localStorage issues in private mode or tests.
  }
}

function typeLabel(value) {
  return value.replaceAll("_", " ");
}

function visibilityThreshold(value) {
  if (value === "great") {
    return 0.72;
  }
  if (value === "moderate") {
    return 0.48;
  }
  return undefined;
}

function formatEventTime(value, timezone) {
  if (!value) {
    return "Time pending";
  }
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    timeZone: timezone
  }).format(new Date(value));
}

function directionCopy(event) {
  const direction = event.sky_position?.direction || "south";
  const altitude = event.sky_position?.altitude_deg ?? 32;
  return `Look ${direction} at ${Math.round(altitude)}deg`;
}

function paletteClass(eventType) {
  if (eventType === "meteor_shower") {
    return "sky-thumb--meteor";
  }
  if (eventType === "planetary_conjunction") {
    return "sky-thumb--conjunction";
  }
  if (eventType === "iss_pass") {
    return "sky-thumb--iss";
  }
  if (eventType === "supermoon" || eventType === "lunar_phase") {
    return "sky-thumb--moon";
  }
  return "sky-thumb--planet";
}

function SkyThumbnail({ event }) {
  const azimuth = event.sky_position?.azimuth_deg ?? 180;
  const altitude = event.sky_position?.altitude_deg ?? 32;
  const x = 18 + (azimuth / 360) * 116;
  const y = 84 - (Math.min(altitude, 90) / 90) * 54;

  return (
    <div className={`sky-thumb ${paletteClass(event.type)}`}>
      <svg viewBox="0 0 152 96" role="presentation" aria-hidden="true">
        <defs>
          <linearGradient id="skyArc" x1="10" y1="84" x2="142" y2="18" gradientUnits="userSpaceOnUse">
            <stop offset="0%" stopColor="rgba(255,255,255,0.18)" />
            <stop offset="100%" stopColor="rgba(255,255,255,0.86)" />
          </linearGradient>
        </defs>
        <path d="M12 84C42 30 110 30 140 84" fill="none" stroke="url(#skyArc)" strokeWidth="2.5" />
        <line x1="12" y1="84" x2="140" y2="84" stroke="rgba(255,255,255,0.18)" strokeWidth="2" />
        <circle cx={x} cy={y} r="6" fill="currentColor" />
        <circle cx={x} cy={y} r="16" fill="currentColor" opacity="0.16" />
      </svg>
      <span>{directionCopy(event)}</span>
    </div>
  );
}

function EventCard({ event, selected, saved, timezone, onSelect, onToggleSave }) {
  return (
    <article className={`sky-card${selected ? " sky-card--selected" : ""}`}>
      <button className="sky-card__body" onClick={() => onSelect(event.event_id)}>
        <div className="sky-card__head">
          <span className={`sky-badge sky-badge--${event.visibility_label.toLowerCase()}`}>
            {event.visibility_label}
          </span>
          <span className="sky-card__type">{typeLabel(event.type)}</span>
        </div>
        <h3>{event.title}</h3>
        <p className="sky-card__time">{formatEventTime(event.best_viewing_time, timezone)}</p>
        <p className="sky-card__summary">{event.summary}</p>
        <SkyThumbnail event={event} />
        <div className="sky-card__meta">
          <span>{directionCopy(event)}</span>
          <span>{event.observation_method}</span>
        </div>
      </button>
      <button className={`sky-save${saved ? " sky-save--active" : ""}`} onClick={() => onToggleSave(event.event_id)}>
        {saved ? "Saved" : "Save"}
      </button>
    </article>
  );
}

function TimelineRail({ events, timezone, selectedId, onSelect }) {
  const ordered = [...events].sort(
    (left, right) => new Date(left.best_viewing_time).getTime() - new Date(right.best_viewing_time).getTime()
  );

  return (
    <section className="panel sky-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Timeline</p>
          <h2>Upcoming sky moments</h2>
        </div>
      </div>
      <div className="sky-timeline">
        {ordered.map((event) => (
          <button
            className={`sky-timeline__item${selectedId === event.event_id ? " sky-timeline__item--active" : ""}`}
            key={event.event_id}
            onClick={() => onSelect(event.event_id)}
          >
            <strong>{formatEventTime(event.best_viewing_time, timezone)}</strong>
            <span>{event.title}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function DetailPanel({ event, explanation, loading, explanationLoading, timezone }) {
  if (loading) {
    return <section className="panel sky-panel">Loading sky event details...</section>;
  }

  if (!event) {
    return <section className="panel sky-panel">Pick an event to see the full sky guide.</section>;
  }

  return (
    <section className="panel sky-panel sky-detail">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Sky guide</p>
          <h2>{event.title}</h2>
        </div>
        <span className={`sky-badge sky-badge--${event.visibility_label.toLowerCase()}`}>
          {event.visibility_label}
        </span>
      </div>

      <div className="sky-detail__hero">
        <SkyThumbnail event={event} />
        <div className="sky-detail__copy">
          <p>{explanation?.summary || event.summary}</p>
          <p className="sky-detail__interesting">
            {explanationLoading ? "Generating location-aware explanation..." : explanation?.why_interesting}
          </p>
        </div>
      </div>

      <dl className="sky-detail__grid">
        <div>
          <dt>Best viewing time</dt>
          <dd>{formatEventTime(event.best_viewing_time, timezone)}</dd>
        </div>
        <div>
          <dt>Direction</dt>
          <dd>{directionCopy(event)}</dd>
        </div>
        <div>
          <dt>Duration</dt>
          <dd>{Math.round(event.duration_minutes || 0)} minutes</dd>
        </div>
        <div>
          <dt>Observe with</dt>
          <dd>{event.observation_method}</dd>
        </div>
      </dl>

      <div className="sky-detail__explanation">
        <p className="eyebrow">Why it matters</p>
        <p>{explanation?.explanation || event.description}</p>
      </div>
    </section>
  );
}

function TonightPanel({ summary, favoritesCount, visibleCount, locationLabel }) {
  return (
    <section className="panel panel--hero sky-tonight">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">Tonight's sky</p>
          <h2>{summary?.headline || "What to watch this week"}</h2>
        </div>
        <div className="sky-location-pill">{locationLabel}</div>
      </div>
      <p className="sky-tonight__lede">{summary?.summary}</p>
      <div className="sky-tonight__stats">
        <article>
          <span>Visible highlights</span>
          <strong>{visibleCount}</strong>
        </article>
        <article>
          <span>Saved events</span>
          <strong>{favoritesCount}</strong>
        </article>
        <article>
          <span>Feed promise</span>
          <strong>14 days</strong>
        </article>
      </div>
    </section>
  );
}

export default function SkyFeedPage() {
  const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  const [location, setLocation] = useState(DEFAULT_LOCATION);
  const [filters, setFilters] = useState({ type: "", days: "14", visibility: "" });
  const deferredFilters = useDeferredValue(filters);
  const [feed, setFeed] = useState([]);
  const [summary, setSummary] = useState(null);
  const [selectedId, setSelectedId] = useState("");
  const [selectedEvent, setSelectedEvent] = useState(null);
  const [explanation, setExplanation] = useState(null);
  const [favorites, setFavorites] = useState(readFavorites);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [explanationLoading, setExplanationLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!navigator.geolocation) {
      return;
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) =>
        setLocation({
          lat: Number(coords.latitude.toFixed(4)),
          lon: Number(coords.longitude.toFixed(4)),
          label: "Using your device"
        }),
      () => setLocation((current) => ({ ...current, label: "Chicago fallback" })),
      {
        enableHighAccuracy: false,
        timeout: 4000,
        maximumAge: 600000
      }
    );
  }, []);

  useEffect(() => {
    persistFavorites(favorites);
  }, [favorites]);

  useEffect(() => {
    setLoading(true);
    fetchSkyFeed({
      lat: location.lat,
      lon: location.lon,
      timezone,
      days: deferredFilters.days,
      event_type: deferredFilters.type,
      min_visibility: visibilityThreshold(deferredFilters.visibility)
    })
      .then((payload) => {
        setFeed(payload.events || []);
        setSummary(payload.tonight_summary || null);
        setSelectedId((current) => current || payload.events?.[0]?.event_id || "");
        setError("");
      })
      .catch((fetchError) => setError(fetchError.message))
      .finally(() => setLoading(false));
  }, [location, timezone, deferredFilters]);

  useEffect(() => {
    if (!selectedId) {
      setSelectedEvent(null);
      setExplanation(null);
      return;
    }
    setDetailLoading(true);
    fetchSkyEventDetail(selectedId, {
      lat: location.lat,
      lon: location.lon,
      timezone
    })
      .then((payload) => setSelectedEvent(payload))
      .finally(() => setDetailLoading(false));

    setExplanationLoading(true);
    fetchSkyEventExplanation(selectedId, {
      lat: location.lat,
      lon: location.lon,
      timezone
    })
      .then((payload) => setExplanation(payload))
      .catch(() => setExplanation(null))
      .finally(() => setExplanationLoading(false));
  }, [selectedId, location, timezone]);

  useEffect(() => {
    if (!feed.length) {
      return;
    }
    if (!feed.some((event) => event.event_id === selectedId)) {
      setSelectedId(feed[0].event_id);
    }
  }, [feed, selectedId]);

  function updateFilter(key, value) {
    setFilters((current) => ({ ...current, [key]: value }));
  }

  function toggleFavorite(eventId) {
    setFavorites((current) =>
      current.includes(eventId) ? current.filter((value) => value !== eventId) : [...current, eventId]
    );
  }

  const visibleCount = feed.filter((event) => event.visibility_label === "Great").length;

  return (
    <main className="single-column sky-feed-page">
      <TonightPanel
        summary={summary}
        favoritesCount={favorites.length}
        visibleCount={visibleCount}
        locationLabel={`${location.label} · ${timezone}`}
      />

      <section className="panel sky-panel sky-filters">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Personalized feed</p>
            <h2>Celestial Events Feed</h2>
          </div>
        </div>
        <div className="sky-filters__controls">
          {Object.entries(FILTERS).map(([key, options]) => (
            <label key={key} className="sky-select">
              <span>{key}</span>
              <select value={filters[key]} onChange={(event) => updateFilter(key, event.target.value)}>
                {options.map((option) => (
                  <option key={option.value || "all"} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
      </section>

      {loading ? <section className="panel sky-panel">Loading your personalized sky feed...</section> : null}
      {error ? <section className="panel panel--error sky-panel">{error}</section> : null}

      {feed.length ? (
        <>
          <TimelineRail events={feed.slice(0, 12)} timezone={timezone} selectedId={selectedId} onSelect={setSelectedId} />

          <section className="sky-layout">
            <div className="sky-feed-list">
              {feed.map((event) => (
                <EventCard
                  key={event.event_id}
                  event={event}
                  selected={selectedId === event.event_id}
                  saved={favorites.includes(event.event_id)}
                  timezone={timezone}
                  onSelect={setSelectedId}
                  onToggleSave={toggleFavorite}
                />
              ))}
            </div>

            <DetailPanel
              event={selectedEvent}
              explanation={explanation}
              loading={detailLoading}
              explanationLoading={explanationLoading}
              timezone={timezone}
            />
          </section>
        </>
      ) : null}
    </main>
  );
}
