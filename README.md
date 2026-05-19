# CandidateConnect Backend

A FastAPI backend for matching candidates to roles.

## Endpoints

- **Candidates**:
  - `GET /candidates`: List all candidates.
  - `GET /candidates/{id}`: Get a specific candidate.
  - `POST /candidates`: Create a candidate.
  - `PUT /candidates/{id}`: Update a candidate.
  - `DELETE /candidates/{id}`: Delete a candidate.
- **Roles**:
  - `GET /roles`: List all roles.
  - `GET /roles/search`: Search roles by title/location.
  - `POST /roles`: Create a role.
  - `PUT /roles/{id}`: Update a role.
  - `DELETE /roles/{id}`: Delete a role.
- **Companies & Auth**:
  - `POST /companies/register`: Register a new company.
  - `POST /companies/login`: Login and receive a JWT token.
- **Applications**:
  - `GET /applications`: List all applications.
  - `POST /applications`: Submit an application.
  - `DELETE /applications/{id}`: Delete an application.
- **Matching**:
  - `GET /matches?candidate_id=X`: Get matched roles.

## Matching Algorithm
Scores roles based on:
1. **Skills** (60%): Overlap between candidate skills and role requirements.
2. **Experience** (25%): Candidate's years vs role's minimum.
3. **Location** (15%): Exact match or Remote.

## API URL
The base URL is stored in `/home/team/shared/api-url.txt`. Currently: `http://localhost:8000`.
