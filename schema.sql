CREATE TABLE candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    experience_years INTEGER,
    location TEXT
);

CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT,
    description TEXT,
    website TEXT,
    location TEXT
);

CREATE TABLE roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    location TEXT,
    salary_range TEXT,
    employment_type TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE TABLE skills (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE candidate_skills (
    candidate_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    PRIMARY KEY (candidate_id, skill_id),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id),
    FOREIGN KEY (skill_id) REFERENCES skills(id)
);

CREATE TABLE role_skills (
    role_id INTEGER NOT NULL,
    skill_id INTEGER NOT NULL,
    PRIMARY KEY (role_id, skill_id),
    FOREIGN KEY (role_id) REFERENCES roles(id),
    FOREIGN KEY (skill_id) REFERENCES skills(id)
);

CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER NOT NULL,
    role_id INTEGER NOT NULL,
    status TEXT DEFAULT 'applied',
    applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id),
    FOREIGN KEY (role_id) REFERENCES roles(id)
);
