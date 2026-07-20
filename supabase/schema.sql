-- Supabase Database Schema for AI Knowledge Base Search (RAG)
-- This file contains all table definitions, constraints, triggers, and Row Level Security (RLS) policies.

-- Enable UUID extension
create extension if not exists "uuid-ossp";

---------------------------------------------------------
-- TABLES
---------------------------------------------------------

-- 1. Documents Table
create table if not exists public.documents (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    name text not null,
    size bigint not null,
    status text not null check (status in ('uploaded', 'processing', 'processed', 'failed')),
    storage_path text not null,
    error_message text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Add index on documents.user_id for faster queries
create index if not exists idx_documents_user_id on public.documents(user_id);

-- 2. Conversations Table
create table if not exists public.conversations (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references auth.users(id) on delete cascade,
    title text not null default 'New Conversation',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Add index on conversations.user_id
create index if not exists idx_conversations_user_id on public.conversations(user_id);

-- 3. Messages Table
create table if not exists public.messages (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null references public.conversations(id) on delete cascade,
    user_id uuid not null references auth.users(id) on delete cascade,
    role text not null check (role in ('user', 'assistant')),
    content text not null,
    sources jsonb default '[]'::jsonb,
    feedback text check (feedback in ('liked', 'disliked', null)),
    created_at timestamptz not null default now()
);

-- Add indices on messages for query performance
create index if not exists idx_messages_conversation_id on public.messages(conversation_id);
create index if not exists idx_messages_user_id on public.messages(user_id);

---------------------------------------------------------
-- ROW LEVEL SECURITY (RLS)
---------------------------------------------------------

-- Enable RLS on all tables
alter table public.documents enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;

-- Policies for documents
create policy "Users can view their own documents"
    on public.documents for select
    using (auth.uid() = user_id);

create policy "Users can insert their own documents"
    on public.documents for insert
    with check (auth.uid() = user_id);

create policy "Users can update their own documents"
    on public.documents for update
    using (auth.uid() = user_id);

create policy "Users can delete their own documents"
    on public.documents for delete
    using (auth.uid() = user_id);

-- Policies for conversations
create policy "Users can view their own conversations"
    on public.conversations for select
    using (auth.uid() = user_id);

create policy "Users can insert their own conversations"
    on public.conversations for insert
    with check (auth.uid() = user_id);

create policy "Users can update their own conversations"
    on public.conversations for update
    using (auth.uid() = user_id);

create policy "Users can delete their own conversations"
    on public.conversations for delete
    using (auth.uid() = user_id);

-- Policies for messages
create policy "Users can view their own messages"
    on public.messages for select
    using (auth.uid() = user_id);

create policy "Users can insert their own messages"
    on public.messages for insert
    with check (auth.uid() = user_id);

create policy "Users can update their own messages"
    on public.messages for update
    using (auth.uid() = user_id);

create policy "Users can delete their own messages"
    on public.messages for delete
    using (auth.uid() = user_id);

---------------------------------------------------------
-- TRIGGERS FOR UPDATED_AT
---------------------------------------------------------

-- Function to set updated_at
create or replace function public.handle_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- Apply updated_at trigger to documents
create trigger trigger_documents_updated_at
    before update on public.documents
    for each row
    execute function public.handle_updated_at();

-- Apply updated_at trigger to conversations
create trigger trigger_conversations_updated_at
    before update on public.conversations
    for each row
    execute function public.handle_updated_at();

---------------------------------------------------------
-- STORAGE BUCKETS CONFIGURATION (REFERENCE)
---------------------------------------------------------
-- Execute these SQL queries to set up the storage bucket policies for the 'pdfs' bucket.

-- Insert bucket config
insert into storage.buckets (id, name, public)
values ('pdfs', 'pdfs', false)
on conflict (id) do nothing;

-- Storage RLS Policies
create policy "Allow authenticated upload to pdfs bucket"
    on storage.objects for insert
    with check (
        bucket_id = 'pdfs' 
        and auth.role() = 'authenticated'
    );

create policy "Allow owners to access their files"
    on storage.objects for select
    using (
        bucket_id = 'pdfs'
        and auth.role() = 'authenticated'
        and (storage.foldername(name))[1] = auth.uid()::text
    );

create policy "Allow owners to delete their files"
    on storage.objects for delete
    using (
        bucket_id = 'pdfs'
        and auth.role() = 'authenticated'
        and (storage.foldername(name))[1] = auth.uid()::text
    );
