// AnCapTruyenLamVideo - Manga Crawler Component

import { Component, signal, computed, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';

import { InputTextModule } from 'primeng/inputtext';
import { ButtonModule } from 'primeng/button';
import { CardModule } from 'primeng/card';
import { ToastModule } from 'primeng/toast';
import { ProgressBarModule } from 'primeng/progressbar';
import { TagModule } from 'primeng/tag';
import { ScrollPanelModule } from 'primeng/scrollpanel';
import { MessageService } from 'primeng/api';

import { CrawlerService } from '../../services/crawler.service';
import { SseService } from '../../services/sse.service';
import { CrawlerTask, ProgressEvent, TaskStatus } from '../../models/crawler.model';

@Component({
  selector: 'app-manga-crawler',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    InputTextModule,
    ButtonModule,
    CardModule,
    ToastModule,
    ProgressBarModule,
    TagModule,
    ScrollPanelModule
  ],
  providers: [MessageService],
  templateUrl: './manga-crawler.component.html',
  styleUrl: './manga-crawler.component.scss'
})
export class MangaCrawlerComponent implements OnDestroy {
  // Signals for reactive state
  mangaUrl = signal('');
  isLoading = signal(false);
  currentTask = signal<CrawlerTask | null>(null);
  progressEvents = signal<ProgressEvent[]>([]);

  // Computed progress percentage
  overallProgress = computed(() => {
    const task = this.currentTask();
    if (!task) return 0;

    const totalChapters = Math.max(task.total_chapters, 1);
    const totalBatches = Math.max(task.total_batches, 1);

    // Weight: chapters 50%, AI batches 50%
    const chapterProgress = (task.chapters_crawled / totalChapters) * 50;
    const aiProgress = (task.batches_processed / totalBatches) * 50;

    return Math.round(chapterProgress + aiProgress);
  });

  // Status badge config
  statusConfig = computed(() => {
    const status = this.currentTask()?.status;
    switch (status) {
      case 'pending':
        return { severity: 'secondary' as const, label: 'Pending' };
      case 'crawling_chapters':
        return { severity: 'info' as const, label: 'Crawling Chapters' };
      case 'downloading_images':
        return { severity: 'info' as const, label: 'Downloading Images' };
      case 'processing_ai':
        return { severity: 'warn' as const, label: 'Processing AI' };
      case 'completed':
        return { severity: 'success' as const, label: 'Completed' };
      case 'failed':
        return { severity: 'danger' as const, label: 'Failed' };
      case 'cancelled':
        return { severity: 'secondary' as const, label: 'Cancelled' };
      default:
        return { severity: 'secondary' as const, label: 'Unknown' };
    }
  });

  private sseSubscription: Subscription | null = null;

  constructor(
    private crawlerService: CrawlerService,
    private sseService: SseService,
    private messageService: MessageService
  ) {}

  ngOnDestroy(): void {
    this.unsubscribeSSE();
  }

  /**
   * Start crawling the manga
   */
  startCrawl(): void {
    const url = this.mangaUrl().trim();

    if (!url) {
      this.messageService.add({
        severity: 'warn',
        summary: 'Warning',
        detail: 'Please enter a manga URL'
      });
      return;
    }

    // Validate URL format
    if (!url.includes('truyenqq')) {
      this.messageService.add({
        severity: 'error',
        summary: 'Error',
        detail: 'URL must be from truyenqqno.com'
      });
      return;
    }

    this.isLoading.set(true);
    this.progressEvents.set([]);
    this.currentTask.set(null);

    this.crawlerService.createTask({ manga_url: url }).subscribe({
      next: (task) => {
        this.currentTask.set(task);
        this.subscribeToTaskEvents(task._id);
        this.messageService.add({
          severity: 'success',
          summary: 'Success',
          detail: 'Crawl task started!'
        });
      },
      error: (err) => {
        this.isLoading.set(false);
        this.messageService.add({
          severity: 'error',
          summary: 'Error',
          detail: err.message || 'Failed to start crawl task'
        });
      }
    });
  }

  /**
   * Cancel the current crawl task
   */
  cancelCrawl(): void {
    const task = this.currentTask();
    if (!task) return;

    this.crawlerService.cancelTask(task._id).subscribe({
      next: () => {
        this.messageService.add({
          severity: 'info',
          summary: 'Cancelled',
          detail: 'Task cancelled'
        });
        this.isLoading.set(false);
        this.unsubscribeSSE();
      },
      error: (err) => {
        this.messageService.add({
          severity: 'error',
          summary: 'Error',
          detail: err.message || 'Failed to cancel task'
        });
      }
    });
  }

  /**
   * Download a script file
   */
  downloadScript(filename: string): void {
    const task = this.currentTask();
    if (!task) return;

    const url = this.crawlerService.getDownloadUrl(task._id, filename);
    window.open(url, '_blank');
  }

  /**
   * Subscribe to SSE events for a task
   */
  private subscribeToTaskEvents(taskId: string): void {
    this.unsubscribeSSE();

    this.sseSubscription = this.sseService.getTaskEvents(taskId).subscribe({
      next: (event) => {
        // Add event to log
        this.progressEvents.update(events => [...events, event]);

        // Update task data if provided
        if (event.data) {
          this.currentTask.update(task => {
            if (!task) return task;
            return { ...task, ...event.data };
          });
        }

        // Update status based on event
        if (event.event_type === 'task_completed') {
          this.currentTask.update(task => task ? { ...task, status: 'completed' as TaskStatus } : task);
          this.isLoading.set(false);
          this.messageService.add({
            severity: 'success',
            summary: 'Completed',
            detail: event.message
          });
        } else if (event.event_type === 'task_failed') {
          this.currentTask.update(task => task ? { ...task, status: 'failed' as TaskStatus } : task);
          this.isLoading.set(false);
          this.messageService.add({
            severity: 'error',
            summary: 'Failed',
            detail: event.message
          });
        }
      },
      error: (err) => {
        console.error('SSE Error:', err);
        this.isLoading.set(false);
        this.messageService.add({
          severity: 'warn',
          summary: 'Connection Lost',
          detail: 'Lost connection to server. Refresh to check status.'
        });
      },
      complete: () => {
        this.isLoading.set(false);
      }
    });
  }

  /**
   * Unsubscribe from SSE
   */
  private unsubscribeSSE(): void {
    if (this.sseSubscription) {
      this.sseSubscription.unsubscribe();
      this.sseSubscription = null;
    }
  }

  /**
   * Get file name from path
   */
  getFileName(path: string): string {
    return path.split('/').pop() || path;
  }
}
