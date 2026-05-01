const JSON_HEADERS = {
  Accept: "application/json"
};

const JSON_POST_HEADERS = {
  ...JSON_HEADERS,
  "Content-Type": "application/json"
};

async function request(path) {
  const response = await fetch(path, { headers: JSON_HEADERS });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed for ${path}`);
  }
  return response.json();
}

async function postRequest(path, payload) {
  const response = await fetch(path, {
    method: "POST",
    headers: JSON_POST_HEADERS,
    body: JSON.stringify(payload)
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed for ${path}`);
  }
  return response.json();
}

export function fetchTransients() {
  return request("/api/transients?limit=24");
}

export function fetchTransientDetail(candidateId) {
  return request(`/api/transients/${candidateId}`);
}

export function fetchTransientReport() {
  return request("/api/transients/reports/latest");
}

export function fetchTessCandidates() {
  return request("/api/candidates?limit=8");
}

function toQueryString(params) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, String(value));
    }
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

export function fetchGalaxyMap(params = {}) {
  return request(`/api/galaxies${toQueryString(params)}`);
}

export function fetchGalaxyMapManifest() {
  return request("/api/galaxy-map/manifest");
}

export function fetchGalaxyDetail(imageId) {
  return request(`/api/galaxy/${imageId}`);
}

export function fetchGalaxyClusters() {
  return request("/api/clusters");
}

export function fetchGalaxyExplanation(imageId) {
  return request(`/api/explain/${imageId}`);
}

export function fetchSkyFeed(params = {}) {
  return request(`/api/events/personalized${toQueryString(params)}`);
}

export function fetchSkyEventDetail(eventId, params = {}) {
  return request(`/api/events/${eventId}${toQueryString(params)}`);
}

export function fetchSkyEventExplanation(eventId, params = {}) {
  return request(`/api/events/${eventId}/explain${toQueryString(params)}`);
}

export function fetchExoplanetDemoTargets() {
  return request("/api/exoplanet/demo-targets");
}

export function startExoplanetAnalysis(payload) {
  return postRequest("/api/exoplanet/analyze", payload);
}

export function fetchExoplanetStatus(jobId) {
  return request(`/api/exoplanet/status/${jobId}`);
}

export function fetchExoplanetResult(jobId) {
  return request(`/api/exoplanet/result/${jobId}`);
}

export function fetchExoplanetReport(jobId) {
  return request(`/api/exoplanet/report/${jobId}`);
}
