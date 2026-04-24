import { useEffect, useRef, useState } from "react";

import {
  fetchGalaxyClusters,
  fetchGalaxyDetail,
  fetchGalaxyExplanation,
  fetchGalaxyMap
} from "../api";
import GalaxyDetailPanel from "./GalaxyDetailPanel";

function clusterColor(clusterId) {
  const palette = [
    "#66d9ff",
    "#92ff7a",
    "#ffd86a",
    "#ff9b7c",
    "#8dd8ff",
    "#ff7fb2",
    "#a5a2ff",
    "#89ffd7",
    "#ffc27a",
    "#9be1ff",
    "#f4b5ff",
    "#ffdcb5",
    "#b6f1d3",
    "#ffb2d1",
    "#ffffff"
  ];
  if (clusterId < 0) {
    return "#fff1ad";
  }
  return palette[clusterId % palette.length];
}

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function viewFromBounds(bounds, padding = 0.18) {
  const width = bounds.max_x - bounds.min_x || 1;
  const height = bounds.max_y - bounds.min_y || 1;
  return {
    centerX: (bounds.min_x + bounds.max_x) / 2,
    centerY: (bounds.min_y + bounds.max_y) / 2,
    spanX: width * (1 + padding),
    spanY: height * (1 + padding)
  };
}

function formatNumber(value, digits = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "n/a";
  }
  return Number(value).toFixed(digits);
}

