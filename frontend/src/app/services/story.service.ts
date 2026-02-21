// AnCapTruyenLamVideo - Story Service

import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { Story, StoryCreate, StoryUpdate } from '../models/story.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class StoryService {
  private apiUrl = `${environment.apiBaseUrl}/stories`;

  constructor(private http: HttpClient) {}

  /**
   * Get all stories
   */
  getStories(): Observable<Story[]> {
    return this.http.get<Story[]>(this.apiUrl).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Get a single story by ID
   */
  getStory(id: string): Observable<Story> {
    return this.http.get<Story>(`${this.apiUrl}/${id}`).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Create a new story
   */
  createStory(story: StoryCreate): Observable<Story> {
    return this.http.post<Story>(this.apiUrl, story).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Update an existing story
   */
  updateStory(id: string, story: StoryUpdate): Observable<Story> {
    return this.http.put<Story>(`${this.apiUrl}/${id}`, story).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Delete a story
   */
  deleteStory(id: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`).pipe(
      catchError(this.handleError)
    );
  }

  /**
   * Handle HTTP errors
   */
  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An error occurred';

    if (error.error instanceof ErrorEvent) {
      // Client-side error
      errorMessage = error.error.message;
    } else {
      // Server-side error
      errorMessage = `Error Code: ${error.status}\nMessage: ${error.message}`;

      if (error.status === 0) {
        errorMessage = 'Cannot connect to the server. Please ensure the backend is running.';
      } else if (error.status === 404) {
        errorMessage = 'Resource not found';
      } else if (error.status === 500) {
        errorMessage = 'Internal server error';
      }
    }

    console.error('StoryService Error:', errorMessage);
    return throwError(() => new Error(errorMessage));
  }
}
