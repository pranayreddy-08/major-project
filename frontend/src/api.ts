import type { SetupStatus, User } from "./types";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export async function login(username: string, password: string) {
  const body = new URLSearchParams({ username, password });
  const response = await fetch(`${API_URL}/api/v1/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!response.ok) {
    throw new ApiError(response.status, "The username or password was not accepted.");
  }
  return (await response.json()) as {
    access_token: string;
    token_type: "bearer";
    expires_in: number;
  };
}

export async function getSetupStatus() {
  const response = await fetch(`${API_URL}/api/v1/auth/setup-status`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) throw new ApiError(response.status, "Unable to check platform setup.");
  return (await response.json()) as SetupStatus;
}

export async function createInitialAdministrator(
  username: string,
  fullName: string,
  password: string,
) {
  const response = await fetch(`${API_URL}/api/v1/auth/setup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, full_name: fullName, password }),
  });
  if (!response.ok) {
    let message = "Unable to create the owner account.";
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail ?? message;
    } catch {
      // Keep the generic setup failure for non-JSON upstream responses.
    }
    throw new ApiError(response.status, message);
  }
  return (await response.json()) as {
    access_token: string;
    token_type: "bearer";
    expires_in: number;
  };
}

export async function api<T>(path: string, token: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_URL}/api/v1${path}`, {
    ...options,
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
      ...(options.body ? { "Content-Type": "application/json" } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      message = body.detail ?? message;
    } catch {
      // Keep the status-based message when an upstream returns a non-JSON error.
    }
    throw new ApiError(response.status, message);
  }
  return (await response.json()) as T;
}

export function getCurrentUser(token: string) {
  return api<User>("/auth/me", token);
}
