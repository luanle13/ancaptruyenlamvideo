// AnCapTruyenLamVideo - App Routes

import { Routes } from '@angular/router';
import { StoriesComponent } from './components/stories/stories.component';

export const routes: Routes = [
  { path: '', redirectTo: '/stories', pathMatch: 'full' },
  { path: 'stories', component: StoriesComponent },
  { path: '**', redirectTo: '/stories' }
];
