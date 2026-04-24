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
                  predicted_class: "Grand design spiral",
                  morphology: "Grand design spiral",
                  confidence: 0.92,
                  rarity_score: 0.12,
                  is_outlier: false
                },
                {
                  image_id: "galaxy-2",
                  x: 1.2,
                  y: -0.8,
                  z: 0.4,
                  cluster_id: -1,
                  cluster_name: "Rare Objects",
                  predicted_class: "Peculiar merger remnant",
                  morphology: "Peculiar merger remnant",
                  confidence: 0.67,
                  rarity_score: 0.91,
                  is_outlier: true
                }
              ]
            };
          }
          if (String(path).includes("/api/clusters")) {
            return [
              {
                cluster_id: 0,
                cluster_name: "Grand Design Spirals",
                count: 1200,
                centroid_x: 0.4,
                centroid_y: 0.1,
                extent_x: 1.8,
                extent_y: 1.5,
                avg_rarity: 0.2,
                dominant_class: "Grand design spiral",
                summary: "Dense spiral family.",
                representatives: []
              }
            ];
          }
          if (String(path).includes("/api/galaxy/")) {
            return {
              image_id: "galaxy-1",
              image_url: "data:image/svg+xml;base64,PHN2Zy8+",
              cluster_id: 0,
              cluster_name: "Grand Design Spirals",
              predicted_class: "Grand design spiral",
              morphology: "Grand design spiral",
              confidence: 0.92,
              rarity_score: 0.12,
              coordinates: { x: 0.1, y: 0.2, z: 0.1, ra: 11.2, dec: -2.1 },
              metadata: {
                catalog: "galaxy-zoo",
                survey: "SDSS",
                redshift: 0.05,
                stellar_mass_log10: 10.2,
                star_formation_rate: 2.8,
                surface_brightness: 21.4,
                feature_tags: ["spiral arms", "disk"]
              },
              cluster_summary: {
                cluster_id: 0,
                cluster_name: "Grand Design Spirals",
                count: 1200,
                dominant_class: "Grand design spiral",
                avg_rarity: 0.2,
                centroid_x: 0.4,
                centroid_y: 0.1,
                extent_x: 1.8,
                extent_y: 1.5,
                summary: "Dense spiral family."
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
  window.history.replaceState({}, "", "/galaxy-map");
  render(<App />);

  expect(await screen.findByRole("heading", { name: /Google Maps for morphology space/i })).toBeInTheDocument();
  expect(screen.getByText(/Galaxies loaded/i)).toBeInTheDocument();
});
