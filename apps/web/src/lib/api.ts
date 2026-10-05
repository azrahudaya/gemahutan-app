import type { components } from "@/lib/api-types";

// String kosong (produksi) berarti API di domain yang sama lewat Caddy; hanya undefined yang jatuh ke localhost.
const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Schemas = components["schemas"];

// Tipe lokal untuk endpoint yang tidak punya schema terpisah di OpenAPI
// (di-generate sebagai application/json: unknown). Bentuknya diambil dari
// app/routers/detections.py, spectrogram.py, dan services/model_status.py.
export type JobStatus = "pending" | "running" | "done" | "failed";

export interface JobItem {
  id: number;
  recording_id: number;
  status: JobStatus;
  progress: number;
  stage: string | null;
  attempts: number;
  last_error: string | null;
  started_at: string | null;
  finished_at: string | null;
}

export interface SimulasiArahAlat {
  x: number;
  y: number;
  azimuth_deg: number | null;
  keyakinan: number | null;
  azimuth_kembar: number[];
  jarak_estimasi_m: number | null;
}

export interface SimulasiLokasiResponse {
  arah: SimulasiArahAlat[];
  perkiraan: [number, number] | null;
  radius_area_m: number | null;
  galat_m: number | null;
  sumber: [number, number];
  jumlah_alat: number;
  sinkron: boolean;
  catatan: string;
}

export interface StatsOverview {
  recordings: number;
  detections: number;
  species_detected: number;
  sites: number;
}

export interface StatsSpeciesItem {
  scientific_name: string;
  common_name: string | null;
  count: number;
}

export interface StatsTimelineItem {
  date: string;
  detections: number;
}

export interface AcousticIndices {
  recording_id: number;
  aci: number | null;
  ndsi: number | null;
  adi: number | null;
  bi: number | null;
  computed_at: string | null;
  caveat: string;
}

export interface ModelTrack {
  id: string;
  name: string;
  version?: string;
  species_count?: number;
  role?: string;
  loaded_by_worker?: boolean;
  checkpoint_in_api_image?: boolean;
  checkpoint_sha256?: string | null;
  epoch?: number;
  best_val_acc?: number;
  macro_f1?: number;
  notes?: string;
}

export interface ModelInfo {
  engine: string;
  status: string;
  status_detail: string;
  worker_alive: boolean;
  tracks: ModelTrack[];
  thresholds_loaded: number;
  thresholds: Record<string, number>;
  worker_heartbeat_age_s: number | null;
  metrics?: Record<string, unknown>;
  limits?: string[];
  warning?: string;
  localization?: Record<string, unknown>;
}

class ApiClient {
  private _refreshPromise: Promise<boolean> | null = null;

  private getToken(): string | null {
    if (typeof window === "undefined") return null;
    return localStorage.getItem("access_token");
  }

