import psycopg2
import json
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from jose import JWTError, jwt
from datetime import datetime, timedelta
from psycopg2 import pool

app = FastAPI()

# Database connection - use external connection for production
import os

DB_URL = os.environ.get("DATABASE_URL", "postgresql://candidateconnect_user:8IDjea9v12HdP8oM1QR71JLOlrVHRhjT@dpg-d88pb5u7r5hc73cn5tjg-a.oregon-postgres.render.com/candidateconnect")

# Parse the connection string
import re
m = re.match(r"postgresql://([^:]+):([^@]+)@(.+)/(.+)", DB_URL)
DB_USER, DB_PASSWORD, DB_HOST_PORT, DB_NAME = m.group(1), m.group(2), m.group(3), m.group(4)
if ":" in DB_HOST_PORT:
    DB_HOST, DB_PORT = DB_HOST_PORT.split(":")
else:
    DB_HOST, DB_PORT = DB_HOST_PORT, "5432"

connection_pool = psycopg2.pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    host=DB_HOST,
    port=DB_PORT,
    database=DB_NAME,
    user=DB_USER,
    password=DB_PASSWORD
)

# JWT settings
SECRET_KEY = "super-secret-key" # In a real app, use environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480 # 8 hours

import hashlib
import hmac

def get_password_hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return hmac.compare_digest(get_password_hash(plain_password), hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# Add CORS middleware to allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def run_db(query: str, params=None):
    conn = connection_pool.getconn()
    try:
        with conn.cursor() as cur:
            cur.execute(query, params)
            if query.strip().upper().startswith("SELECT"):
                columns = [desc[0] for desc in cur.description]
                results = cur.fetchall()
                return [dict(zip(columns, row)) for row in results]
            else:
                conn.commit()
                return cur.rowcount
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        connection_pool.putconn(conn)

class Candidate(BaseModel):
    name: str
    email: str
    experience_years: int
    location: str
    skills: List[str]

class Role(BaseModel):
    company_id: int
    title: str
    description: str
    location: str
    salary_range: str
    employment_type: str
    min_experience: int = 0
    skills: List[str]

class Application(BaseModel):
    candidate_id: int
    role_id: int
    status: str = "applied"

class CompanyRegister(BaseModel):
    name: str
    email: str
    password: str
    description: Optional[str] = None
    website: Optional[str] = None

class CompanyLogin(BaseModel):
    email: str
    password: str

# --- Candidates CRUD ---

@app.get("/candidates")
def get_candidates():
    candidates = run_db("SELECT id, name, email, experience_years, location FROM candidates")
    for candidate in candidates:
        skills = run_db("SELECT s.name FROM skills s JOIN candidate_skills cs ON s.id = cs.skill_id WHERE cs.candidate_id = %s", (candidate['id'],))
        candidate['skills'] = [s['name'] for s in skills]
    return candidates

@app.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: int):
    res = run_db("SELECT id, name, email, experience_years, location FROM candidates WHERE id = %s", (candidate_id,))
    if not res:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate = res[0]
    skills = run_db("SELECT s.name FROM skills s JOIN candidate_skills cs ON s.id = cs.skill_id WHERE cs.candidate_id = %s", (candidate_id,))
    candidate['skills'] = [s['name'] for s in skills]
    return candidate

