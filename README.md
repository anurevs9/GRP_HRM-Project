# Human Resources Management System (HRMS)

This project is a web-based **Human Resources Management System (HRMS)** built using the **Django** web framework. It provides features for managing employees, departments, recruitment, payroll, and user authentication.

## Features

## User Authentication

- Login and registration functionality for employees.
- Uses Django's built-in authentication system.
- Distinct user roles (e.g., employee, payroll administrator) implemented using custom decorators and permission checks.

## Employee Management

- CRUD (Create, Read, Update, Delete) operations for employee records.
- Employee profiles with details like name, email, phone, department, etc.

## Department Management

- CRUD operations for departments.
- Departments are linked to employees.
- Admin-only access for department creation and editing.

## Task Management System

### Task Creation and Assignment

- **Task Priority**: A dropdown menu with options: High, Medium, and Low.
- **Assigned To**: Contains the name of the employee to whom the Team Leader, Manager, or Admin wants to assign the task. The dropdown must show only those employees who are reporting to the logged-in user.
- **Task Type**: A dropdown with two options: Individual and Team.

### Dashboard Admin

- **Create Task Button**: Allows the user to create a task and assign it to team members. After creating the task, the user returns to the dashboard.
- **Pagination**: Displays 10 records per screen.
- **Filter by Employee**: Filters tasks to be shown as per the selected employee. The dropdown contains only names of those employees who are reporting to the logged-in user.
- **Filter by Status**: Filters tasks as per the status such as Pending, Completed, and In Progress.
- **See Details Button**: Provides users with a detailed view of the task along with its description.
- **Filter Between Date Ranges**: Works on the start date filter and displays records based on the dates provided in the To and From section.
- **Statistical Section**: Shows the number of completed tasks, pending tasks, and in-progress tasks with respect to the selection either for specific employees or for all employees.
- **Multiple Filters Selection**: Supports multiple filter selections. For example, if a specific employee is selected by the user (Team Leader/Manager/Admin) and the user also clicks on the completed option from the Filter by Status, the dashboard must show the selected employee's completed tasks.

### Dashboard Manager/Team Leader

- Similar functionalities as the Admin Dashboard with appropriate access controls.

### Employee Dashboard

- Displays tasks assigned to the logged-in employee with options to update task status and view task details.

### Update Task Details

- When the User (Admin/TL/Manager) clicks on the edit button, it opens a view to update task details such as Task Title, Task Description, Assigned To, Task Priority, Start Date, End Date, and Task Type.
- After updating task details, the user is directed back to the dashboard.

### Delete Task

- When the User (Admin/TL/Manager) clicks on the delete button, a pop-up provides a warning for deletion with a confirm button to delete the task.

## Recruitment

- Employees can create new job postings.
- Application status tracking (e.g., open, closed, pending).

## Payroll

- Payroll record creation, including basic salary, overtime, bonuses, and deductions.
- Calculation of net salary.
- Integration with Razorpay for payment processing (requires Razorpay account and API keys).
- Automated email notifications to employees upon successful payment, including a detailed salary breakdown (using HTML email templates).
- Role-based access control to restrict payroll processing to authorized personnel.

## Performance Management System

### Add a Review

- This functionality is accessed by Admin/TL/Manager to add review details when a review is being conducted with the team members.
- **Select Employee**: A dropdown that shows a list of only those employees who are reporting to the logged-in Admin/Manager/TL.
- **Review Period**: Contains three options: Monthly, Quarterly, and Annual.

### Admin Dashboard

- Access to all performance reviews and ability to manage them.

### Manager/TL Dashboard

- Similar functionalities as the Admin Dashboard with appropriate access controls.

### Employee Review Dashboard

- Displays performance reviews for the logged-in employee.


## User Roles and Permissions

- Expanded role-based permissions using Django's framework or `django-guardian`.

## Reporting

- Generate reports on employee data, payroll, and recruitment.

## Dashboard

- Displays key metrics and summaries.

## Leave Management System

### Leave Dashboard - Employee

- The dashboard displays all leave balances along with details of all leaves taken.
- Employees can edit leave requests before they are approved by the manager. Once approved, the edit button is disabled.
- Employees cannot delete leave requests. They can request deletion from their reporting manager, admin, or HR department.

### Apply Leave

- By clicking the "Apply Leave" button on the dashboard, the employee is directed to an apply leave form.
- **Select Leave**: A dropdown with three options: PL (Privilege Leave), CL (Casual Leave), and SL (Sick Leave).
- After applying for leave, the user is directed back to their dashboard where the applied leave is visible with a default status of "Pending".
- The applied leave is also visible on the reporting manager's dashboard for approval or rejection.

### Update Leave

- Employees can update the leave status before it is approved or rejected by the reporting manager.
- Employees cannot edit the leave after it has been approved or rejected.
- After updating the leave status, the user is directed back to the dashboard.

### Leave Dashboard - Admin/Manager

- The admin or manager dashboard contains two sections: "Manager/Admin Leave" and "Reportees' Leaves".
- Managers or admins can approve or reject leave requests by clicking the edit button in the "Reportees' Leaves" section.
- After clicking the edit button, a form opens where the manager or admin can approve or reject the leave.

### Leave Balance

- Leave balance is updated according to the leaves consumed by the user.

### Leave Quota Functionality

- Leave quotas for SL, PL, and CL are updated by HR department managers and admins.
- The "Add Leave Quota" button is visible to HR managers and admins.
- Clicking the "Add Leave Quota" button directs the user to a dashboard with a form to add leave quotas for the year for a selected employee from the dropdown.
- The dropdown contains a list of employees.
- Edit functionality is provided to update leave quotas for a particular employee.
- Pagination is used to display a limited number of employees per page.

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
git clone https://github.com/anurevs9/GRP_HRM-Project.git
cd hrm_project
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

This project is actively being developed. Contributions and feedback are welcome! 

