export interface Tag {
  key: string
  label: string
  icon: string | null
  category: 'gameplay' | 'feature' | 'special'
}

export interface UserBrief {
  id: number
  display_name: string
  minecraft_username: string | null
  avatar_url: string | null
  owns_java_edition: boolean
}

export interface SeedListItem {
  id: number
  title: string
  description_preview: string
  cover_url: string | null
  seed_value: string
  edition: 'java' | 'bedrock'
  tested_version: string
  tags: Tag[]
  like_count: number
  collection_count: number
  view_count: number
  is_liked: boolean
  uploader: UserBrief | null
  created_at: string
}

export interface Screenshot {
  id: number
  url: string
  is_cover: boolean
  sort_order: number
}

export interface KeyCoord {
  id: number
  label: string
  x: number
  y: number | null
  z: number
}

export interface SeedDetail {
  id: number
  title: string
  description: string
  seed_value: string
  edition: string
  tested_version: string
  compatible_range: string | null
  world_type: string
  mod_env: string
  modpack_name: string | null
  modpack_version: string | null
  spawn_x: number
  spawn_z: number
  status: string
  screenshots: Screenshot[]
  key_coords: KeyCoord[]
  tags: Tag[]
  like_count: number
  collection_count: number
  view_count: number
  is_liked: boolean
  uploader: UserBrief | null
  created_at: string
}

export interface AuthUser {
  id: number
  display_name: string
  minecraft_uuid: string | null
  minecraft_username: string | null
  owns_java_edition: boolean
  avatar_url: string | null
  role: string
  unread_count: number
  created_at: string
}

export interface CollectionItem {
  id: number
  name: string
  description: string | null
  cover_url: string | null
  seed_count: number
  is_public: boolean
  sort_order: number
  created_at: string
  updated_at: string | null
}

export interface CollectionDetail {
  id: number
  name: string
  description: string | null
  cover_strategy: string
  cover_seed_id: number | null
  cover_url: string | null
  is_public: boolean
  owner: UserBrief | null
  seeds: SeedListItem[]
  meta: PaginationMeta | null
}

export interface Version {
  id: number
  edition: string
  version: string
  is_latest: boolean
  sort_order: number
}

export interface Comment {
  id: number
  content: string
  author: UserBrief | null
  created_at: string
}

export interface Notification {
  id: number
  type: string
  message: string
  detail: string | null
  seed_id: number | null
  is_read: boolean
  created_at: string
}

export interface PaginationMeta {
  page: number
  page_size: number
  total: number
  pages: number
}

export interface Envelope<T> {
  data: T
  meta?: PaginationMeta
}
