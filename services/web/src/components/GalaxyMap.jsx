import { useEffect, useMemo, useRef, useState } from "react";

import {
  fetchGalaxyDetail,
  fetchGalaxyExplanation,
  fetchGalaxyMap,
  fetchGalaxyMapManifest,
} from "../api";
import ClusterSummaryPanel from "./ClusterSummaryPanel";
import FilterBar from "./FilterBar";
import GalaxyDetailDrawer from "./GalaxyDetailDrawer";
import StoryModeOverlay from "./StoryModeOverlay";

function navigate(path) {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new PopStateEvent("popstate"));
}

function clusterColor(clusterId) {
  const palette = [
    "#8bddff",
    "#9fffb2",
    "#ffd86a",
    "#ff8f6b",
    "#7de7ff",
    "#ff94be",
    "#d7ff72",
    "#84ffd5",
    "#ffbf88",
    "#99e2ff",
    "#d0b8ff",
    "#f7d799",
    "#f4f4ff",
  ];
  if (clusterId < 0) {
    return "#fff1ad";
  }
  return palette[clusterId % palette.length];
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function viewFromBounds(bounds, padding = 0.14) {
  const width = bounds.max_x - bounds.min_x || 1;
  const height = bounds.max_y - bounds.min_y || 1;
  return {
    centerX: (bounds.min_x + bounds.max_x) / 2,
    centerY: (bounds.min_y + bounds.max_y) / 2,
    spanX: width * (1 + padding),
    spanY: height * (1 + padding),
  };
}

function readMapState() {
  const params = new URLSearchParams(window.location.search);
  return {
    clusterId: params.get("cluster") || "",
    morphology: params.get("morphology") || "",
    instrument: params.get("instrument") || "",
    filterBand: params.get("band") || "",
    sourceField: params.get("field") || "",
    redshiftMin: params.get("zMin") || "",
    redshiftMax: params.get("zMax") || "",
    magnitudeMax: params.get("magMax") || "",
    search: params.get("search") || "",
    labelMode: params.get("labels") || "scientific",
    selectedId: params.get("selected") || "",
  };
}

function writeMapState(filters, selectedId) {
  const params = new URLSearchParams();
  const mapping = {
    clusterId: "cluster",
    morphology: "morphology",
    instrument: "instrument",
    filterBand: "band",
    sourceField: "field",
    redshiftMin: "zMin",
    redshiftMax: "zMax",
    magnitudeMax: "magMax",
    search: "search",
    labelMode: "labels",
  };
  Object.entries(mapping).forEach(([key, alias]) => {
    if (filters[key]) {
      params.set(alias, filters[key]);
    }
  });
  if (selectedId) {
    params.set("selected", selectedId);
  }
  const query = params.toString();
  const nextPath = `${window.location.pathname}${query ? `?${query}` : ""}`;
  window.history.replaceState({}, "", nextPath);
}

function buildQuery(filters) {
  return {
    limit: 15000,
    cluster_id: filters.clusterId ? Number(filters.clusterId) : undefined,
    morphology: filters.morphology || undefined,
    instrument: filters.instrument || undefined,
    filter_band: filters.filterBand || undefined,
    source_field: filters.sourceField || undefined,
    redshift_min: filters.redshiftMin || undefined,
    redshift_max: filters.redshiftMax || undefined,
    magnitude_max: filters.magnitudeMax || undefined,
    search: filters.search || undefined,
  };
}

function LabsNav() {
  return (
    <div className="labs-subnav" aria-label="Galaxy map sections">
      <button className="ghost-button" type="button" onClick={() => navigate("/labs/galaxy-map")}>
        Experience
      </button>
      <button className="ghost-button" type="button" onClick={() => navigate("/labs/galaxy-map/about")}>
        Methodology
      </button>
      <button className="ghost-button" type="button" onClick={() => navigate("/labs/galaxy-map/data")}>
        Data
      </button>
    </div>
  );
}

function MapCanvas({
  points,
  bounds,
  selectedId,
  neighborIds,
  activeCluster,
  hoverPreview,
  labelMode,
  onHoverPoint,
  onSelectPoint,
}) {
  const canvasRef = useRef(null);
  const surfaceRef = useRef(null);
  const dragRef = useRef(null);
  const [view, setView] = useState(() => viewFromBounds(bounds));
  const [hoverState, setHoverState] = useState(null);

  useEffect(() => {
    setView(viewFromBounds(bounds));
  }, [bounds.max_x, bounds.max_y, bounds.min_x, bounds.min_y]);

  useEffect(() => {
    if (!activeCluster) {
      return;
    }
    setView({
      centerX: activeCluster.centroid_x,
      centerY: activeCluster.centroid_y,
      spanX: Math.max(activeCluster.extent_x * 1.8, 1.8),
      spanY: Math.max(activeCluster.extent_y * 1.8, 1.5),
    });
  }, [activeCluster]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const surface = surfaceRef.current;
    if (!canvas || !surface) {
      return;
    }
    const ratio = window.devicePixelRatio || 1;
    const width = surface.clientWidth;
    const height = surface.clientHeight;
    canvas.width = width * ratio;
    canvas.height = height * ratio;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;

    const context = canvas.getContext("2d");
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    context.clearRect(0, 0, width, height);

    const background = context.createLinearGradient(0, 0, width, height);
    background.addColorStop(0, "rgba(6, 18, 32, 0.96)");
    background.addColorStop(0.6, "rgba(7, 21, 38, 0.98)");
    background.addColorStop(1, "rgba(2, 6, 16, 1)");
    context.fillStyle = background;
    context.fillRect(0, 0, width, height);

    for (let index = 0; index < 64; index += 1) {
      context.fillStyle = `rgba(255,255,255,${0.04 + ((index % 5) * 0.02)})`;
      context.beginPath();
      context.arc((index * 89) % width, (index * 47) % height, 0.6 + (index % 3), 0, Math.PI * 2);
      context.fill();
    }

    const neighborSet = new Set(neighborIds);
    points.forEach((point) => {
      const screenX = ((point.x - (view.centerX - view.spanX / 2)) / view.spanX) * width;
      const screenY = height - (((point.y - (view.centerY - view.spanY / 2)) / view.spanY) * height);
      if (screenX < -10 || screenX > width + 10 || screenY < -10 || screenY > height + 10) {
        return;
      }
      const depthBoost = (point.z - bounds.min_z) / Math.max(bounds.max_z - bounds.min_z, 0.001);
      let radius = 1.6 + depthBoost * 1.7;
      if (neighborSet.has(point.image_id)) {
        radius = 4.4;
      }
      if (selectedId === point.image_id) {
        radius = 6;
      }
      if (point.is_outlier) {
        radius += 0.8;
      }
      const dimmed = activeCluster && activeCluster.cluster_id !== point.cluster_id && selectedId !== point.image_id;
      context.globalAlpha = dimmed ? 0.14 : point.is_outlier ? 0.94 : 0.72;
      context.fillStyle = clusterColor(point.cluster_id);
      context.beginPath();
      context.arc(screenX, screenY, radius, 0, Math.PI * 2);
      context.fill();

      if (neighborSet.has(point.image_id) || selectedId === point.image_id) {
        context.globalAlpha = 0.22;
        context.strokeStyle = selectedId === point.image_id ? "#ffffff" : clusterColor(point.cluster_id);
        context.lineWidth = selectedId === point.image_id ? 2.4 : 1.4;
        context.beginPath();
        context.arc(screenX, screenY, radius + 5, 0, Math.PI * 2);
        context.stroke();
      }
    });
    context.globalAlpha = 1;
  }, [activeCluster, bounds, neighborIds, points, selectedId, view]);

  function findNearestPoint(clientX, clientY) {
    const rect = surfaceRef.current.getBoundingClientRect();
    const maxDistance = 14;
    let best = null;
    let bestDistance = Number.POSITIVE_INFINITY;
    points.forEach((point) => {
      const screenX = ((point.x - (view.centerX - view.spanX / 2)) / view.spanX) * rect.width;
      const screenY = rect.height - (((point.y - (view.centerY - view.spanY / 2)) / view.spanY) * rect.height);
      const distance = Math.hypot(clientX - rect.left - screenX, clientY - rect.top - screenY);
      if (distance < maxDistance && distance < bestDistance) {
        best = point;
        bestDistance = distance;
      }
    });
    return best;
  }

  function handleWheel(event) {
    event.preventDefault();
    const rect = surfaceRef.current.getBoundingClientRect();
    const xFraction = (event.clientX - rect.left) / rect.width;
    const yFraction = 1 - (event.clientY - rect.top) / rect.height;
    const anchorX = view.centerX - view.spanX / 2 + xFraction * view.spanX;
    const anchorY = view.centerY - view.spanY / 2 + yFraction * view.spanY;
    const factor = event.deltaY > 0 ? 1.15 : 0.86;
    const nextSpanX = clamp(view.spanX * factor, 0.3, (bounds.max_x - bounds.min_x) * 1.8);
    const nextSpanY = clamp(view.spanY * factor, 0.25, (bounds.max_y - bounds.min_y) * 1.8);
    setView({
      centerX: anchorX - (xFraction - 0.5) * nextSpanX,
      centerY: anchorY - (yFraction - 0.5) * nextSpanY,
      spanX: nextSpanX,
      spanY: nextSpanY,
    });
  }

  function handlePointerDown(event) {
    dragRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      view,
    };
  }

  function handlePointerMove(event) {
    if (dragRef.current) {
      const rect = surfaceRef.current.getBoundingClientRect();
      const deltaX = ((event.clientX - dragRef.current.startX) / rect.width) * dragRef.current.view.spanX;
      const deltaY = ((event.clientY - dragRef.current.startY) / rect.height) * dragRef.current.view.spanY;
      setView({
        ...dragRef.current.view,
        centerX: dragRef.current.view.centerX - deltaX,
        centerY: dragRef.current.view.centerY + deltaY,
      });
      return;
    }

    const point = findNearestPoint(event.clientX, event.clientY);
    setHoverState(
      point
        ? {
            point,
            x: event.clientX - surfaceRef.current.getBoundingClientRect().left + 16,
            y: event.clientY - surfaceRef.current.getBoundingClientRect().top + 16,
          }
        : null,
    );
    onHoverPoint(point);
  }

  function handlePointerUp() {
    dragRef.current = null;
  }

  function handleClick(event) {
    const point = findNearestPoint(event.clientX, event.clientY);
    if (point) {
      onSelectPoint(point.image_id);
    }
  }

  const hoverTitle = hoverState?.point
    ? labelMode === "simple"
      ? hoverState.point.simple_label || hoverState.point.predicted_class
      : hoverState.point.scientific_label || hoverState.point.predicted_class
    : "";

  return (
    <div
      className="galaxy-map-surface galaxy-map-surface--labs"
      onWheel={handleWheel}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerLeave={() => {
        dragRef.current = null;
        setHoverState(null);
        onHoverPoint(null);
      }}
      onClick={handleClick}
      ref={surfaceRef}
      role="presentation"
    >
      <canvas ref={canvasRef} />
      <div className="galaxy-map-legend">
        <span className="galaxy-legend-dot" />
        Similar morphology cluster
        <span className="galaxy-legend-dot galaxy-legend-dot--rare" />
        Rare-object candidate
      </div>
      {hoverState ? (
        <div className="galaxy-hover-card" style={{ left: hoverState.x, top: hoverState.y }}>
          {hoverPreview?.image_url ? (
            <img src={hoverPreview.image_url} alt={hoverState.point.image_id} />
          ) : (
            <div className="galaxy-hover-card__placeholder">Loading cutout...</div>
          )}
          <strong>{hoverTitle}</strong>
          <span>{hoverState.point.source_field}</span>
          <span>z {Number(hoverState.point.redshift || 0).toFixed(2)}</span>
        </div>
      ) : null}
    </div>
  );
}

