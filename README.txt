Human Resources Management System (HRMS)

This project is a web-based Human Resources Management System (HRMS) built using the Django web framework. It provides features for managing employees, departments, recruitment, payroll, and user authentication.



Features

The HRMS currently includes the following core features:

User Authentication:
    Login and registration functionality for employees.
    Uses Django's built-in authentication system.
    Distinct user roles (e.g., employee, payroll administrator) are implemented using custom decorators and permission checks.

Employee Management:
    CRUD (Create, Read, Update, Delete) operations for employee records.
    Employee profiles with details like name, email, phone, department, etc.

Department Management:
    CRUD operations for departments.
    Departments are linked to employees.
    Admin-only access for department creation and editing.

Recruitment:
    Employees can create new job postings (recruitments).
    Public-facing list of open job postings.
    Candidates can apply for jobs through a dedicated application form.
    Employees can view a list of candidates who have applied for each position.
    Application status tracking (e.g., open, closed, pending).

Payroll:
    Payroll record creation, including basic salary, overtime, bonuses, and deductions.
    Calculation of net salary.
    Integration with Razorpay for payment processing (requires Razorpay account and API keys).
    Automated email notifications to employees upon successful payment, including a detailed salary breakdown (using HTML email templates).
    Role-based access control to restrict payroll processing to authorized personnel.





Project Structure

The project follows a standard Django structure:

core: 
	(Likely the main app) Contains core functionality, including user authentication, models, forms, views, and URL patterns. It likely contains the base template (base.html).


hrm: 
	(Likely an app) Contains HR-specific functionality, such as recruitment and payroll management, including corresponding models, views, forms, and templates.

templates: 
	Contains HTML templates for all views. The templates are organized into subdirectories corresponding to the apps (e.g., hrm/recruitment, hrm/payroll, core).

static: 
	(Not explicitly shown in the code, but standard) Contains static files like CSS, JavaScript, and images.
models.py: Defines the database models (e.g., Employee, Department, Recruitment, Candidate, Payroll).

forms.py: 
	Defines Django forms for user input (e.g., LoginForm, SignupForm, RecruitmentForm, CandidateForm, PayrollForm, DepartmentForm).
views.py: Contains view functions that handle user requests and interact with models and forms.

urls.py: 
	Defines URL patterns that map URLs to views.
decorators.py: (Probably in core) Contains custom decorators, like @employee_required, to restrict access to views based on user roles.

utils.py: Contains utility, such as checking for admin status.





Setup and Installation

Prerequisites:
    Python 3.8+
    pip (Python package installer)
    A database (e.g., PostgreSQL, MySQL, SQLite - SQLite is suitable for development).
    A Razorpay account and API keys (if using the payroll feature with payment processing).



Clone the repository:

```bash
git clone <repository_url>
cd <project_directory>



create a virtual environment (recommended):

python3 -m venv venv
source venv/bin/activate  # On Linux/macOS
venv\Scripts\activate  # On Windows
Use code with caution.
Bash


Install dependencies:

pip install -r requirements.txt
Use code with caution.
Bash
(You'll need to create a requirements.txt file listing all project dependencies, including Django, Razorpay, and any other libraries you're using. For example:

django
 razorpay
 psycopg2-binary  # If using PostgreSQL
Use code with caution.
)




Configure settings (settings.py):

Database: 
	Set up your database connection details (DATABASES setting).
Secret Key: Generate a new secret key (SECRET_KEY).

Email Settings:
	 Configure email settings (EMAIL_BACKEND, EMAIL_HOST, EMAIL_PORT, etc.) for sending emails. Use the console backend for development.

Razorpay Keys: 
	Add your Razorpay API key ID and secret (RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET).

Allowed Hosts: Add your domain to the allowed hosts.

Static files: 
	Configure static files collection settings.

Templates: Configure DIRS in TEMPLATES.

PAYROLL_ADMIN_ROLES:
	 Define this setting as a list of role names that have payroll access (e.g., PAYROLL_ADMIN_ROLES = ['Payroll Administrator', 'HR Manager']).



Run migrations:

python manage.py migrate

Bash
Create a superuser (for initial admin access):

python manage.py createsuperuser

Bash
Run the development server:

python manage.py runserver

Bash
Access the application: Open your web browser and go to http://127.0.0.1:8000/ (or the address shown in the console).

Further Development

User Roles and Permissions: 
	Expand the user role system with more granular permissions (e.g., using Django's built-in permissions framework or a third-party library like django-guardian).

Reporting: 
	Add reporting features to generate reports on employee data, payroll, recruitment, etc.

Dashboard: 
	Create a dashboard to display key metrics and summaries.

Leave Management: Implement a system for employees to request and manage leave.

Performance Management: Add features for performance reviews and goal setting.

Document Management: Allow storing and managing employee-related documents.

Improved UI/UX: Enhance the user interface and user experience with more interactive elements and better styling.

Testing: Write comprehensive unit and integration tests to ensure code quality and prevent regressions.

Deployment: Deploy to a production server environment.

