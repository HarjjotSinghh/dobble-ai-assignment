-- Seed data for doctor appointment system
-- This runs automatically when PostgreSQL container starts

-- Insert demo users (passwords are bcrypt hash of "password123")
INSERT INTO users (email, password_hash, name, role, created_at) VALUES
('dr.ahuja@hospital.com', '$2b$12$LJ3m4ys3Lp5v8Bq0D5Y8XOZmFJ3Q2YxKrE5VdNJQ1P3rF6R8h5TKa', 'Dr. Priya Ahuja', 'doctor', NOW()),
('dr.sharma@hospital.com', '$2b$12$LJ3m4ys3Lp5v8Bq0D5Y8XOZmFJ3Q2YxKrE5VdNJQ1P3rF6R8h5TKa', 'Dr. Rahul Sharma', 'doctor', NOW()),
('dr.patel@hospital.com', '$2b$12$LJ3m4ys3Lp5v8Bq0D5Y8XOZmFJ3Q2YxKrE5VdNJQ1P3rF6R8h5TKa', 'Dr. Anita Patel', 'doctor', NOW()),
('patient.john@email.com', '$2b$12$LJ3m4ys3Lp5v8Bq0D5Y8XOZmFJ3Q2YxKrE5VdNJQ1P3rF6R8h5TKa', 'John Doe', 'patient', NOW()),
('patient.jane@email.com', '$2b$12$LJ3m4ys3Lp5v8Bq0D5Y8XOZmFJ3Q2YxKrE5VdNJQ1P3rF6R8h5TKa', 'Jane Smith', 'patient', NOW())
ON CONFLICT (email) DO NOTHING;

-- Insert doctor profiles
INSERT INTO doctors (user_id, specialization, phone, bio) VALUES
(1, 'General Physician', '+91-9876543210', 'Experienced general physician with 10+ years of practice.'),
(2, 'Cardiologist', '+91-9876543211', 'Heart specialist with expertise in interventional cardiology.'),
(3, 'Dermatologist', '+91-9876543212', 'Skin care expert specializing in cosmetic dermatology.')
ON CONFLICT DO NOTHING;

-- Insert patient profiles
INSERT INTO patients (user_id, phone, date_of_birth) VALUES
(4, '+91-9876543213', '1990-05-15'),
(5, '+91-9876543214', '1985-08-22')
ON CONFLICT DO NOTHING;

-- Insert doctor availability (Monday-Friday, 9 AM - 5 PM with lunch break)
-- Dr. Ahuja - Monday to Friday
INSERT INTO doctor_availability (doctor_id, day_of_week, start_time, end_time) VALUES
(1, 0, '09:00', '12:00'), (1, 0, '14:00', '17:00'),
(1, 1, '09:00', '12:00'), (1, 1, '14:00', '17:00'),
(1, 2, '09:00', '12:00'), (1, 2, '14:00', '17:00'),
(1, 3, '09:00', '12:00'), (1, 3, '14:00', '17:00'),
(1, 4, '09:00', '12:00'), (1, 4, '14:00', '17:00');

-- Dr. Sharma - Monday, Wednesday, Friday
INSERT INTO doctor_availability (doctor_id, day_of_week, start_time, end_time) VALUES
(2, 0, '10:00', '13:00'), (2, 0, '15:00', '18:00'),
(2, 2, '10:00', '13:00'), (2, 2, '15:00', '18:00'),
(2, 4, '10:00', '13:00'), (2, 4, '15:00', '18:00');

-- Dr. Patel - Tuesday, Thursday, Saturday
INSERT INTO doctor_availability (doctor_id, day_of_week, start_time, end_time) VALUES
(3, 1, '09:00', '12:00'), (3, 1, '14:00', '16:00'),
(3, 3, '09:00', '12:00'), (3, 3, '14:00', '16:00'),
(3, 5, '09:00', '13:00');

-- Insert some sample past appointments
INSERT INTO appointments (doctor_id, patient_id, appointment_date, start_time, end_time, status, reason, created_at) VALUES
(1, 1, CURRENT_DATE - INTERVAL '1 day', '09:00', '09:30', 'completed', 'Fever and cold', NOW() - INTERVAL '2 days'),
(1, 2, CURRENT_DATE - INTERVAL '1 day', '10:00', '10:30', 'completed', 'Regular checkup', NOW() - INTERVAL '2 days'),
(1, 1, CURRENT_DATE - INTERVAL '2 days', '14:00', '14:30', 'completed', 'Follow-up for fever', NOW() - INTERVAL '3 days'),
(2, 1, CURRENT_DATE - INTERVAL '1 day', '10:00', '10:30', 'completed', 'Heart palpitations', NOW() - INTERVAL '2 days'),
(1, 2, CURRENT_DATE, '09:00', '09:30', 'scheduled', 'Headache', NOW() - INTERVAL '1 day'),
(1, 1, CURRENT_DATE + INTERVAL '1 day', '10:00', '10:30', 'scheduled', 'Fever follow-up', NOW())
ON CONFLICT DO NOTHING;
