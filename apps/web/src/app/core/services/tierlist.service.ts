import { HttpClient } from '@angular/common/http';
import { DOCUMENT } from '@angular/common';
import { Inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { DataManifest, Region, Tier, TierlistDataset, WindowKey } from '../models/tierlist.model';

@Injectable({
  providedIn: 'root',
})
export class TierlistService {
  constructor(
    private readonly http: HttpClient,
    @Inject(DOCUMENT) private readonly document: Document,
  ) {}

  buildAssetUrl(relativePath: string): string {
    const cleanPath = relativePath.replace(/^\/+/, '');
    return new URL(cleanPath, this.document.baseURI).toString();
  }

  buildManifestPath(): string {
    return this.buildAssetUrl('data/manifest.json');
  }

  buildDatasetPath(region: Region, tier: Tier, window: WindowKey): string {
    return this.buildAssetUrl(`data/${region}/${tier}/${window}.json`);
  }

  buildTeamplayDatasetPath(region: Region, tier: Tier, window: WindowKey): string {
    return this.buildAssetUrl(`data/teamplay/${region}/${tier}/${window}.json`);
  }

  getManifest(): Observable<DataManifest> {
    return this.http.get<DataManifest>(this.buildManifestPath());
  }

  getDataset(region: Region, tier: Tier, window: WindowKey): Observable<TierlistDataset> {
    return this.http.get<TierlistDataset>(this.buildDatasetPath(region, tier, window));
  }

  getTeamplayDataset(region: Region, tier: Tier, window: WindowKey): Observable<TierlistDataset> {
    return this.http.get<TierlistDataset>(this.buildTeamplayDatasetPath(region, tier, window));
  }
}