function MapCanvas({
  points,
  bounds,
  selectedId,
  neighborIds,
  focusedCluster,
  hoverPreview,
  onHoverPoint,
  onSelectPoint,
  onViewportChange
}) {
  const canvasRef = useRef(null);
  const surfaceRef = useRef(null);
  const dragRef = useRef(null);
  const debounceRef = useRef(null);
  const viewportChangeRef = useRef(onViewportChange);
  const [view, setView] = useState(() => viewFromBounds(bounds));
  const [hoverState, setHoverState] = useState(null);
  const [depthMode, setDepthMode] = useState(true);

  useEffect(() => {
    viewportChangeRef.current = onViewportChange;
  }, [onViewportChange]);

  useEffect(() => {
    setView(viewFromBounds(bounds));
  }, [bounds.min_x, bounds.max_x, bounds.min_y, bounds.max_y]);

  useEffect(() => {
    if (!focusedCluster) {
      return;
    }
    setView({
      centerX: focusedCluster.centroid_x,
      centerY: focusedCluster.centroid_y,
      spanX: Math.max(focusedCluster.extent_x * 1.9, 1.8),
      spanY: Math.max(focusedCluster.extent_y * 1.9, 1.4)
    });
  }, [focusedCluster]);

  useEffect(() => {
    window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      viewportChangeRef.current({
        min_x: view.centerX - view.spanX / 2,
        max_x: view.centerX + view.spanX / 2,
        min_y: view.centerY - view.spanY / 2,
        max_y: view.centerY + view.spanY / 2,
        zoom: (bounds.max_x - bounds.min_x) / Math.max(view.spanX, 0.0001)
      });
    }, 180);
    return () => window.clearTimeout(debounceRef.current);
  }, [bounds.max_x, bounds.min_x, view]);

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
    background.addColorStop(0, "rgba(7, 24, 44, 0.94)");
    background.addColorStop(1, "rgba(3, 9, 20, 0.98)");
    context.fillStyle = background;
    context.fillRect(0, 0, width, height);

    for (let index = 0; index < 55; index += 1) {
      context.fillStyle = `rgba(255,255,255,${0.06 + ((index % 5) * 0.03)})`;
      context.beginPath();
      context.arc(
        (index * 97) % width,
        (index * 53) % height,
        0.5 + (index % 4),
        0,
        Math.PI * 2
      );
      context.fill();
    }

    const selectedSet = new Set([selectedId]);
    const neighborSet = new Set(neighborIds);

    points.forEach((point) => {
      const screenX = ((point.x - (view.centerX - view.spanX / 2)) / view.spanX) * width;
      const screenY = height - (((point.y - (view.centerY - view.spanY / 2)) / view.spanY) * height);
      if (screenX < -8 || screenX > width + 8 || screenY < -8 || screenY > height + 8) {
        return;
      }

      const depthBoost = depthMode ? (point.z - bounds.min_z) / Math.max(bounds.max_z - bounds.min_z, 0.001) : 0.5;
      let radius = 1.7 + depthBoost * 1.7;
      if (neighborSet.has(point.image_id)) {
        radius = 4.6;
      }
      if (selectedSet.has(point.image_id)) {
        radius = 6.2;
      }
      if (point.is_outlier) {
        radius += 1.1;
      }
      context.globalAlpha = point.is_outlier ? 0.95 : 0.72;
      context.fillStyle = clusterColor(point.cluster_id);
      context.beginPath();
      context.arc(screenX, screenY, radius, 0, Math.PI * 2);
      context.fill();

      if (neighborSet.has(point.image_id) || selectedSet.has(point.image_id)) {
        context.globalAlpha = 0.22;
        context.strokeStyle = selectedSet.has(point.image_id) ? "#ffffff" : clusterColor(point.cluster_id);
        context.lineWidth = selectedSet.has(point.image_id) ? 2.6 : 1.4;
        context.beginPath();
        context.arc(screenX, screenY, radius + 5, 0, Math.PI * 2);
        context.stroke();
      }
    });
    context.globalAlpha = 1;
  }, [bounds, depthMode, neighborIds, points, selectedId, view]);

  function screenToWorld(clientX, clientY) {
    const rect = surfaceRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    return {
      x: view.centerX - view.spanX / 2 + (x / rect.width) * view.spanX,
      y: view.centerY + view.spanY / 2 - (y / rect.height) * view.spanY,
      surfaceX: x,
      surfaceY: y
    };
  }

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
    const factor = event.deltaY > 0 ? 1.14 : 0.88;
    const nextSpanX = clamp(view.spanX * factor, 0.35, (bounds.max_x - bounds.min_x) * 1.8);
    const nextSpanY = clamp(view.spanY * factor, 0.25, (bounds.max_y - bounds.min_y) * 1.8);
    setView({
      centerX: anchorX - (xFraction - 0.5) * nextSpanX,
      centerY: anchorY - (yFraction - 0.5) * nextSpanY,
      spanX: nextSpanX,
      spanY: nextSpanY
    });
  }

  function handlePointerDown(event) {
    dragRef.current = {
      startX: event.clientX,
      startY: event.clientY,
      view
    };
  }

  function handlePointerMove(event) {
    if (dragRef.current) {
      const rect = surfaceRef.current.getBoundingClientRect();
      const deltaX = event.clientX - dragRef.current.startX;
      const deltaY = event.clientY - dragRef.current.startY;
      setView({
        centerX: dragRef.current.view.centerX - (deltaX / rect.width) * dragRef.current.view.spanX,
        centerY: dragRef.current.view.centerY + (deltaY / rect.height) * dragRef.current.view.spanY,
        spanX: dragRef.current.view.spanX,
        spanY: dragRef.current.view.spanY
      });
      return;
    }

    const point = findNearestPoint(event.clientX, event.clientY);
    if (!point) {
      setHoverState(null);
      onHoverPoint(null);
      return;
    }
    const world = screenToWorld(event.clientX, event.clientY);
    setHoverState({
      point,
      x: world.surfaceX + 18,
      y: world.surfaceY + 18
    });
    onHoverPoint(point);
  }

  function handlePointerLeave() {
    dragRef.current = null;
    setHoverState(null);
    onHoverPoint(null);
  }

  function handlePointerUp(event) {
    const dragging = dragRef.current;
    dragRef.current = null;
    if (!dragging) {
      return;
    }
    const dragDistance = Math.hypot(event.clientX - dragging.startX, event.clientY - dragging.startY);
    if (dragDistance < 6) {
      const point = findNearestPoint(event.clientX, event.clientY);
      if (point) {
        onSelectPoint(point.image_id);
      }
    }
  }

  return (
    <div className="galaxy-surface-wrap">
      <div className="galaxy-map-toolbar">
        <div className="galaxy-map-stats">
          <span>{points.length.toLocaleString()} points loaded</span>
          <span>{neighborIds.length ? `${neighborIds.length} neighbors highlighted` : "Hover for preview"}</span>
        </div>
        <div className="galaxy-map-controls">
          <button className="ghost-button" onClick={() => setView(viewFromBounds(bounds))}>
            Reset view
          </button>
          <button className="ghost-button" onClick={() => setDepthMode((value) => !value)}>
            {depthMode ? "Depth on" : "Depth off"}
          </button>
        </div>
      </div>

      <div
        ref={surfaceRef}
        className="galaxy-map-surface"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerLeave={handlePointerLeave}
        onWheel={handleWheel}
        role="presentation"
      >
        <canvas ref={canvasRef} />

        <div className="galaxy-map-legend">
          <span className="galaxy-legend-dot" />
          Morphology clusters
          <span className="galaxy-legend-dot galaxy-legend-dot--rare" />
          Rare objects
        </div>

        {hoverState ? (
          <div className="galaxy-hover-card" style={{ left: hoverState.x, top: hoverState.y }}>
            {hoverPreview?.image_url ? (
              <img src={hoverPreview.image_url} alt={hoverState.point.image_id} />
            ) : (
              <div className="galaxy-hover-card__placeholder">Loading preview...</div>
            )}
            <strong>{hoverState.point.predicted_class}</strong>
            <span>{hoverState.point.cluster_name}</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}

export default function GalaxyMap() {
  const requestRef = useRef(0);
  const hoverFetchRef = useRef(null);
  const [mapData, setMapData] = useState({
    total: 0,
    returned: 0,
    visible_clusters: [],
    bounds: {
      min_x: -10,
      max_x: 10,
      min_y: -6,
      max_y: 6,
      min_z: -2,
      max_z: 2
    },
    points: []
  });
  const [clusters, setClusters] = useState([]);
  const [loadingMap, setLoadingMap] = useState(true);
  const [mapError, setMapError] = useState("");
  const [selectedId, setSelectedId] = useState("");
  const [selectedDetail, setSelectedDetail] = useState(null);
  const [detailError, setDetailError] = useState("");
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [explanation, setExplanation] = useState("");
  const [loadingExplanation, setLoadingExplanation] = useState(false);
  const [hoveredPoint, setHoveredPoint] = useState(null);
  const [hoverCache, setHoverCache] = useState({});
  const [focusedCluster, setFocusedCluster] = useState(null);

  useEffect(() => {
    setLoadingMap(true);
    Promise.all([fetchGalaxyMap({ limit: 6000 }), fetchGalaxyClusters()])
      .then(([mapResponse, clusterResponse]) => {
        setMapData(mapResponse);
        setClusters(clusterResponse);
        setMapError("");
        if (mapResponse.points.length > 0) {
          setSelectedId(mapResponse.points[0].image_id);
        }
      })
      .catch((error) => setMapError(error.message))
      .finally(() => setLoadingMap(false));
  }, []);

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
          setHoverCache((cache) => ({
            ...cache,
            [hoveredPoint.image_id]: detail
          }));
        })
        .catch(() => undefined);
    }, 120);
    return () => window.clearTimeout(hoverFetchRef.current);
  }, [hoverCache, hoveredPoint]);

  function handleViewportChange(nextViewport) {
    requestRef.current += 1;
    const requestId = requestRef.current;
    const zoom = nextViewport.zoom || 1;
    const limit = zoom >= 2.4 ? 12000 : zoom >= 1.2 ? 8500 : 5000;
    fetchGalaxyMap({
      min_x: nextViewport.min_x,
      max_x: nextViewport.max_x,
      min_y: nextViewport.min_y,
      max_y: nextViewport.max_y,
      limit
    })
      .then((response) => {
        if (requestId === requestRef.current) {
          setMapData((previous) => ({
            ...response,
            bounds: previous.bounds
          }));
        }
      })
      .catch((error) => {
        if (requestId === requestRef.current) {
          setMapError(error.message);
        }
      });
  }

  function handleExploreCluster(cluster) {
    const nextCluster = clusters.find((item) => item.cluster_id === cluster.cluster_id) || cluster;
    setFocusedCluster({ ...nextCluster });
  }

  const neighborIds = selectedDetail?.nearest_neighbors?.map((neighbor) => neighbor.image_id) || [];
  const hoverPreview = hoveredPoint ? hoverCache[hoveredPoint.image_id] : null;
  const headlineCluster = focusedCluster || clusters[0];
  const visibleClusterCount = mapData.visible_clusters.length || clusters.length;

  return (
    <main className="single-column galaxy-page">
      <section className="panel panel--hero galaxy-hero">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">Galaxy Embedding Map</p>
            <h2>Google Maps for morphology space.</h2>
          </div>
          <div className="snapshot-grid galaxy-hero__stats">
            <article className="snapshot-card">
              <span>Galaxies loaded</span>
              <strong>{mapData.total.toLocaleString()}</strong>
              <p>Embedding points served from the API with viewport-aware sampling.</p>
            </article>
            <article className="snapshot-card">
              <span>Clusters visible</span>
              <strong>{visibleClusterCount}</strong>
              <p>Color-coded morphology families ready for cluster exploration.</p>
            </article>
            <article className="snapshot-card">
              <span>Rare objects</span>
              <strong>{clusters.find((cluster) => cluster.cluster_id === -1)?.count || "Live"}</strong>
              <p>Low-density outliers are highlighted for quick discovery demos.</p>
            </article>
          </div>
        </div>
        <p className="home-intro__lede">
          Pan through galaxy morphology space, dive into tight visual families, and open any point
          for its nearest neighbors, metadata, and a local-LLM explanation grounded in cluster
          context. The app reads a real Parquet artifact when available and falls back to a
          deterministic demo catalog so the module is always ready to show.
        </p>
        {headlineCluster ? (
          <div className="galaxy-headline-cluster">
            <span className="eyebrow">Featured cluster</span>
            <h3>{headlineCluster.cluster_name}</h3>
            <p>{headlineCluster.summary}</p>
          </div>
        ) : null}
      </section>

      <section className="galaxy-layout">
        <div className="galaxy-map-column">
          <section className="panel galaxy-map-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Interactive map</p>
                <h2>Explore the embedding manifold</h2>
              </div>
              <div className="galaxy-map-inline-stats">
                <span>{mapData.returned.toLocaleString()} rendered</span>
                <span>{loadingMap ? "Syncing view..." : "Live viewport queries"}</span>
              </div>
            </div>
            {mapError ? <p className="error-copy">{mapError}</p> : null}
            <MapCanvas
              points={mapData.points}
              bounds={mapData.bounds}
              selectedId={selectedId}
              neighborIds={neighborIds}
              focusedCluster={focusedCluster}
              hoverPreview={hoverPreview}
              onHoverPoint={setHoveredPoint}
              onSelectPoint={setSelectedId}
              onViewportChange={handleViewportChange}
            />
          </section>

          <section className="panel galaxy-cluster-panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">Explore cluster mode</p>
                <h2>Jump straight into the strongest structures</h2>
              </div>
            </div>
            <div className="galaxy-cluster-grid">
              {clusters.slice(0, 8).map((cluster) => (
                <button
                  key={cluster.cluster_id}
                  className={`galaxy-cluster-card${focusedCluster?.cluster_id === cluster.cluster_id ? " is-active" : ""}`}
                  onClick={() => handleExploreCluster(cluster)}
                >
                  <div>
                    <span className="galaxy-cluster-card__dot" style={{ background: clusterColor(cluster.cluster_id) }} />
                    <strong>{cluster.cluster_name}</strong>
                  </div>
                  <p>{cluster.summary}</p>
                  <span>{cluster.count.toLocaleString()} members</span>
                </button>
              ))}
            </div>
          </section>
        </div>

        <GalaxyDetailPanel
          detail={selectedDetail}
          explanation={explanation}
          loading={loadingDetail}
          loadingExplanation={loadingExplanation}
          error={detailError}
          onSelectGalaxy={setSelectedId}
          onExploreCluster={handleExploreCluster}
        />
      </section>
    </main>
  );
}
