// AnCapTruyenLamVideo - YouTube Service

import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { environment } from '../../environments/environment';

export interface YouTubeStatus {
  enabled: boolean;
  authenticated: boolean;
  privacy: string;
}

export interface AuthUrlResponse {
  auth_url: string;
}

@Injectable({
  providedIn: 'root'
})
export class YouTubeService {
  private apiUrl = `${environment.apiBaseUrl}/youtube`;

  constructor(private http: HttpClient) {}

  /**
   * Get YouTube authentication status
   */
  getStatus(): Observable<YouTubeStatus> {
    return this.http.get<YouTubeStatus>(`${this.apiUrl}/status`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Start OAuth flow - get auth URL
   */
  startAuth(): Observable<AuthUrlResponse> {
    return this.http.get<AuthUrlResponse>(`${this.apiUrl}/auth/start`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Revoke YouTube credentials
   */
  revokeAuth(): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/auth/revoke`, {})
      .pipe(catchError(this.handleError));
  }

  /**
   * Handle HTTP errors
   */
  private handleError(error: HttpErrorResponse): Observable<never> {
    let errorMessage = 'An error occurred';

    if (error.error instanceof ErrorEvent) {
      errorMessage = error.error.message;
    } else {
      if (error.status === 500) {
        errorMessage = error.error?.detail || 'Server error';
      } else if (error.status === 0) {
        errorMessage = 'Cannot connect to server';
      } else {
        errorMessage = `Error: ${error.status}`;
      }
    }

    console.error('YouTubeService error:', errorMessage);
    return throwError(() => new Error(errorMessage));
  }
}