  private async _tryRefresh(): Promise<boolean> {
    // Hindari banyak panggilan refresh bersamaan.
    if (this._refreshPromise) return this._refreshPromise;

    const refreshToken = typeof window !== "undefined"
      ? localStorage.getItem("refresh_token")
      : null;
    if (!refreshToken) return false;

    this._refreshPromise = (async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/auth/refresh`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) return false;
        const data = (await res.json()) as Schemas["TokenResponse"];
        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);
        return true;
      } catch {
        return false;
      } finally {
        this._refreshPromise = null;
      }
    })();
    return this._refreshPromise;
  }

  private async request<T>(
    path: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData)) {
      headers["Content-Type"] = "application/json";
    }

    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
    });

    // 401 dari /auth/* (sandi salah, tautan kedaluwarsa) adalah jawaban biasa, bukan sesi habis:
    // jangan refresh atau alihkan ke /login supaya pesan galatnya sampai ke formulir.
    if (res.status === 401 && !path.startsWith("/api/v1/auth/")) {
      // Coba refresh token dulu. Kalau berhasil, ulangi permintaan sekali.
      const refreshed = await this._tryRefresh();
      if (refreshed) {
        const token = this.getToken();
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }
        const retryRes = await fetch(`${API_BASE}${path}`, {
          ...options,
          headers,
        });
        if (retryRes.ok || retryRes.status !== 401) {
          // Lanjutkan pemrosesan hasil retryRes di bawah.
          Object.assign(res, {
            status: retryRes.status,
            ok: retryRes.ok,
            headers: retryRes.headers,
            json: retryRes.json.bind(retryRes),
            blob: retryRes.blob.bind(retryRes),
            text: retryRes.text.bind(retryRes),
            arrayBuffer: retryRes.arrayBuffer.bind(retryRes),
            body: retryRes.body,
          });
        } else {
          // Refresh berhasil tapi tetap 401: token versi lama, sandi ganti.
          if (typeof window !== "undefined") {
            localStorage.removeItem("access_token");
            localStorage.removeItem("refresh_token");
            window.location.href = "/login";
          }
          throw new Error("Unauthorized");
        }
      } else {
        // Refresh gagal: token sudah dicabut atau tidak valid.
        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/login";
        }
        throw new Error("Unauthorized");
      }
    }

    if (!res.ok) {
      const body = (await res.json().catch(() => ({}))) as { detail?: string };
      throw new Error(body.detail || `Request failed: ${res.status}`);
    }

    if (res.headers.get("content-type")?.includes("image/")) {
      return res.blob() as unknown as T;
    }

    if (res.status === 204) {
      return undefined as T;
    }

    return res.json() as Promise<T>;
  }

  // Auth
  async login(email: string, password: string) {
    return this.request<Schemas["TokenResponse"]>(
      "/api/v1/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) }
    );
  }

  async register(data: { name: string; email: string; password: string }) {
    // Daftar mengembalikan UserResponse. Klien harus memanggil login() setelahnya.
    return this.request<Schemas["UserResponse"]>(
      "/api/v1/auth/register",
      { method: "POST", body: JSON.stringify(data) }
    );
  }

  async forgotPassword(email: string) {
    return this.request<{ message: string }>("/api/v1/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  }

  async resetPassword(token: string, password: string) {
    return this.request<{ message: string; sessions_revoked?: boolean }>(
      "/api/v1/auth/reset-password",
      { method: "POST", body: JSON.stringify({ token, password }) }
    );
  }

  async activateAccount(token: string, password: string) {
    return this.request<{ message: string }>("/api/v1/auth/aktivasi", {
      method: "POST",
      body: JSON.stringify({ token, password }),
    });
  }

  async logout(refreshToken?: string | null) {
    // Refresh token dikirim supaya server ikut mencabutnya, bukan hanya
    // access token yang sedang dipakai.
    return this.request<void>("/api/v1/auth/logout", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken ?? null }),
    });
  }

  async getMe() {
    return this.request<Schemas["UserResponse"]>("/api/v1/me");
  }

  // Recordings
  async getRecordings(params?: Record<string, string>) {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<Schemas["RecordingListResponse"]>(`/api/v1/recordings${qs}`);
  }

  async getRecording(id: string) {
    return this.request<Schemas["RecordingResponse"]>(`/api/v1/recordings/${id}`);
  }

  async getDetections(id: string) {
    return this.request<Schemas["DetectionResponse"][]>(`/api/v1/recordings/${id}/detections`);
  }

  async updateRecording(id: string, data: Record<string, unknown>) {
    return this.request<Schemas["RecordingResponse"]>(`/api/v1/recordings/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteRecording(id: string) {
    return this.request<void>(`/api/v1/recordings/${id}`, { method: "DELETE" });
  }

  async getSpectrogram(id: string) {
    return this.request<Blob>(`/api/v1/recordings/${id}/spectrogram`);
  }

  async getIndices(id: string) {
    return this.request<AcousticIndices>(`/api/v1/recordings/${id}/indices`);
  }

  async uploadRecording(
    formData: FormData,
    onProgress?: (pct: number) => void
  ): Promise<Schemas["RecordingResponse"]> {
    const token = this.getToken();
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE}/api/v1/recordings`);
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText) as Schemas["RecordingResponse"]);
        } else {
          reject(new Error(xhr.responseText || `Upload failed: ${xhr.status}`));
        }
      };
      xhr.onerror = () => reject(new Error("Upload failed"));
      xhr.send(formData);
    });
  }

  // Stats
  async getStatsOverview() {
    return this.request<StatsOverview>("/api/v1/stats/overview");
  }

  async getStatsSpecies() {
    return this.request<StatsSpeciesItem[]>("/api/v1/stats/species");
  }

  async getStatsTimeline() {
    return this.request<StatsTimelineItem[]>("/api/v1/stats/timeline");
  }

  // Sites
  async getSites(params?: Record<string, string>) {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<Schemas["SiteResponse"][]>(`/api/v1/sites${qs}`);
  }

  async getSite(id: string) {
    return this.request<Schemas["SiteResponse"]>(`/api/v1/sites/${id}`);
  }

  async createSite(data: Record<string, string>) {
    return this.request<Schemas["SiteResponse"]>("/api/v1/sites", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateSite(id: string, data: Record<string, unknown>) {
    return this.request<Schemas["SiteResponse"]>(`/api/v1/sites/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteSite(id: string) {
    return this.request<void>(`/api/v1/sites/${id}`, { method: "DELETE" });
  }

  // Species
  async getSpeciesList() {
    return this.request<Schemas["SpeciesResponse"][]>("/api/v1/species");
  }

  async getSpecies(id: string) {
    return this.request<Schemas["SpeciesResponse"]>(`/api/v1/species/${id}`);
  }

  async setSpeciesPrioritas(id: number, prioritas: boolean) {
    return this.request<Schemas["SpeciesResponse"]>(`/api/v1/species/${id}/prioritas`, {
      method: "PATCH",
      body: JSON.stringify({ prioritas }),
    });
  }

  async getSpeciesDetections(id: string, limit = 50) {
    return this.request<Schemas["DetectionResponse"][]>(`/api/v1/species/${id}/detections?limit=${limit}`);
  }

  // Detections
  async verifyDetection(detectionId: number, status: string) {
    return this.request<Schemas["DetectionResponse"]>(`/api/v1/detections/${detectionId}/verify`, {
      method: "POST",
      body: JSON.stringify({ status }),
    });
  }

  // Audio
  getAudioUrl(recordingId: string): string {
    const token = this.getToken();
    return `${API_BASE}/api/v1/recordings/${recordingId}/audio${token ? `?token=${token}` : ""}`;
  }

  // Ekspor data
  exportUrl(path: "verified" | "recordings", params?: Record<string, string>) {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return `${API_BASE}/api/v1/exports/${path}${qs}`;
  }

  async downloadExport(path: "verified" | "recordings", params?: Record<string, string>) {
    const token = this.getToken();
    const res = await fetch(this.exportUrl(path, params), {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!res.ok) throw new Error(`Ekspor gagal: ${res.status}`);
    return res.blob();
  }

  // Jobs
  async getJobs(params?: number | Record<string, string>) {
    if (typeof params === "number") {
      return this.request<JobItem[]>(`/api/v1/jobs?recording_id=${params}`);
    }
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<JobItem[]>(`/api/v1/jobs${qs}`);
  }

  async retryJob(jobId: number) {
    return this.request<JobItem>(`/api/v1/jobs/${jobId}/retry`, { method: "POST" });
  }

  /** Siaran status job. Token lewat query karena EventSource tidak bisa kirim header. */
  jobStreamUrl(): string {
    const token = this.getToken();
    return `${API_BASE}/api/v1/jobs/stream${token ? `?token=${token}` : ""}`;
  }

  // Perangkat
  async getDevices(params?: Record<string, string>) {
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<Schemas["DeviceResponse"][]>(`/api/v1/devices${qs}`);
  }

  async getDevicesPilihan(params?: Record<string, string>) {
    // Daftar singkat perangkat untuk dipilih ranger saat rekam/unggah.
    const qs = params ? "?" + new URLSearchParams(params).toString() : "";
    return this.request<{ id: number; name: string; site_id: number; site_name: string | null; channel_count: number; active: boolean }[]>(`/api/v1/devices/pilihan${qs}`);
  }

  async createDevice(data: Record<string, unknown>) {
    return this.request<Schemas["DeviceResponse"]>("/api/v1/devices", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async updateDevice(id: number, data: Record<string, unknown>) {
    return this.request<Schemas["DeviceResponse"]>(`/api/v1/devices/${id}`, {
      method: "PATCH",
      body: JSON.stringify(data),
    });
  }

  async deleteDevice(id: number) {
    return this.request<void>(`/api/v1/devices/${id}`, { method: "DELETE" });
  }

  // Simulasi perkiraan lokasi (blok K)
  async simulasiLokasi(data: Record<string, unknown>) {
    return this.request<SimulasiLokasiResponse>("/api/v1/simulasi/lokasi", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  // Akun (admin)
  async getUsers() {
    return this.request<Schemas["UserListResponse"]>("/api/v1/users");
  }

  async updateUserRole(id: number, role: string) {
    return this.request<Schemas["UserResponse"]>(`/api/v1/users/${id}/role`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    });
  }

  async deleteUser(id: number) {
    return this.request<void>(`/api/v1/users/${id}`, { method: "DELETE" });
  }

  async undangUser(data: { email: string; name?: string; role: string }) {
    return this.request<Schemas["UserListResponse"]>("/api/v1/users/undang", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  async resendInvite(userId: number) {
    return this.request<Schemas["UserListResponse"]>(
      `/api/v1/users/${userId}/undang-ulang`,
      { method: "POST" }
    );
  }

  // Unggah batch
  async uploadRecordingBatch(
    formData: FormData,
    onProgress?: (pct: number) => void
  ): Promise<Schemas["BatchUploadResponse"]> {
    const token = this.getToken();
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("POST", `${API_BASE}/api/v1/recordings/batch`);
      if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);

      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable && onProgress) {
          onProgress(Math.round((e.loaded / e.total) * 100));
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          resolve(JSON.parse(xhr.responseText) as Schemas["BatchUploadResponse"]);
        } else {
          let pesan = `Unggah batch gagal: ${xhr.status}`;
          try {
            const body = JSON.parse(xhr.responseText) as { detail?: string };
            pesan = body.detail || pesan;
          } catch {
            /* biarkan pesan bawaan */
          }
          reject(new Error(pesan));
        }
      };
      xhr.onerror = () => reject(new Error("Unggah batch gagal: jaringan"));
      xhr.send(formData);
    });
  }

  async getBatches() {
    return this.request<Schemas["BatchUploadResponse"][]>("/api/v1/batches");
  }

  async getBatch(id: string) {
    return this.request<Schemas["BatchDetailResponse"]>(`/api/v1/batches/${id}`);
  }

  // Model info
  async getModelInfo() {
    return this.request<ModelInfo>("/api/v1/model/info");
  }
}

export const api = new ApiClient();
