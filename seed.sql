INSERT INTO skills (name) VALUES ('Python'), ('React'), ('FastAPI'), ('SQL'), ('TypeScript'), ('AWS');
INSERT INTO companies (name, email, password_hash, description, website, location) VALUES 
('TechCorp', 'contact@techcorp.com', '$2b$12$R9h/lIPzHZlu699i89VfF.Y6O3NfH0F0F0F0F0F0F0F0F0F0F0F0F', 'Leading tech company', 'https://techcorp.com', 'San Francisco'),
('DevShop', 'hello@devshop.io', '$2b$12$R9h/lIPzHZlu699i89VfF.Y6O3NfH0F0F0F0F0F0F0F0F0F0F0F0F', 'Expert software development agency', 'https://devshop.io', 'Remote');
INSERT INTO candidates (name, email, experience_years, location) VALUES ('Alice Smith', 'alice@example.com', 5, 'New York'), ('Bob Jones', 'bob@example.com', 3, 'Austin');
INSERT INTO roles (company_id, title, description, location, salary_range, employment_type) VALUES (1, 'Backend Engineer', 'Develop robust APIs using FastAPI', 'San Francisco', '120k-160k', 'Full-time'), (2, 'Frontend Developer', 'Build beautiful UIs with React', 'Remote', '100k-140k', 'Full-time');
INSERT INTO candidate_skills (candidate_id, skill_id) VALUES (1, 1), (1, 3), (1, 4), (2, 2), (2, 5);
INSERT INTO role_skills (role_id, skill_id) VALUES (1, 1), (1, 3), (1, 4), (2, 2), (2, 5);
INSERT INTO applications (candidate_id, role_id, status) VALUES (1, 1, 'applied'), (2, 2, 'interviewing');
