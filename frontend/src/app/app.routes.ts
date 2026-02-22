// AnCapTruyenLamVideo - App Routes

import { Routes } from '@angular/router';
import { MangaCrawlerComponent } from './components/manga-crawler/manga-crawler.component';

export const routes: Routes = [
  { path: '', redirectTo: '/crawler', pathMatch: 'full' },
  { path: 'crawler', component: MangaCrawlerComponent },
  { path: '**', redirectTo: '/crawler' }
];
