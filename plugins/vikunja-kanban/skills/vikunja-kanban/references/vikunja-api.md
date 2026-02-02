# Vikunja API (Used by this skill)

Base path: `/api/v1`

## Authentication

Use `Authorization: Bearer <token>`.

## Projects

- `GET /projects` — list projects
- `PUT /projects` — create project

## Views and buckets

- `GET /projects/{id}/views` — list views for a project
- `GET /projects/{id}/views/{view}/buckets` — list buckets for a view
- `GET /projects/{id}/views/{view}/tasks` — list tasks for a view

## Tasks

- `PUT /projects/{id}/tasks` — create task in project
- `GET /tasks/{id}` — get task
- `POST /tasks/{id}` — update task

## Task position / bucket

- `POST /tasks/{id}/position` — update task position
- `POST /projects/{id}/views/{view}/buckets/{bucket}/tasks` — move task into bucket

## Labels

- `GET /labels` — list labels
- `PUT /labels` — create label
- `PUT /tasks/{task}/labels` — add label to task

## Comments

- `GET /tasks/{taskID}/comments` — list comments
- `PUT /tasks/{taskID}/comments` — add comment
