import { inject, Injectable } from "@angular/core";
import { HttpClient } from "@angular/common/http";
import { firstValueFrom } from "rxjs";
import type { DashboardResponse } from "../../types";

@Injectable({
  providedIn: "root",
})
export class DashboardService {
  private readonly http = inject(HttpClient);

  async getDashboard(refreshFews = false): Promise<DashboardResponse> {
    const url = refreshFews
      ? "/api/dashboard?refreshFews=1"
      : "/api/dashboard";
    return firstValueFrom(this.http.get<DashboardResponse>(url));
  }
}
