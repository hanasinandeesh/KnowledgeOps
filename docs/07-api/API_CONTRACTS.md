# KnowledgeOps --- Initial API Contracts

**Status:** Initial design baseline; exact schemas and authentication
mechanism require implementation review.

## 1. Conventions

-   Base path: `/api/v1`.
-   JSON request/response bodies unless multipart upload is specified.
-   UUID identifiers represented as strings.
-   Timestamps represented as ISO 8601 UTC.
-   Validate requests and responses with Pydantic.
-   Use consistent structured error responses.
-   Organization identity comes from authenticated server-side context,
    not a client-supplied tenant ID.
-   Enforce authorization in the service/backend layer.

## 2. Proposed endpoints

### Authentication

`POST /api/v1/auth/login` - Authenticate user. - Return approved
session/token representation. - Exact cookie/JWT/session design remains
open.

### Current user

`GET /api/v1/users/me` - Return current authenticated user and permitted
organization context.

### Current organization

`GET /api/v1/organizations/current` - Return organization information
for current membership.

### Upload document

`POST /api/v1/documents` - Content type: multipart/form-data. - Accept
file and required metadata such as title, visibility and optional
department. - Authorize uploader and visibility selection. - Create
document/version/job records. - Return `202 Accepted` with document ID,
version ID and ingestion job ID. - Do not process a large file
synchronously in the request.

### List documents

`GET /api/v1/documents` - Return only documents visible to the current
user. - Support pagination and safe filters after design is finalized.

### Get document

`GET /api/v1/documents/{document_id}` - Return authorized metadata and
processing status. - Do not expose storage paths or unauthorized
content.

### Archive document

`POST /api/v1/documents/{document_id}/archive` - Authorize operation. -
Update authoritative lifecycle state. - Ensure subsequent retrieval
excludes it.

### Ingestion job status

`GET /api/v1/ingestion-jobs/{job_id}` - Return authorized job status and
safe error information.

### Search

`POST /api/v1/search` - Example request:
`{ "query": "What is the travel reimbursement policy?" }` -
Authenticate, retrieve authorized evidence and return grounded
result/citations or no-answer. - Conversation support may be added
through the conversation endpoint.

### Create conversation

`POST /api/v1/conversations` - Create owner-private conversation.

### Send message

`POST /api/v1/conversations/{conversation_id}/messages` - Verify
conversation ownership. - Perform fresh permission-aware retrieval. -
Persist message, answer and source references.

### Get conversation

`GET /api/v1/conversations/{conversation_id}` - Only the owner can
access by default.

### Submit feedback

`POST /api/v1/feedback` - Accept feedback associated with a message the
user is allowed to access.

## 3. Standard error shape

Proposed shape:

``` json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request could not be processed.",
    "request_id": "..."
  }
}
```

Do not leak internal stack traces, secrets, storage paths or
inaccessible resource details.

## 4. Error codes

-   INVALID_REQUEST
-   UNAUTHENTICATED
-   FORBIDDEN
-   RESOURCE_NOT_FOUND
-   RESOURCE_CONFLICT
-   FILE_TOO_LARGE
-   UNSUPPORTED_FILE_TYPE
-   VALIDATION_ERROR
-   RATE_LIMITED
-   INTERNAL_ERROR
-   AI_PROVIDER_ERROR
-   AI_PROVIDER_UNAVAILABLE

## 5. Open API decisions

-   Exact login/session mechanism and token transport.
-   Exact request/response Pydantic schemas.
-   Pagination convention.
-   Search response and citation schema.
-   Upload size limits.
-   Idempotency key support.
-   Rate-limit response headers.
-   Conversation title generation.
-   Whether search is a standalone endpoint or only message-based in
    first UI release.
