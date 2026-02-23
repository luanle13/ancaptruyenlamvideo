// AnCapTruyenLamVideo - Crawler Service

import { Injectable } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { CrawlerTask, CrawlerTaskCreate, ContentFiles } from '../models/crawler.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class CrawlerService {
  private apiUrl = `${environment.apiBaseUrl}/crawler`;

  constructor(private http: HttpClient) {}

  /**
   * Create and start a new crawl task
   */
  createTask(task: CrawlerTaskCreate): Observable<CrawlerTask> {
    return this.http.post<CrawlerTask>(`${this.apiUrl}/tasks`, task)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get all crawl tasks
   */
  getTasks(): Observable<CrawlerTask[]> {
    return this.http.get<CrawlerTask[]>(`${this.apiUrl}/tasks`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get a specific task by ID
   */
  getTask(id: string): Observable<CrawlerTask> {
    return this.http.get<CrawlerTask>(`${this.apiUrl}/tasks/${id}`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Cancel a running task
   */
  cancelTask(id: string): Observable<{ message: string }> {
    return this.http.post<{ message: string }>(`${this.apiUrl}/tasks/${id}/cancel`, {})
      .pipe(catchError(this.handleError));
  }

  /**
   * Get list of generated script files for a task
   */
  getTaskContent(id: string): Observable<ContentFiles> {
    return this.http.get<ContentFiles>(`${this.apiUrl}/content/${id}`)
      .pipe(catchError(this.handleError));
  }

  /**
   * Get download URL for a script file
   */
  getDownloadUrl(taskId: string, filename: string): string {
    return `${this.apiUrl}/content/${taskId}/${filename}`;
  }

  /**
   * Get download URL for a video file
   */
  getVideoUrl(taskId: string, filename: string): string {
    return `${this.apiUrl}/videos/${taskId}/${filename}`;
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
      if (error.status === 400) {
        errorMessage = error.error?.detail || 'Invalid request';
      } else if (error.status === 404) {
        errorMessage = 'Task not found';
      } else if (error.status === 0) {
        errorMessage = 'Cannot connect to server';
      } else {
        errorMessage = `Server error: ${error.status}`;
      }
    }

    console.error('CrawlerService error:', errorMessage);
    return throwError(() => new Error(errorMessage));
  }
}