export default function GalaxyMap() {
  const hoverFetchRef = useRef(null);
  const initialStateRef = useRef(readMapState());
  const [manifest, setManifest] = useState(null);
  const [mapData, setMapData] = useState({
    total: 0,
    returned: 0,
    visible_clusters: [],
    bounds: { min_x: -5, max_x: 5, min_y: -5, max_y: 5, min_z: -2, max_z: 2 },
    points: [],
  });
  const [filters, setFilters] = useState({
    clusterId: initialStateRef.current.clusterId,
    morphology: initialStateRef.current.morphology,
    instrument: initialStateRef.current.instrument,
    filterBand: initialStateRef.current.filterBand,
    sourceField: initialStateRef.current.sourceField,
    redshiftMin: initialStateRef.current.redshiftMin,
    redshiftMax: initialStateRef.current.redshiftMax,
    magnitudeMax: initialStateRef.current.magnitudeMax,
    search: initialStateRef.current.search,
  });
  const [labelMode, setLabelMode] = useState(initialStateRef.current.labelMode || "scientific");
  const [selectedId, setSelectedId] = useState(initialStateRef.current.selectedId || "");
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [explanation, setExplanation] = useState("");
  const [loadingMap, setLoadingMap] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  const [mapError, setMapError] = useState("");
  const [detailError, setDetailError] = useState("");
  const [storyOpen, setStoryOpen] = useState(false);
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [hoverCache, setHoverCache] = useState({});
  const [similarMode, setSimilarMode] = useState(false);

  useEffect(() => {
    fetchGalaxyMapManifest()
      .then((data) => setManifest(data))
      .catch((error) => setMapError(error.message));
  }, []);

  const query = useMemo(() => buildQuery(filters), [filters]);

  useEffect(() => {
    setLoadingMap(true);
    fetchGalaxyMap(query)
      .then((data) => {
        setMapData(data);
        setMapError("");
        if (!selectedId && data.points[0]) {
          setSelectedId(data.points[0].image_id);
        }
        if (selectedId && !data.points.find((point) => point.image_id === selectedId) && data.points[0]) {
          setSelectedId(data.points[0].image_id);
        }
      })
      .catch((error) => setMapError(error.message))
      .finally(() => setLoadingMap(false));
  }, [query, selectedId]);

  useEffect(() => {
    writeMapState({ ...filters, labelMode }, selectedId);
  }, [filters, labelMode, selectedId]);

  useEffect(() => {
    if (!selectedId) {
      return;
    }
    setLoadingDetail(true);
    setLoadingExplanation(true);
    Promise.allSettled([fetchGalaxyDetail(selectedId), fetchGalaxyExplanation(selectedId)]).then((results) => {
      const [detailResult, explanationResult] = results;
      if (detailResult.status === "fulfilled") {
        setSelectedDetail(detailResult.value);
        setDetailError("");
      } else {
        setDetailError(detailResult.reason?.message || "Unable to load galaxy detail.");
      }
      if (explanationResult.status === "fulfilled") {
        setExplanation(explanationResult.value.explanation);
      } else {
        setExplanation("");
      }
      setLoadingDetail(false);
      setLoadingExplanation(false);
    });
  }, [selectedId]);

  useEffect(() => {
    window.clearTimeout(hoverFetchRef.current);
    if (!hoveredPoint || hoverCache[hoveredPoint.image_id]) {
      return undefined;
    }
    hoverFetchRef.current = window.setTimeout(() => {
      fetchGalaxyDetail(hoveredPoint.image_id)
        .then((detail) => {
          setHoverCache((current) => ({ ...current, [hoveredPoint.image_id]: detail }));
        })
        .catch(() => undefined);
    }, 100);
    return () => window.clearTimeout(hoverFetchRef.current);
  }, [hoverCache, hoveredPoint]);

  const clusters = manifest?.clusters || [];
  const activeCluster = clusters.find((cluster) => String(cluster.cluster_id) === String(filters.clusterId || selectedDetail?.cluster_id || ""));
  const neighborIds = selectedDetail?.nearest_neighbors?.map((neighbor) => neighbor.image_id) || [];
  const heroCluster = activeCluster || clusters[0];
  const hoverPreview = hoveredPoint ? hoverCache[hoveredPoint.image_id] : null;

  function handleFilterChange(key, value) {
    if (key === "labelMode") {
      setLabelMode(value);
      return;
    }
    setFilters((current) => ({
      ...current,
      [key]: value,
    }));
  }

  function handleReset() {
    setFilters({
      clusterId: "",
      morphology: "",
      instrument: "",
      filterBand: "",
      sourceField: "",
      redshiftMin: "",
      redshiftMax: "",
      magnitudeMax: "",
      search: "",
    });
    setLabelMode("scientific");
    setSimilarMode(false);
  }

  async function handleShare() {
    try {
      await navigator.clipboard.writeText(window.location.href);
    } catch {
      window.prompt("Copy this view URL", window.location.href);
    }
  }

  function handleSelectCluster(clusterId) {
    setFilters((current) => ({ ...current, clusterId: String(clusterId), search: "" }));
    setSimilarMode(false);
  }

  function handleFindSimilar() {
    if (!selectedDetail) {
      return;
    }
    setSimilarMode(true);
    setFilters((current) => ({
      ...current,
      clusterId: String(selectedDetail.cluster_id),
      morphology: "",
      search: "",
    }));
  }

  const heroTitle = heroCluster
    ? labelMode === "simple"
      ? heroCluster.plain_cluster_name || heroCluster.cluster_name
      : heroCluster.cluster_name
    : "Galaxy Embedding Map";
  const heroSummary = heroCluster
    ? labelMode === "simple"
      ? heroCluster.plain_summary || heroCluster.summary
      : heroCluster.summary
    : manifest?.subtitle;

  return (
    <main className="single-column galaxy-labs-page">
      <LabsNav />

      <section className="panel panel--hero galaxy-labs-hero">
        <div className="galaxy-labs-hero__copy">
          <p className="eyebrow">Ohnita Labs</p>
          <h2>Galaxy Embedding Map</h2>
          <p className="home-intro__lede">
            Explore the early universe through AI-generated visual similarity maps. Each point is a galaxy, each cluster is a morphology family, and each detail panel turns embedding space into something readable.
          </p>
          <div className="galaxy-labs-hero__actions">
            <button
              className="primary-link"
              type="button"
              onClick={() => document.getElementById("galaxy-map-experience")?.scrollIntoView({ behavior: "smooth" })}
            >
              Explore the Map
            </button>
            <button className="ghost-button" type="button" onClick={() => setStoryOpen(true)}>
              Open story mode
            </button>
          </div>
        </div>
        <div className="galaxy-labs-hero__stats">
          <article className="snapshot-card">
            <span>Galaxies in sample</span>
            <strong>{manifest?.total_galaxies?.toLocaleString() || mapData.total.toLocaleString()}</strong>
            <p>Interactive JWST-style morphology sample sized for smooth 10k+ point exploration.</p>
          </article>
          <article className="snapshot-card">
            <span>Featured cluster</span>
            <strong>{heroTitle}</strong>
            <p>{heroSummary}</p>
          </article>
          <article className="snapshot-card">
            <span>Current view</span>
            <strong>{mapData.returned.toLocaleString()} points</strong>
            <p>{similarMode ? "Similar-galaxy spotlight is active." : "Filters and selection are shareable via the URL."}</p>
          </article>
        </div>
      </section>

      <section className="panel galaxy-guide-panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">How to use this tool</p>
            <h2>A map for comparison, not just a list of objects</h2>
          </div>
        </div>
        <div className="guide-grid">
          <article className="guide-card">
            <div className="guide-card__copy">
              <h3>How to use it</h3>
            </div>
            <p>
              Pan, zoom, filter, and click through clusters to compare galaxies, then open the
              detail drawer to see metadata, neighbors, and explanations for the selected object.
            </p>
          </article>
          <article className="guide-card">
            <div className="guide-card__copy">
              <h3>What it is doing</h3>
            </div>
            <p>
              The map places galaxies near other visually similar galaxies in embedding space, so
              clusters represent shared morphology and outliers surface rarer structures.
            </p>
          </article>
          <article className="guide-card">
            <div className="guide-card__copy">
              <h3>Why it matters</h3>
            </div>
            <p>
              This makes it easier to see relationships that are hard to notice in a table, helping
              visitors learn by comparison, neighborhood, and visual pattern.
            </p>
          </article>
        </div>
      </section>

      <FilterBar
        manifest={manifest}
        filters={filters}
        labelMode={labelMode}
        onChange={handleFilterChange}
        onReset={handleReset}
        onShare={handleShare}
        onOpenStory={() => setStoryOpen(true)}
      />

      <section className="galaxy-labs-layout" id="galaxy-map-experience">
        <div className="galaxy-labs-main">
          <section className="panel galaxy-map-panel galaxy-map-panel--labs">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Interactive map</p>
                <h2>AI-assisted exploration of early-universe structure</h2>
              </div>
              <div className="galaxy-map-inline-stats">
                <span>{loadingMap ? "Loading points..." : `${mapData.returned.toLocaleString()} rendered`}</span>
                <span>{mapData.total.toLocaleString()} matched</span>
                <span>{clusters.length} morphology clusters</span>
              </div>
            </div>
            {mapError ? <p className="error-copy">{mapError}</p> : null}
            <MapCanvas
              points={mapData.points}
              bounds={mapData.bounds}
              selectedId={selectedId}
              neighborIds={neighborIds}
              activeCluster={activeCluster}
              hoverPreview={hoverPreview}
              labelMode={labelMode}
              onHoverPoint={setHoveredPoint}
              onSelectPoint={(imageId) => {
                setSelectedId(imageId);
                setSimilarMode(false);
              }}
            />
          </section>

          <ClusterSummaryPanel
            clusters={clusters.slice(0, 8)}
            activeClusterId={activeCluster?.cluster_id}
            labelMode={labelMode}
            onSelectCluster={handleSelectCluster}
            onSelectGalaxy={(imageId) => {
              setSelectedId(imageId);
              setSimilarMode(false);
            }}
          />
        </div>

        <GalaxyDetailDrawer
          detail={selectedDetail}
          explanation={explanation}
          loading={loadingDetail}
          loadingExplanation={loadingExplanation}
          error={detailError}
          labelMode={labelMode}
          similarModeActive={similarMode}
          onSelectGalaxy={(imageId) => {
            setSelectedId(imageId);
            setSimilarMode(false);
          }}
          onFindSimilar={handleFindSimilar}
        />
      </section>

      <StoryModeOverlay open={storyOpen} steps={manifest?.story_steps || []} onClose={() => setStoryOpen(false)} />
    </main>
  );
}
