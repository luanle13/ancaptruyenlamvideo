// AnCapTruyenLamVideo - Crawler Models

export type TaskStatus =
  | 'pending'
  | 'crawling_chapters'
  | 'downloading_images'
  | 'processing_ai'
  | 'completed'
  | 'failed'
  | 'cancelled';

export interface ChapterInfo {
  chapter_number: string;
  chapter_title: string;
  chapter_url: string;
  image_count: number;
  images_downloaded: boolean;
  ai_processed: boolean;
}

export interface CrawlerTask {
  _id: string;
  manga_url: string;
  manga_title?: string;
  status: TaskStatus;
  total_chapters: number;
  chapters_crawled: number;
  images_downloaded: number;
  total_images: number;
  batches_processed: number;
  total_batches: number;
  output_files: string[];
  error_message?: string;
  created_at: string;
  updated_at: string;
  completed_at?: string;
}

export interface CrawlerTaskCreate {
  manga_url: string;
}

export interface ProgressEvent {
  task_id: string;
  event_type: string;
  message: string;
  progress: number;
  data?: any;
}

export interface ContentFiles {
  files: string[];
}
