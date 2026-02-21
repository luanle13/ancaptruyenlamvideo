// AnCapTruyenLamVideo - Story Model

export interface Story {
  _id?: string;
  title: string;
  description: string;
  author: string;
  status: 'draft' | 'published' | 'archived';
  createdAt?: string;
  updatedAt?: string;
}

export interface StoryCreate {
  title: string;
  description: string;
  author: string;
  status: 'draft' | 'published' | 'archived';
}

export interface StoryUpdate {
  title?: string;
  description?: string;
  author?: string;
  status?: 'draft' | 'published' | 'archived';
}
