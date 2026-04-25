import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import App from "../App";

beforeEach(() => {
  Object.defineProperty(HTMLElement.prototype, "clientWidth", {
    configurable: true,
    get() {
      return 960;
    }
  });
  Object.defineProperty(HTMLElement.prototype, "clientHeight", {
    configurable: true,
    get() {
      return 620;
    }
  });
  HTMLCanvasElement.prototype.getContext = vi.fn(() => ({
    setTransform: vi.fn(),
    clearRect: vi.fn(),
    fillRect: vi.fn(),
    createLinearGradient: vi.fn(() => ({ addColorStop: vi.fn() })),
    beginPath: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    stroke: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn()
  }));
  HTMLElement.prototype.getBoundingClientRect = vi.fn(() => ({
    width: 960,
    height: 620,
    top: 0,
    left: 0,
    right: 960,
    bottom: 620
  }));
  vi.stubGlobal(
    "fetch",
    vi.fn((path) =>
      Promise.resolve({
        ok: true,
        json: async () => {
          if (String(path).includes("/api/transients?")) {
            return [
              {
                candidate_id: "gaia-1",
                external_alert_id: "Gaia24abc",
                rank: 1,
                score: 0.91,
                novelty_flag: true,
                summary: "Synthetic alert used for the app shell test.",
                classification_hint: "Cataclysmic variable",
                magnitude_change: 1.23,
                sky_region: "Cygnus"
              }
            ];
          }
          if (String(path).includes("/api/transients/reports/latest")) {
            return {
              title: "Nightly transient report",
              markdown: "Report body",
              run: { run_date: "2026-04-23" }
            };
          }
          if (String(path).includes("/api/candidates?")) {
            return [
              {
                candidate_id: "tic-1",
                tic_id: "123456789",
                anomaly_score: 0.83,
                variability_hint: "Unusual periodicity"
              }
            ];
          }
          if (String(path).includes("/api/galaxy-map/manifest")) {
            return {
              title: "Galaxy Embedding Map",
              subtitle: "Explore the early universe through AI-assisted visual similarity maps.",
              total_galaxies: 12000,
              data_mode: "synthetic",
              ranges: {
                redshift_min: 0.1,
                redshift_max: 8.8,
                magnitude_min: 23.5,
                magnitude_max: 29.4
              },
              instruments: ["NIRCam"],
              filter_bands: ["F200W", "F277W"],
              morphologies: ["Grand design spiral", "Peculiar merger remnant"],
              source_fields: ["CEERS", "JADES"],
              clusters: [
                {
                  cluster_id: 0,
                  cluster_name: "Grand Design Spirals",
                  plain_cluster_name: "Spiral cities",
                  count: 1200,
                  centroid_x: 0.4,
                  centroid_y: 0.1,
                  extent_x: 1.8,
                  extent_y: 1.5,
                  avg_rarity: 0.2,
                  dominant_class: "Grand design spiral",
                  summary: "Dense spiral family.",
                  plain_summary: "Classic spiral galaxies.",
                  redshift_min: 0.4,
                  redshift_max: 2.2,
                  representatives: [
                    {
                      image_id: "galaxy-1",
                      cluster_id: 0,
                      cluster_name: "Grand Design Spirals",
                      plain_cluster_name: "Spiral cities",
                      predicted_class: "Grand design spiral",
                      scientific_label: "Grand design spiral",
                      simple_label: "Large spiral galaxy",
                      x: 0.1,
                      y: 0.2,
                      confidence: 0.92,
                      redshift: 0.05,
                      magnitude: 24.3,
                      image_url: "data:image/svg+xml;base64,PHN2Zy8+"
                    }
                  ]
                }
              ],
              story_steps: [
                {
                  id: "embeddings",
                  title: "What the map shows",
                  body: "Nearby points share similar visual structure."
                }
              ],
              methodology: [
                {
                  title: "Embed",
                  detail: "Synthetic embeddings for test coverage."
                }
              ],
              data_sources: [
                {
                  label: "Mock sample",
                  detail: "Synthetic sample."
                }
              ],
              artifacts: [
                {
                  name: "galaxies.parquet",
                  path: "/tmp/galaxies.parquet",
                  description: "Synthetic artifact."
                }
              ]
            };
          }
          if (String(path).includes("/api/galaxies")) {
            return {
              total: 12000,
              returned: 2,
              visible_clusters: [0, 1],
              bounds: {
                min_x: -10,
                max_x: 10,
                min_y: -6,
                max_y: 6,
                min_z: -2,
                max_z: 2
              },
              points: [
                {
                  image_id: "galaxy-1",
                  x: 0.1,
                  y: 0.2,
                  z: 0.1,
                  cluster_id: 0,
                  cluster_name: "Grand Design Spirals",
                  plain_cluster_name: "Spiral cities",
                  predicted_class: "Grand design spiral",
                  scientific_label: "Grand design spiral",
                  simple_label: "Large spiral galaxy",
                  morphology: "Grand design spiral",
                  confidence: 0.92,
                  rarity_score: 0.12,
                  redshift: 0.05,
                  magnitude: 24.3,
                  source_field: "CEERS",
                  instrument: "NIRCam",
                  filter_band: "F200W",
                  thumbnail_url: null,
                  is_outlier: false
                },
                {
                  image_id: "galaxy-2",
                  x: 1.2,
                  y: -0.8,
                  z: 0.4,
                  cluster_id: -1,
                  cluster_name: "Rare Objects",
                  plain_cluster_name: "Rare shapes",
                  predicted_class: "Peculiar merger remnant",
                  scientific_label: "Peculiar merger remnant",
                  simple_label: "Rare galaxy",
                  morphology: "Peculiar merger remnant",
                  confidence: 0.67,
                  rarity_score: 0.91,
                  redshift: 4.25,
                  magnitude: 28.6,
                  source_field: "JADES",
                  instrument: "NIRCam",
                  filter_band: "F277W",
                  thumbnail_url: null,
                  is_outlier: true
                }
              ]
            };
          }
          if (String(path).includes("/api/galaxy/")) {
            return {
              image_id: "galaxy-1",
              image_url: "data:image/svg+xml;base64,PHN2Zy8+",
              cluster_id: 0,
              cluster_name: "Grand Design Spirals",
              plain_cluster_name: "Spiral cities",
              predicted_class: "Grand design spiral",
              scientific_label: "Grand design spiral",
              simple_label: "Large spiral galaxy",
              morphology: "Grand design spiral",
              confidence: 0.92,
              rarity_score: 0.12,
              coordinates: { x: 0.1, y: 0.2, z: 0.1, ra: 11.2, dec: -2.1 },
              metadata: {
                catalog: "galaxy-zoo",
                survey: "SDSS",
                observation_source: "Synthetic sample",
                observation_program: "CEERS pilot",
                source_field: "CEERS",
                instrument: "NIRCam",
                filter_band: "F200W",
                redshift: 0.05,
                magnitude: 24.3,
                brightness_score: 0.72,
                lookback_time_gyr: 0.7,
                stellar_mass_log10: 10.2,
                star_formation_rate: 2.8,
                surface_brightness: 21.4,
                feature_tags: ["spiral arms", "disk"],
                morphology_tags: ["spiral arms", "disk"],
                data_mode: "synthetic"
              },
              cluster_summary: {
                cluster_id: 0,
                cluster_name: "Grand Design Spirals",
                plain_cluster_name: "Spiral cities",
                count: 1200,
                dominant_class: "Grand design spiral",
                avg_rarity: 0.2,
                centroid_x: 0.4,
                centroid_y: 0.1,
                extent_x: 1.8,
                extent_y: 1.5,
                summary: "Dense spiral family.",
                plain_summary: "Classic spiral galaxies.",
                redshift_min: 0.4,
                redshift_max: 2.2
              },
              nearest_neighbors: []
            };
          }
          if (String(path).includes("/api/explain/")) {
            return {
              image_id: "galaxy-1",
              explanation: "This galaxy sits in a dense spiral cluster with strong arm structure.",
              source: "fallback"
            };
          }
          if (String(path).includes("/api/events/personalized")) {
            return {
              requested_location: {
                latitude: 41.8781,
                longitude: -87.6298,
                timezone: "America/Chicago"
              },
              generated_at: "2026-04-23T00:00:00Z",
              tonight_summary: {
                headline: "Eta Aquariids meteor shower",
                summary: "Fast meteors are starting to build before dawn.",
                count: 2
              },
              events: [
                {
                  event_id: "meteor-eta-aquariids-2026",
                  title: "Eta Aquariids meteor shower",
                  type: "meteor_shower",
                  start_time: "2026-04-23T00:00:00Z",
                  end_time: "2026-05-06T00:00:00Z",
                  peak_time: "2026-05-05T09:00:00Z",
                  best_viewing_time: "2026-05-05T09:00:00Z",
                  visibility_score: 0.88,
                  visibility_label: "Great",
                  magnitude: 2.5,
                  brightness_score: 0.72,
                  description: "Synthetic shower description.",
                  region_applicability: { lat_min: -65, lat_max: 45, lon_min: -180, lon_max: 180 },
                  rarity_score: 0.74,
                  importance_score: 0.81,
                  sky_position: {
                    azimuth_deg: 120,
                    altitude_deg: 38,
                    direction: "southeast"
                  },
                  observation_method: "naked eye",
                  duration_minutes: 120,
                  thumbnail: { badge: "Meteor Shower" },
                  summary: "Fast meteors are starting to build before dawn.",
                  why_interesting: "A strong annual shower."
                }
              ]
            };
          }
          if (String(path).includes("/api/events/") && String(path).includes("/explain")) {
            return {
              event_id: "meteor-eta-aquariids-2026",
              summary: "Fast meteors are starting to build before dawn.",
              why_interesting: "A strong annual shower.",
              explanation: "This shower comes from Halley's debris stream.",
              source: "fallback"
            };
          }
          if (String(path).includes("/api/events/")) {
            return {
              event_id: "meteor-eta-aquariids-2026",
              title: "Eta Aquariids meteor shower",
              type: "meteor_shower",
              start_time: "2026-04-23T00:00:00Z",
              end_time: "2026-05-06T00:00:00Z",
              peak_time: "2026-05-05T09:00:00Z",
              best_viewing_time: "2026-05-05T09:00:00Z",
              visibility_score: 0.88,
              visibility_label: "Great",
              magnitude: 2.5,
              brightness_score: 0.72,
              description: "Synthetic shower description.",
              region_applicability: { lat_min: -65, lat_max: 45, lon_min: -180, lon_max: 180 },
              rarity_score: 0.74,
              importance_score: 0.81,
              sky_position: {
                azimuth_deg: 120,
                altitude_deg: 38,
                direction: "southeast"
              },
              observation_method: "naked eye",
              duration_minutes: 120,
              thumbnail: { badge: "Meteor Shower" },
              summary: "Fast meteors are starting to build before dawn.",
              why_interesting: "A strong annual shower."
            };
          }
          return {};
        },
        text: async () => ""
      }),
    ),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

test("renders the application shell", () => {
  window.history.replaceState({}, "", "/");
  render(<App />);

  expect(
    screen.getByRole("heading", {
      name: /A place to learn from the sky through live data and open exploration\./i
    }),
  ).toBeInTheDocument();
  expect(screen.getAllByRole("button", { name: /Transient feed/i }).length).toBeGreaterThan(0);
  expect(screen.getAllByRole("button", { name: /Nightly report/i }).length).toBeGreaterThan(0);
});

test("renders the galaxy map route", async () => {
  window.history.replaceState({}, "", "/labs/galaxy-map");
  render(<App />);

  expect((await screen.findAllByRole("heading", { name: /Galaxy Embedding Map/i })).length).toBeGreaterThan(0);
  expect(screen.getAllByText(/Explore the Map/i).length).toBeGreaterThan(0);
});

test("renders the celestial events route", async () => {
  window.history.replaceState({}, "", "/sky-feed");
  render(<App />);

  expect(await screen.findByRole("heading", { name: /Upcoming sky moments/i })).toBeInTheDocument();
  expect(screen.getAllByText(/Eta Aquariids meteor shower/i).length).toBeGreaterThan(0);
  expect(await screen.findByText(/This shower comes from Halley's debris stream/i)).toBeInTheDocument();
});

test("renders the recent papers route", async () => {
  window.history.replaceState({}, "", "/papers");
  render(<App />);

  expect(
    await screen.findByRole("heading", { name: /Top 10 interesting astronomy papers this week/i }),
  ).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /arXiv 2604\.21848/i })).toHaveAttribute(
    "href",
    "https://arxiv.org/abs/2604.21848",
  );
});
