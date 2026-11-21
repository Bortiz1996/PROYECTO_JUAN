import { inject, Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { firstValueFrom } from "rxjs";
import type { DashboardResponse } from "../../types";
import { buildStaticDashboard } from "../../utils/staticDashboard";

@Injectable({
  providedIn: "root",
})
export class DashboardService {
  private readonly http = inject(HttpClient);

  async getDashboard(refreshFews = false): Promise<DashboardResponse> {
    const isGitHubPages =
      typeof window !== "undefined" &&
      window.location.hostname.endsWith("github.io");

    if (isGitHubPages) {
      return buildStaticDashboard(refreshFews);
    }

    const url = refreshFews
      ? "api/dashboard?refreshFews=1"
      : "api/dashboard";

    try {
      const payload = await firstValueFrom(
        this.http.get<DashboardResponse>(url)
      );
      if (payload && Array.isArray(payload.records)) {
        return payload;
      }
    } catch {
      // Static hosting without /api/dashboard backend — fall back to static CSV + Open-Meteo.
    }

    return buildStaticDashboard(refreshFews);
  }
}
