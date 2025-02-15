# Human Resources Management System (HRMS)

This project is a web-based **Human Resources Management System (HRMS)** built using the **Django** web framework. It provides features for managing employees, departments, recruitment, payroll, and user authentication.

## Features

### User Authentication

- Login and registration functionality for employees.
- Uses Django's built-in authentication system.
- Distinct user roles (e.g., employee, payroll administrator) implemented using custom decorators and permission checks.

### Employee Management

- CRUD (Create, Read, Update, Delete) operations for employee records.
- Employee profiles with details like name, email, phone, department, etc.

### Department Management

- CRUD operations for departments.
- Departments are linked to employees.
- Admin-only access for department creation and editing.

### Recruitment

- Employees can create new job postings.
- Application status tracking (e.g., open, closed, pending).

### Payroll

- Payroll record creation, including basic salary, overtime, bonuses, and deductions.
- Calculation of net salary.
- Integration with Razorpay for payment processing (requires Razorpay account and API keys).
- Automated email notifications to employees upon successful payment, including a detailed salary breakdown (using HTML email templates).
- Role-based access control to restrict payroll processing to authorized personnel.

### User Roles and Permissions

- Expanded role-based permissions using Django's framework or `django-guardian`.

### Reporting

- Generate reports on employee data, payroll, and recruitment.

### Dashboard

- Displays key metrics and summaries.

### Leave Management

- Employees can request and manage leave.
- Approval system for HR and managers.

### Performance Management

- Performance reviews and goal-setting features.

## Project Structure

The project follows a standard **Django** structure:

```
project_root/
│── core/         # Main app with authentication, models, forms, views, and base templates
│── hrm/          # HR-specific functionality like recruitment and payroll
│── templates/    # HTML templates organized into subdirectories
│── static/       # Static files (CSS, JavaScript, images)
│── models.py     # Defines database models
│── forms.py      # Defines Django forms for user input
│── views.py      # Handles user requests, models, and forms
│── urls.py       # Defines URL patterns for views
│── decorators.py # Custom decorators for access control
│── utils.py      # Utility functions
```

## Setup and Installation

### Prerequisites

- Python 3.8+
- pip (Python package installer)
- A database (e.g., PostgreSQL, MySQL, SQLite)
- A Razorpay account and API keys (for payroll feature)

### Clone the Repository

```bash
git clone <repository_url>
cd <project_directory>
```

### Create a Virtual Environment (Recommended)

```bash
python3 -m venv venv
source venv/bin/activate  # On Linux/macOS
venv\Scripts\activate  # On Windows
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

*Ensure ********************`requirements.txt`******************** includes:*

```txt
django
razorpay
psycopg2-binary  # If using PostgreSQL
```

### Configure Settings (`settings.py`)

- **Database**: Set up database connection details (`DATABASES` setting).
- **Secret Key**: Generate a new secret key (`SECRET_KEY`).
- **Email Settings**: Configure (`EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, etc.).
- **Razorpay Keys**: Add `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET`.
- **Allowed Hosts**: Add your domain to `ALLOWED_HOSTS`.
- **Static Files**: Configure static file settings.
- **Templates**: Update `TEMPLATES['DIRS']`.
- **Payroll Admin Roles**: Define payroll access roles:
  ```python
  PAYROLL_ADMIN_ROLES = ['Payroll Administrator', 'HR Manager']
  ```

### Run Migrations

```bash
python manage.py migrate
```

### Create a Superuser (for Admin Access)

```bash
python manage.py createsuperuser
```

### Run the Development Server

```bash
python manage.py runserver
```

### Access the Application

Open your web browser and go to:

```
https://anurevsx99.pythonanywhere.com/login-register/
```

## Further Development

### Planned Features

- **Public Posting: Public-facing list of open job postings.**
- **Candidate Role: Candidates can apply for jobs through a dedicated application form.**
- **Document Management**: Enable uploading and managing employee documents.
- **Improved UI/UX**: Enhance the interface with better styling.
- **Testing**: Add unit and integration tests.
- **Deployment**: Deploy to a production server.

---

This project is actively being developed. Contributions and feedback are welcome! 🚀

