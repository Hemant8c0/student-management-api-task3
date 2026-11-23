# Student Management API — Task 3

A REST API built with **FastAPI**, **SQLAlchemy 2** and **SQLite**. This project includes student CRUD operations, API-key authentication, request validation and consistent JSON error responses.

## Task 3 implementation

- **API-key authentication:** every `/students/` route requires the `X-API-Key` request header.
- **Protected routes:** create, list, read, update and delete student endpoints are protected.
- **Payload validation:** Pydantic validates names, email addresses, age and course. Unknown JSON fields are rejected.
- **Consistent errors:** errors use the same `error.code`, `error.message` and `error.details` structure.
- **Safe key comparison:** API keys are compared using `secrets.compare_digest`.
- **Configurable key:** read from the `STUDENT_API_KEY` environment variable. A development-only fallback is provided for local testing.

> Before deploying, set your own strong `STUDENT_API_KEY`. Do not commit real API keys or passwords to GitHub.

## 1. Requirements

- Python 3.10 or newer
- pip

## 2. Install and run (Windows PowerShell)

Open PowerShell in this project folder:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set a development API key for this terminal session:

```powershell
$env:STUDENT_API_KEY = "my-local-key-123"
```

Start the server:

```powershell
uvicorn main:app --reload
```

Open:
- API home: http://127.0.0.1:8000/
- Swagger UI: http://127.0.0.1:8000/docs

The `students.db` SQLite database and `students` table are created automatically.

### macOS / Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
export STUDENT_API_KEY="my-local-key-123"
uvicorn main:app --reload
```

## 3. Authentication: how to test protected routes

All `/students` endpoints require this header:

```http
X-API-Key: my-local-key-123
```

The value must match the `STUDENT_API_KEY` environment variable used when the server was started.

### Test in Swagger UI

1. Start the API and open `http://127.0.0.1:8000/docs`.
2. Find a student endpoint, for example `GET /students/`.
3. Click **Try it out** and then **Execute** without adding the key. It should return `401 Unauthorized`.
4. Use the **Authorize** button near the top of Swagger UI.
5. Enter `my-local-key-123` in the APIKeyAuth value field and click **Authorize**, then **Close**.
6. Execute the student endpoint again. It should now return a successful response (for an empty database, `GET /students/` returns `[]`).
7. To test a wrong key, remove/reauthorize with an incorrect value; the response should be `401`.

### Test with curl

No key (expected `401`):

```bash
curl -i http://127.0.0.1:8000/students/
```

Correct key (expected `200`):

```bash
curl -i -H "X-API-Key: my-local-key-123" http://127.0.0.1:8000/students/
```

Wrong key (expected `401`):

```bash
curl -i -H "X-API-Key: wrong-key" http://127.0.0.1:8000/students/
```

## 4. CRUD examples

Use the header on **every** request to `/students`. The examples below use `my-local-key-123`.

### Create a student — `POST /students/`

```bash
curl -X POST http://127.0.0.1:8000/students/ \
  -H "X-API-Key: my-local-key-123" \
  -H "Content-Type: application/json" \
  -d '{"name":"Aman Sharma","email":"aman@example.com","age":21,"course":"Computer Science"}'
```

Expected status: `201 Created`.

### Read all students — `GET /students/`

```bash
curl -H "X-API-Key: my-local-key-123" http://127.0.0.1:8000/students/
```

### Read one student — `GET /students/1`

```bash
curl -H "X-API-Key: my-local-key-123" http://127.0.0.1:8000/students/1
```

### Update a student — `PUT /students/1`

```bash
curl -X PUT http://127.0.0.1:8000/students/1 \
  -H "X-API-Key: my-local-key-123" \
  -H "Content-Type: application/json" \
  -d '{"age":22,"course":"Data Science"}'
```

### Delete a student — `DELETE /students/1`

```bash
curl -X DELETE -H "X-API-Key: my-local-key-123" http://127.0.0.1:8000/students/1
```

## 5. Payload validation

`POST /students/` requires all of these fields:

| Field | Validation |
|---|---|
| `name` | String, 2–100 characters |
| `email` | Valid email address |
| `age` | Integer from 16 to 100 |
| `course` | String, 2–100 characters |

For `PUT /students/{student_id}`, send at least one field. Only supplied fields are updated. Unknown fields are rejected.

Invalid example (expected `422 Unprocessable Entity`):

```json
{
  "name": "A",
  "email": "not-an-email",
  "age": 12,
  "course": "C"
}
```

## 6. Consistent error response format

All handled API errors use this structure:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "API key missing or invalid",
    "details": null
  }
}
```

Examples:

| Situation | HTTP status | Error code |
|---|---:|---|
| Missing or incorrect API key | 401 | `UNAUTHORIZED` |
| Invalid request body | 422 | `VALIDATION_ERROR` |
| Student ID does not exist | 404 | `NOT_FOUND` |
| Duplicate student email | 409 | `CONFLICT` |
| Unexpected server error | 500 | `INTERNAL_SERVER_ERROR` |

For validation errors, `details` contains the invalid field, message and validation type. Internal exception details are not returned to API clients.

## 7. Endpoints

| Method | Endpoint | Authentication |
|---|---|---|
| GET | `/` | Not required |
| POST | `/students/` | API key required |
| GET | `/students/` | API key required |
| GET | `/students/{student_id}` | API key required |
| PUT | `/students/{student_id}` | API key required |
| DELETE | `/students/{student_id}` | API key required |

## 8. GitHub submission

Create a new **empty** GitHub repository, for example `student-management-api-task3`. Do not initialize it with another README.

Run these commands in the project folder:

```bash
git init
git add .
git commit -m "Complete Task 3 API authentication and validation"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/student-management-api-task3.git
git push -u origin main
```

Replace `YOUR-USERNAME` with your GitHub username. Your submission URL will be:

```text
https://github.com/YOUR-USERNAME/student-management-api-task3
```

## Submission checklist

- [ ] Server starts successfully.
- [ ] `/students` endpoints reject requests without a key.
- [ ] Correct API key allows access.
- [ ] Invalid payload returns `422` in the documented error format.
- [ ] Duplicate email returns `409`.
- [ ] Missing student returns `404`.
- [ ] README explains how to test protected routes.
- [ ] Project is pushed to GitHub and the repository URL is submitted.
