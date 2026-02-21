// AnCapTruyenLamVideo - Stories Component

import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TableModule } from 'primeng/table';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { InputTextModule } from 'primeng/inputtext';
import { TextareaModule } from 'primeng/textarea';
import { SelectModule } from 'primeng/select';
import { ToastModule } from 'primeng/toast';
import { ConfirmDialogModule } from 'primeng/confirmdialog';
import { ToolbarModule } from 'primeng/toolbar';
import { TagModule } from 'primeng/tag';
import { ProgressSpinnerModule } from 'primeng/progressspinner';
import { MessageService, ConfirmationService } from 'primeng/api';

import { Story, StoryCreate } from '../../models/story.model';
import { StoryService } from '../../services/story.service';

interface StatusOption {
  label: string;
  value: 'draft' | 'published' | 'archived';
}

@Component({
  selector: 'app-stories',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    TableModule,
    ButtonModule,
    DialogModule,
    InputTextModule,
    TextareaModule,
    SelectModule,
    ToastModule,
    ConfirmDialogModule,
    ToolbarModule,
    TagModule,
    ProgressSpinnerModule
  ],
  providers: [MessageService, ConfirmationService],
  templateUrl: './stories.component.html',
  styleUrl: './stories.component.scss'
})
export class StoriesComponent implements OnInit {
  // Signals for reactive state management
  stories = signal<Story[]>([]);
  loading = signal<boolean>(false);
  storyDialog = signal<boolean>(false);
  submitted = signal<boolean>(false);

  // Current story being edited/created
  story: Story = this.getEmptyStory();

  // Status options for dropdown
  statusOptions: StatusOption[] = [
    { label: 'Draft', value: 'draft' },
    { label: 'Published', value: 'published' },
    { label: 'Archived', value: 'archived' }
  ];

  // Computed signal for dialog title
  dialogTitle = computed(() => this.story._id ? 'Edit Story' : 'New Story');

  constructor(
    private storyService: StoryService,
    private messageService: MessageService,
    private confirmationService: ConfirmationService
  ) {}

  ngOnInit(): void {
    this.loadStories();
  }

  private getEmptyStory(): Story {
    return {
      title: '',
      description: '',
      author: '',
      status: 'draft'
    };
  }

  loadStories(): void {
    this.loading.set(true);
    this.storyService.getStories().subscribe({
      next: (data) => {
        this.stories.set(data);
        this.loading.set(false);
      },
      error: (error) => {
        this.messageService.add({
          severity: 'error',
          summary: 'Error',
          detail: 'Failed to load stories. Please check if the backend is running.',
          life: 5000
        });
        this.loading.set(false);
        console.error('Error loading stories:', error);
      }
    });
  }

  openNew(): void {
    this.story = this.getEmptyStory();
    this.submitted.set(false);
    this.storyDialog.set(true);
  }

  editStory(story: Story): void {
    this.story = { ...story };
    this.storyDialog.set(true);
  }

  deleteStory(story: Story): void {
    this.confirmationService.confirm({
      message: `Are you sure you want to delete "${story.title}"?`,
      header: 'Confirm Delete',
      icon: 'pi pi-exclamation-triangle',
      acceptButtonStyleClass: 'p-button-danger',
      accept: () => {
        if (story._id) {
          this.storyService.deleteStory(story._id).subscribe({
            next: () => {
              this.stories.update(stories => stories.filter(s => s._id !== story._id));
              this.messageService.add({
                severity: 'success',
                summary: 'Success',
                detail: 'Story deleted successfully',
                life: 3000
              });
            },
            error: (error) => {
              this.messageService.add({
                severity: 'error',
                summary: 'Error',
                detail: 'Failed to delete story',
                life: 3000
              });
              console.error('Error deleting story:', error);
            }
          });
        }
      }
    });
  }

  hideDialog(): void {
    this.storyDialog.set(false);
    this.submitted.set(false);
  }

  saveStory(): void {
    this.submitted.set(true);

    if (!this.story.title?.trim() || !this.story.author?.trim()) {
      return;
    }

    if (this.story._id) {
      // Update existing story
      this.storyService.updateStory(this.story._id, this.story).subscribe({
        next: (updatedStory) => {
          this.stories.update(stories =>
            stories.map(s => s._id === updatedStory._id ? updatedStory : s)
          );
          this.messageService.add({
            severity: 'success',
            summary: 'Success',
            detail: 'Story updated successfully',
            life: 3000
          });
          this.hideDialog();
        },
        error: (error) => {
          this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to update story',
            life: 3000
          });
          console.error('Error updating story:', error);
        }
      });
    } else {
      // Create new story
      const newStory: StoryCreate = {
        title: this.story.title,
        description: this.story.description,
        author: this.story.author,
        status: this.story.status
      };

      this.storyService.createStory(newStory).subscribe({
        next: (createdStory) => {
          this.stories.update(stories => [...stories, createdStory]);
          this.messageService.add({
            severity: 'success',
            summary: 'Success',
            detail: 'Story created successfully',
            life: 3000
          });
          this.hideDialog();
        },
        error: (error) => {
          this.messageService.add({
            severity: 'error',
            summary: 'Error',
            detail: 'Failed to create story',
            life: 3000
          });
          console.error('Error creating story:', error);
        }
      });
    }
  }

  getStatusSeverity(status: string): 'success' | 'info' | 'warn' | 'danger' | 'secondary' | 'contrast' {
    switch (status) {
      case 'published':
        return 'success';
      case 'draft':
        return 'warn';
      case 'archived':
        return 'secondary';
      default:
        return 'info';
    }
  }
}
