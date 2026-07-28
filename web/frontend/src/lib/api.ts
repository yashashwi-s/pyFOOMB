const BASE_URL = 'http://localhost:8000/api';

/** Loosely-typed JSON request body — payload shapes vary per endpoint and
 * are validated server-side by the FastAPI/pydantic layer. */
type JsonPayload = Record<string, unknown>;

async function fetcher(endpoint: string, options: RequestInit = {}) {
  const response = await fetch(`${BASE_URL}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  if (!response.ok) {
    let message = 'An error occurred';
    try {
      const errorData = await response.json();
      message = errorData.detail || errorData.message || message;
    } catch {
      message = response.statusText;
    }
    throw new Error(message);
  }
  return response.json();
}

export const api = {
  health: () => fetcher('/health'),
  getTemplates: () => fetcher('/templates'),
  createModel: (payload: JsonPayload) => fetcher('/models', { method: 'POST', body: JSON.stringify(payload) }),
  getModels: () => fetcher('/models'),
  getModel: (id: string) => fetcher(`/models/${id}`),
  deleteModel: (id: string) => fetcher(`/models/${id}`, { method: 'DELETE' }),
  
  getMeasurements: (id: string) => fetcher(`/models/${id}/measurements`),
  clearMeasurements: (id: string) => fetcher(`/models/${id}/measurements`, { method: 'DELETE' }),
  addMeasurements: (id: string, payload: JsonPayload) => fetcher(`/models/${id}/measurements`, { method: 'POST', body: JSON.stringify(payload) }),
  pasteMeasurements: (id: string, text: string) => fetcher(`/models/${id}/measurements/paste`, { method: 'POST', body: JSON.stringify({ text }) }),
  importGoogleSheets: (id: string, url: string) => fetcher(`/models/${id}/measurements/sheets`, { method: 'POST', body: JSON.stringify({ url }) }),
  uploadMeasurementFile: async (id: string, file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await fetch(`${BASE_URL}/models/${id}/measurements/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!response.ok) {
        let message = 'An error occurred';
        try {
          const errorData = await response.json();
          message = errorData.detail || errorData.message || message;
        } catch {
          message = response.statusText;
        }
        throw new Error(message);
    }
    return response.json();
  },
  generateData: (id: string, payload: JsonPayload) => fetcher(`/models/${id}/generate-data`, { method: 'POST', body: JSON.stringify(payload) }),
  
  simulate: (id: string, payload: JsonPayload) => fetcher(`/models/${id}/simulate`, { method: 'POST', body: JSON.stringify(payload) }),
  estimate: (id: string, payload: JsonPayload) => fetcher(`/models/${id}/estimate`, { method: 'POST', body: JSON.stringify(payload) }),
  
  getSensitivities: (id: string, payload: JsonPayload) => fetcher(`/models/${id}/sensitivities`, { method: 'POST', body: JSON.stringify(payload) }),
  getParameterMatrices: (id: string, payload: JsonPayload) => fetcher(`/models/${id}/parameter-matrices`, { method: 'POST', body: JSON.stringify(payload) }),
  
  getReplicates: (id: string) => fetcher(`/models/${id}/replicates`),
  getParameters: (id: string) => fetcher(`/models/${id}/parameters`),
  addReplicate: (id: string, newRepId: string) => fetcher(`/models/${id}/replicates`, { method: 'POST', body: JSON.stringify({ replicate_id: newRepId }) }),
  applyMappings: (id: string, formatted: JsonPayload[]) => fetcher(`/models/${id}/mappings`, { method: 'POST', body: JSON.stringify(formatted) }),
  setIntegrator: (id: string, kwargs: JsonPayload) => fetcher(`/models/${id}/integrator`, { method: 'PUT', body: JSON.stringify(kwargs) }),
};