@app.post("/candidates")
def create_candidate(candidate: Candidate):
    result = run_db(
        "INSERT INTO candidates (name, email, experience_years, location) VALUES (%s, %s, %s, %s) RETURNING id",
        (candidate.name, candidate.email, candidate.experience_years, candidate.location)
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create candidate")
    candidate_id = result[0]['id'] if isinstance(result, list) else result

    for skill_name in candidate.skills:
        skill_res = run_db("SELECT id FROM skills WHERE name = %s", (skill_name,))
        if not skill_res:
            run_db("INSERT INTO skills (name) VALUES (%s)", (skill_name,))
            skill_res = run_db("SELECT id FROM skills WHERE name = %s", (skill_name,))
        skill_id = skill_res[0]['id']
        run_db("INSERT INTO candidate_skills (candidate_id, skill_id) VALUES (%s, %s)", (candidate_id, skill_id))

    return {"id": candidate_id, "message": "Candidate created successfully"}

@app.put("/candidates/{candidate_id}")
def update_candidate(candidate_id: int, candidate: Candidate):
    run_db("UPDATE candidates SET name=%s, email=%s, experience_years=%s, location=%s WHERE id=%s",
           (candidate.name, candidate.email, candidate.experience_years, candidate.location, candidate_id))
    run_db("DELETE FROM candidate_skills WHERE candidate_id=%s", (candidate_id,))
    for skill_name in candidate.skills:
        skill_res = run_db("SELECT id FROM skills WHERE name = %s", (skill_name,))
        if not skill_res:
            run_db("INSERT INTO skills (name) VALUES (%s)", (skill_name,))
            skill_res = run_db("SELECT id FROM skills WHERE name = %s", (skill_name,))
        skill_id = skill_res[0]['id']
        run_db("INSERT INTO candidate_skills (candidate_id, skill_id) VALUES (%s, %s)", (candidate_id, skill_id))
    return {"message": "Candidate updated successfully"}

@app.delete("/candidates/{candidate_id}")
def delete_candidate(candidate_id: int):
    run_db("DELETE FROM candidate_skills WHERE candidate_id=%s", (candidate_id,))
    run_db("DELETE FROM candidates WHERE id=%s", (candidate_id,))
    return {"message": "Candidate deleted successfully"}

# --- Roles CRUD ---

@app.get("/roles")
def get_roles():
    roles = run_db("SELECT id, company_id, title, description, location, salary_range, employment_type, min_experience FROM roles")
    for role in roles:
        skills = run_db("SELECT s.name FROM skills s JOIN role_skills rs ON s.id = rs.skill_id WHERE rs.role_id = %s", (role['id'],))
        role['skills'] = [s['name'] for s in skills]
    return roles

@app.get("/roles/search")
def search_roles(title: Optional[str] = None, location: Optional[str] = None):
    query = "SELECT id, company_id, title, description, location, salary_range, employment_type, min_experience FROM roles WHERE 1=1"
    params = []
    if title:
        query += " AND title LIKE %s"
        params.append(f"%{title}%")
    if location:
        query += " AND location LIKE %s"
        params.append(f"%{location}%")
    roles = run_db(query, tuple(params) if params else None)
    for role in roles:
        skills = run_db("SELECT s.name FROM skills s JOIN role_skills rs ON s.id = rs.skill_id WHERE rs.role_id = %s", (role['id'],))
        role['skills'] = [s['name'] for s in skills]
    return roles

@app.post("/roles")
def create_role(role: Role):
    result = run_db(
        "INSERT INTO roles (company_id, title, description, location, salary_range, employment_type, min_experience) VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING id",
        (role.company_id, role.title, role.description, role.location, role.salary_range, role.employment_type, role.min_experience)
    )
    if not result:
        raise HTTPException(status_code=500, detail="Failed to create role")
    role_id = result[0]['id'] if isinstance(result, list) else result

    for skill_name in role.skills:
        skill_res = run_db("SELECT id FROM skills WHERE name = %s", (skill_name,))
        if not skill_res:
            run_db("INSERT INTO skills (name) VALUES (%s)", (skill_name,))
            skill_res = run_db("SELECT id FROM skills WHERE name = %s", (skill_name,))
        skill_id = skill_res[0]['id']
        run_db("INSERT INTO role_skills (role_id, skill_id) VALUES (%s, %s)", (role_id, skill_id))

    return {"id": role_id, "message": "Role created successfully"}

@app.put("/roles/{role_id}")
def update_role(role_id: int, role: Role):
    run_db("UPDATE roles SET company_id=%s, title=%s, description=%s, location=%s, salary_range=%s, employment_type=%s, min_experience=%s WHERE id=%s",
           (role.company_id, role.title, role.description, role.location, role.salary_range, role.employment_type, role.min_experience, role_id))
    run_db("DELETE FROM role_skills WHERE role_id=%s", (role_id,))
    for skill_name in role.skills:
        skill_res = run_db("SELECT id FROM skills WHERE name = %s", (skill_name,))
        if not skill_res:
            run_db("INSERT INTO skills (name) VALUES (%s)", (skill_name,))
            skill_res = run_db("SELECT id FROM skills WHERE name = %s", (skill_name,))
        skill_id = skill_res[0]['id']
        run_db("INSERT INTO role_skills (role_id, skill_id) VALUES (%s, %s)", (role_id, skill_id))
    return {"message": "Role updated successfully"}

@app.delete("/roles/{role_id}")
def delete_role(role_id: int):
    run_db("DELETE FROM role_skills WHERE role_id=%s", (role_id,))
    run_db("DELETE FROM roles WHERE id=%s", (role_id,))
    return {"message": "Role deleted successfully"}

# --- Applications CRUD ---

@app.get("/applications")
def get_applications():
    return run_db("SELECT id, candidate_id, role_id, status, applied_at FROM applications")

@app.post("/applications")
def create_application(app_data: Application):
    run_db("INSERT INTO applications (candidate_id, role_id, status) VALUES (%s, %s, %s)",
           (app_data.candidate_id, app_data.role_id, app_data.status))
    return {"message": "Application submitted successfully"}

@app.delete("/applications/{application_id}")
def delete_application(application_id: int):
    run_db("DELETE FROM applications WHERE id=%s", (application_id,))
    return {"message": "Application deleted successfully"}

# --- Company Auth ---

@app.post("/companies/register")
def register_company(company: CompanyRegister):
    existing = run_db("SELECT id FROM companies WHERE email = %s", (company.email,))
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(company.password)
    run_db("INSERT INTO companies (name, email, password_hash, description, website) VALUES (%s, %s, %s, %s, %s)",
           (company.name, company.email, hashed_password, company.description or '', company.website or ''))
    return {"message": "Company registered successfully"}

@app.post("/companies/login")
def login_company(login: CompanyLogin):
    conn = psycopg2.connect(
        host="dpg-d88pb5u7r5hc73cn5tjg-a.oregon-postgres.render.com",
        port="5432",
        database="candidateconnect",
        user="candidateconnect_user",
        password="8IDjea9v12HdP8oM1QR71JLOlrVHRhjT"
    )
    cur = conn.cursor()
    cur.execute("SELECT id, name, email, password_hash FROM companies WHERE email = %s", (login.email,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    company = dict(zip(['id', 'name', 'email', 'password_hash'], rows[0]))
    stored_hash = company['password_hash']
    input_hash = hashlib.sha256(login.password.encode()).hexdigest()
    
    if not hmac.compare_digest(input_hash, stored_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": company['email'], "company_id": company['id']},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Matching Algorithm ---

@app.get("/matches")
def get_matches(candidate_id: int):
    candidate_res = run_db("SELECT id, name, email, experience_years, location FROM candidates WHERE id = %s", (candidate_id,))
    if not candidate_res:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate = candidate_res[0]

    candidate_skills_res = run_db("SELECT s.name FROM skills s JOIN candidate_skills cs ON s.id = cs.skill_id WHERE cs.candidate_id = %s", (candidate_id,))
    candidate_skills = set(s['name'] for s in candidate_skills_res)

    roles = run_db("SELECT id, company_id, title, description, location, salary_range, employment_type, min_experience FROM roles")
    matches = []

    for role in roles:
        role_skills_res = run_db("SELECT s.name FROM skills s JOIN role_skills rs ON s.id = rs.skill_id WHERE rs.role_id = %s", (role['id'],))
        role_skills = set(s['name'] for s in role_skills_res)

        # 1. Skills match (primary - 60%)
        common_skills = candidate_skills.intersection(role_skills)
        skill_match_score = len(common_skills) / len(role_skills) if role_skills else 0

        # 2. Experience level match (secondary - 25%)
        if candidate['experience_years'] >= role['min_experience']:
            experience_score = 1.0
        elif role['min_experience'] > 0:
            experience_score = candidate['experience_years'] / role['min_experience']
        else:
            experience_score = 1.0

        # 3. Location preference (tertiary - 15%)
        location_match = (candidate['location'].lower() == role['location'].lower() or role['location'].lower() == 'remote')
        location_score = 1.0 if location_match else 0.5

        final_score = (skill_match_score * 0.6) + (experience_score * 0.25) + (location_score * 0.15)

        if skill_match_score > 0:
            matches.append({
                "role_id": role['id'],
                "title": role['title'],
                "score": round(final_score, 2),
                "skill_match_score": round(skill_match_score, 2),
                "experience_score": round(experience_score, 2),
                "location_score": round(location_score, 2),
                "common_skills": list(common_skills),
                "location_match": location_match
            })

    matches.sort(key=lambda x: x['score'], reverse=True)
    return matches

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)