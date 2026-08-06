const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ApiOptions extends Omit<RequestInit, "body"> {
  body?: any;
  token?: string | null;
  isFormData?: boolean;
}

async function apiFetch<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
  const { token, body, isFormData, ...customConfig } = options;
  const headers: HeadersInit = {
    ...customConfig.headers,
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  if (body && !isFormData) {
    headers["Content-Type"] = "application/json";
  }

  const config: RequestInit = {
    ...customConfig,
    headers,
  };

  if (body) {
    config.body = isFormData ? body : JSON.stringify(body);
  }

  const res = await fetch(`${API_URL}${endpoint}`, config);
  
  if (!res.ok) {
    let errorDetail = `HTTP ${res.status}`;
    try {
      const errData = await res.json();
      errorDetail = errData.detail ?? errorDetail;
    } catch {
      // Ignore JSON parse errors for error responses
    }
    throw new Error(errorDetail);
  }

  return res.json() as Promise<T>;
}

// Intake API
export const apiIntakeDocument = (file: File) => {
  const fd = new FormData();
  fd.append("file", file);
  return apiFetch<any>("/api/intake/document", {
    method: "POST",
    body: fd,
    isFormData: true,
  });
};

export const apiIntakeScenario = (scenarioData: any) => {
  return apiFetch<any>("/api/intake/scenario", {
    method: "POST",
    body: scenarioData,
  });
};

// Structures API
export const apiStructuresGenerate = (scenario: any, max_alternatives = 3, token?: string | null) => {
  return apiFetch<any>("/api/structures/generate", {
    method: "POST",
    body: { scenario, max_alternatives },
    token,
  });
};

// Compliance API
export const apiComplianceEvaluate = (scenario: any, proposed_structure: any) => {
  return apiFetch<any>("/api/compliance/evaluate", {
    method: "POST",
    body: { scenario, proposed_structure },
  });
};

// Diagram API
export const apiDiagramGenerate = (structure_json: any) => {
  return apiFetch<any>("/api/diagram/generate", {
    method: "POST",
    body: { structure_json },
  });
};

// Review API
export const apiReviewQueueList = (limit: number = 100, token?: string | null) => {
  return apiFetch<any[]>(`/api/review/queue?limit=${limit}`, {
    method: "GET",
    token,
  });
};

export const apiReviewAction = (data: any, token?: string | null) => {
  return apiFetch<any>("/api/review/action", {
    method: "POST",
    body: data,
    token,
  });
};

export const apiReviewCorrection = (data: any, token?: string | null) => {
  return apiFetch<any>("/api/review/correction", {
    method: "POST",
    body: data,
    token,
  });
};
