// AnCapTruyenLamVideo - SSE Service

import { Injectable, NgZone } from '@angular/core';
import { Observable } from 'rxjs';
import { ProgressEvent } from '../models/crawler.model';
import { environment } from '../../environments/environment';

@Injectable({
  providedIn: 'root'
})
export class SseService {
  constructor(private zone: NgZone) {}

  /**
   * Connect to SSE endpoint for task progress events
   */
  getTaskEvents(taskId: string): Observable<ProgressEvent> {
    return new Observable(observer => {
      const url = `${environment.apiBaseUrl}/crawler/tasks/${taskId}/events`;
      const eventSource = new EventSource(url);

      // List of event types to listen for
      const eventTypes = [
        'task_started',
        'chapters_found',
        'chapter_crawled',
        'image_downloaded',
        'batch_processing',
        'batch_completed',
        'video_generating',
        'video_progress',
        'video_completed',
        'task_completed',
        'task_failed',
        'progress_update',
        'keepalive'
      ];

      // Add listener for each event type
      eventTypes.forEach(type => {
        eventSource.addEventListener(type, (event: MessageEvent) => {
          this.zone.run(() => {
            try {
              if (type === 'keepalive') {
                // Ignore keepalive events
                return;
              }

              const data = JSON.parse(event.data) as ProgressEvent;
              observer.next(data);

              // Close connection on terminal events
              if (type === 'task_completed' || type === 'task_failed') {
                eventSource.close();
                observer.complete();
              }
            } catch (e) {
              console.error('Error parsing SSE event:', e);
            }
          });
        });
      });

      // Handle errors
      eventSource.onerror = (error) => {
        this.zone.run(() => {
          console.error('SSE Error:', error);
          eventSource.close();
          observer.error(new Error('Connection lost'));
        });
      };

      // Cleanup on unsubscribe
      return () => {
        eventSource.close();
      };
    });
  }
}
