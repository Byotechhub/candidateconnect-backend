import subprocess
import json
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta

app = FastAPI()

# JWT settings
SECRET_KEY = "super-secret-key" # In a real app, use environment variables
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480 # 8 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

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

def run_db(query: str):
    escaped_query = query.replace('"', '\"')
    result = subprocess.run(['team-db', escaped_query], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing query: {query}")
        print(f"Stderr: {result.stderr}")
        raise HTTPException(status_code=500, detail=result.stderr)
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []

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
    candidates = run_db("SELECT * FROM candidates")
    for candidate in candidates:
        skills = run_db(f"SELECT s.name FROM skills s JOIN candidate_skills cs ON s.id = cs.skill_id WHERE cs.candidate_id = {candidate['id']}")
        candidate['skills'] = [s['name'] for s in skills]
    return candidates

@app.get("/candidates/{candidate_id}")
def get_candidate(candidate_id: int):
    res = run_db(f"SELECT * FROM candidates WHERE id = {candidate_id}")
    if not res:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate = res[0]
    skills = run_db(f"SELECT s.name FROM skills s JOIN candidate_skills cs ON s.id = cs.skill_id WHERE cs.candidate_id = {candidate_id}")
    candidate['skills'] = [s['name'] for s in skills]
    return candidate

@app.post("/candidates")
def create_candidate(candidate: Candidate):
    run_db(f"INSERT INTO candidates (name, email, experience_years, location) VALUES ('{candidate.name}', '{candidate.email}', {candidate.experience_years}, '{candidate.location}')")
    res = run_db(f"SELECT id FROM candidates WHERE email = '{candidate.email}'")
    if not res:
        raise HTTPException(status_code=500, detail="Failed to create candidate")
    candidate_id = res[0]['id']
    
    for skill_name in candidate.skills:
        skill_res = run_db(f"SELECT id FROM skills WHERE name = '{skill_name}'")
        if not skill_res:
            run_db(f"INSERT INTO skills (name) VALUES ('{skill_name}')")
            skill_res = run_db(f"SELECT id FROM skills WHERE name = '{skill_name}'")
        skill_id = skill_res[0]['id']
        run_db(f"INSERT INTO candidate_skills (candidate_id, skill_id) VALUES ({candidate_id}, {skill_id})")
    
    return {"id": candidate_id, "message": "Candidate created successfully"}

@app.put("/candidates/{candidate_id}")
def update_candidate(candidate_id: int, candidate: Candidate):
    run_db(f"UPDATE candidates SET name='{candidate.name}', email='{candidate.email}', experience_years={candidate.experience_years}, location='{candidate.location}' WHERE id={candidate_id}")
    # Update skills: delete old and add new
    run_db(f"DELETE FROM candidate_skills WHERE candidate_id={candidate_id}")
    for skill_name in candidate.skills:
        skill_res = run_db(f"SELECT id FROM skills WHERE name = '{skill_name}'")
        if not skill_res:
            run_db(f"INSERT INTO skills (name) VALUES ('{skill_name}')")
            skill_res = run_db(f"SELECT id FROM skills WHERE name = '{skill_name}'")
        skill_id = skill_res[0]['id']
        run_db(f"INSERT INTO candidate_skills (candidate_id, skill_id) VALUES ({candidate_id}, {skill_id})")
    return {"message": "Candidate updated successfully"}

@app.delete("/candidates/{candidate_id}")
def delete_candidate(candidate_id: int):
    run_db(f"DELETE FROM candidate_skills WHERE candidate_id={candidate_id}")
    run_db(f"DELETE FROM candidates WHERE id={candidate_id}")
    return {"message": "Candidate deleted successfully"}

# --- Roles CRUD ---

@app.get("/roles")
def get_roles():
    roles = run_db("SELECT * FROM roles")
    for role in roles:
        skills = run_db(f"SELECT s.name FROM skills s JOIN role_skills rs ON s.id = rs.skill_id WHERE rs.role_id = {role['id']}")
        role['skills'] = [s['name'] for s in skills]
    return roles

@app.get("/roles/search")
def search_roles(title: Optional[str] = None, location: Optional[str] = None):
    query = "SELECT * FROM roles WHERE 1=1"
    if title:
        query += f" AND title LIKE '%{title}%'"
    if location:
        query += f" AND location LIKE '%{location}%'"
    roles = run_db(query)
    for role in roles:
        skills = run_db(f"SELECT s.name FROM skills s JOIN role_skills rs ON s.id = rs.skill_id WHERE rs.role_id = {role['id']}")
        role['skills'] = [s['name'] for s in skills]
    return roles

@app.post("/roles")
def create_role(role: Role):
    run_db(f"INSERT INTO roles (company_id, title, description, location, salary_range, employment_type, min_experience) VALUES ({role.company_id}, '{role.title}', '{role.description}', '{role.location}', '{role.salary_range}', '{role.employment_type}', {role.min_experience})")
    res = run_db(f"SELECT id FROM roles WHERE company_id = {role.company_id} ORDER BY id DESC LIMIT 1")
    if not res:
        raise HTTPException(status_code=500, detail="Failed to create role")
    role_id = res[0]['id']
    
    for skill_name in role.skills:
        skill_res = run_db(f"SELECT id FROM skills WHERE name = '{skill_name}'")
        if not skill_res:
            run_db(f"INSERT INTO skills (name) VALUES ('{skill_name}')")
            skill_res = run_db(f"SELECT id FROM skills WHERE name = '{skill_name}'")
        skill_id = skill_res[0]['id']
        run_db(f"INSERT INTO role_skills (role_id, skill_id) VALUES ({role_id}, {skill_id})")
        
    return {"id": role_id, "message": "Role created successfully"}

@app.put("/roles/{role_id}")
def update_role(role_id: int, role: Role):
    run_db(f"UPDATE roles SET company_id={role.company_id}, title='{role.title}', description='{role.description}', location='{role.location}', salary_range='{role.salary_range}', employment_type='{role.employment_type}', min_experience={role.min_experience} WHERE id={role_id}")
    run_db(f"DELETE FROM role_skills WHERE role_id={role_id}")
    for skill_name in role.skills:
        skill_res = run_db(f"SELECT id FROM skills WHERE name = '{skill_name}'")
        if not skill_res:
            run_db(f"INSERT INTO skills (name) VALUES ('{skill_name}')")
            skill_res = run_db(f"SELECT id FROM skills WHERE name = '{skill_name}'")
        skill_id = skill_res[0]['id']
        run_db(f"INSERT INTO role_skills (role_id, skill_id) VALUES ({role_id}, {skill_id})")
    return {"message": "Role updated successfully"}

@app.delete("/roles/{role_id}")
def delete_role(role_id: int):
    run_db(f"DELETE FROM role_skills WHERE role_id={role_id}")
    run_db(f"DELETE FROM roles WHERE id={role_id}")
    return {"message": "Role deleted successfully"}

# --- Applications CRUD ---

@app.get("/applications")
def get_applications():
    return run_db("SELECT * FROM applications")

@app.post("/applications")
def create_application(app_data: Application):
    run_db(f"INSERT INTO applications (candidate_id, role_id, status) VALUES ({app_data.candidate_id}, {app_data.role_id}, '{app_data.status}')")
    return {"message": "Application submitted successfully"}

@app.delete("/applications/{application_id}")
def delete_application(application_id: int):
    run_db(f"DELETE FROM applications WHERE id={application_id}")
    return {"message": "Application deleted successfully"}

# --- Company Auth ---

@app.post("/companies/register")
def register_company(company: CompanyRegister):
    # Check if email exists
    existing = run_db(f"SELECT id FROM companies WHERE email = '{company.email}'")
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(company.password)
    # Be careful with hashed password potentially containing single quotes (though bcrypt usually doesn't, it has $)
    # team-db tool uses JSON and might have its own escaping issues if I don't handle it.
    # But since it's a CLI tool where I pass the query as a string, I should be fine if I use double quotes for the query.
    
    query = f"INSERT INTO companies (name, email, password_hash, description, website) VALUES ('{company.name}', '{company.email}', '{hashed_password}', '{company.description or ''}', '{company.website or ''}')"
    run_db(query)
    return {"message": "Company registered successfully"}

@app.post("/companies/login")
def login_company(login: CompanyLogin):
    res = run_db(f"SELECT * FROM companies WHERE email = '{login.email}'")
    if not res:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    company = res[0]
    if not verify_password(login.password, company['password_hash']):
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
    candidate_res = run_db(f"SELECT * FROM candidates WHERE id = {candidate_id}")
    if not candidate_res:
        raise HTTPException(status_code=404, detail="Candidate not found")
    candidate = candidate_res[0]
    
    candidate_skills_res = run_db(f"SELECT s.name FROM skills s JOIN candidate_skills cs ON s.id = cs.skill_id WHERE cs.candidate_id = {candidate_id}")
    candidate_skills = set(s['name'] for s in candidate_skills_res)
    
    roles = run_db("SELECT * FROM roles")
    matches = []
    
    for role in roles:
        role_skills_res = run_db(f"SELECT s.name FROM skills s JOIN role_skills rs ON s.id = rs.skill_id WHERE rs.role_id = {role['id']}")
        role_skills = set(s['name'] for s in role_skills_res)
        
        # 1. Skills match (primary - 60%)
        common_skills = candidate_skills.intersection(role_skills)
        skill_match_score = len(common_skills) / len(role_skills) if role_skills else 0
        
        # 2. Experience level match (secondary - 25%)
        # If candidate has more or equal experience, 1.0. If less, proportional.
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
    uvicorn.run(app, host="0.0.0.0", port=8000)
