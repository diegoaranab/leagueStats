import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { DataManifest, Region, Tier, TierlistDataset, WindowKey } from '../models/tierlist.model';

@Injectable({
  providedIn: 'root',
})
export class TierlistService {
  constructor(private readonly http: HttpClient) {}

  buildManifestPath(): string {
    return '/data/manifest.json';
  }

  buildDatasetPath(region: Region, tier: Tier, window: WindowKey): string {
    return `/data/${region}/${tier}/${window}.json`;
  }

  getManifest(): Observable<DataManifest> {
    return this.http.get<DataManifest>(this.buildManifestPath());
  }

  getDataset(region: Region, tier: Tier, window: WindowKey): Observable<TierlistDataset> {
    return this.http.get<TierlistDataset>(this.buildDatasetPath(region, tier, window));
  }
}
