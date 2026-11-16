# API Architecture

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `POST` | `/auth/login` | Authenticate user |
| `GET` | `/users/me` | Current user and membership |
| `GET` | `/organizations/current` | Current organization |
| `POST` | `/documents` | Upload document |
| `GET` | `/documents` | List accessible documents |
| `GET` | `/documents/{id}` | Document details |
| `POST` | `/documents/{id}/archive` | Archive document |
| `GET` | `/ingestion-jobs/{id}` | Check ingestion status |
| `POST` | `/search` | Search authorized knowledge |
| `POST` | `/conversations` | Create private conversation |
| `POST` | `/conversations/{id}/messages` | Ask a question |
| `GET` | `/conversations/{id}` | Read owned conversation |
| `POST` | `/feedback` | Submit answer feedback |

