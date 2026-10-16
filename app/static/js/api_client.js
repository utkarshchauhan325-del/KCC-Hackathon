/**
 * FloodGuard CivicEye API Client
 * Connects the frontend to FastAPI backend endpoints.
 */

const ApiClient = {
  baseUrl: "/api/v1",

  async getIncidents(params = {}) {
    try {
      const url = new URL(`${window.location.origin}${this.baseUrl}/incidents`);
      Object.keys(params).forEach(k => {
        if (params[k]) url.searchParams.append(k, params[k]);
      });
      const res = await fetch(url.toString());
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn("API fallback to local data:", err);
      return null;
    }
  },

  async getStats() {
    try {
      const res = await fetch(`${this.baseUrl}/stats`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn("Stats API fallback:", err);
      return null;
    }
  },

  async dispatchCrew(incidentId, crewUnit, notes = "") {
    try {
      const res = await fetch(`${this.baseUrl}/dispatch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ incident_id: incidentId, crew_unit: crewUnit, notes })
      });
      return await res.json();
    } catch (err) {
      console.error("Dispatch failed:", err);
      return { status: "ERROR", message: err.message };
    }
  },

  async resolveIncident(incidentId, notes = "") {
    try {
      const res = await fetch(`${this.baseUrl}/resolve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ incident_id: incidentId, notes })
      });
      return await res.json();
    } catch (err) {
      console.error("Resolve failed:", err);
      return { status: "ERROR", message: err.message };
    }
  }
};
