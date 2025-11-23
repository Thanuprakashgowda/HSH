
# HostelHub Flask Backend (Python + MySQL)

This is a Flask implementation of the HostelHub issue reporting & maintenance tracking system.

## 1. Requirements

- Python 3 installed
- MySQL Server + MySQL Workbench
- Postman for testing

## 2. Create Database in MySQL

Run this SQL in MySQL Workbench:

```sql
CREATE DATABASE hostelhub;
USE hostelhub;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100),
  email VARCHAR(100) UNIQUE,
  password VARCHAR(255),
  role ENUM('student','admin') DEFAULT 'student'
);

CREATE TABLE complaints (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT,
  title VARCHAR(255),
  description TEXT,
  category VARCHAR(100),
  image VARCHAR(255),
  status ENUM('Open','In Progress','Resolved') DEFAULT 'Open',
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE comments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  complaint_id INT,
  user_id INT,
  message TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (complaint_id) REFERENCES complaints(id),
  FOREIGN KEY (user_id) REFERENCES users(id)
);
```

> Note: If you already created these tables for the Node.js backend, you can reuse the same database.

## 3. Configure DB connection

Open `app.py` and update `DB_CONFIG`:

```python
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "your_password_here",  # change this
    "database": "hostelhub",
}
```

Set your MySQL password (and user if not `root`).

## 4. Create virtual environment (optional but recommended)

On Windows CMD or PowerShell:

```bash
cd path\to\hostelhub-flask-backend
python -m venv venv
venv\Scripts\activate
```

On Linux / Mac:

```bash
python3 -m venv venv
source venv/bin/activate
```

## 5. Install dependencies

```bash
pip install -r requirements.txt
```

## 6. Run the Flask server

From the project folder:

```bash
python app.py
```

You should see:

```
 * Running on http://127.0.0.1:5000
```

## 7. Test APIs with Postman

### 7.1 Register (student/admin)

- Method: POST  
- URL: `http://localhost:5000/auth/register`  
- Body (JSON):

```json
{
  "name": "Alice",
  "email": "alice@example.com",
  "password": "1234",
  "role": "student"
}
```

### 7.2 Login

- Method: POST  
- URL: `http://localhost:5000/auth/login`  
- Body:

```json
{
  "email": "alice@example.com",
  "password": "1234"
}
```

Copy the `token` from the response.

### 7.3 Create complaint (student)

- Method: POST  
- URL: `http://localhost:5000/complaints`  
- Headers:
  - `Authorization: Bearer <token>`
- Body type: `form-data`

| key         | type | value                          |
|------------|------|--------------------------------|
| title      | text | "Water leakage in bathroom"    |
| description| text | "Pipe leaking near sink"       |
| category   | text | "Plumbing"                     |
| image      | file | (optional image file)          |

### 7.4 View my complaints

- Method: GET  
- URL: `http://localhost:5000/complaints/my`  
- Header:
  - `Authorization: Bearer <token>`

### 7.5 Add comment (chat)

- Method: POST  
- URL: `http://localhost:5000/complaints/<complaintId>/comments`  
- Header:
  - `Authorization: Bearer <token>`  
- Body (JSON):

```json
{
  "message": "We are working on this."
}
```

### 7.6 View comments

- Method: GET  
- URL: `http://localhost:5000/complaints/<complaintId>/comments`  
- Header:
  - `Authorization: Bearer <token>`

### 7.7 Admin: view all complaints

- Method: GET  
- URL: `http://localhost:5000/admin/complaints`  
- Header:
  - `Authorization: Bearer <admin_token>`

### 7.8 Admin: update status

- Method: PUT  
- URL: `http://localhost:5000/admin/complaints/<complaintId>/status`  
- Header:
  - `Authorization: Bearer <admin_token>`  
- Body:

```json
{
  "status": "In Progress"
}
```

### 7.9 Admin: analytics (L3)

- Method: GET  
- URL: `http://localhost:5000/admin/analytics/summary`  
- Header:
  - `Authorization: Bearer <admin_token>`

This Flask backend gives you:

- Student & Admin login/registration
- Raise complaint with category + image
- View complaint history
- Comment/chat between student and admin
- Status management (Open → In Progress → Resolved)
- Basic analytics for hackathon Level 3
