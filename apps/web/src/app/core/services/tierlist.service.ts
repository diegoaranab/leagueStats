import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

import { DataManifest, Region, Tier, TierlistDataset, WindowKey } from '../models/tierlist.model';

@Injectable({
  providedIn: 'root',
})
export class TierlistService {
  constructor(private readonly http: HttpClient) {}

  getManifest(): Observable<DataManifest> {
    return this.http.get<DataManifest>('data/manifest.json');
  }

  getDataset(region: Region, tier: Tier, window: WindowKey): Observable<TierlistDataset> {
    return this.http.get<TierlistDataset>(`data/${region}/${tier}/${window}.json`);
  }
}
