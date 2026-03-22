# Student Management System (SMS)

A comprehensive web-based Student Management System built with Django (Python) for backend development and HTML, CSS, JavaScript, and Bootstrap for frontend design. This system serves as a centralized digital platform for managing academic, administrative, and communication processes within educational institutions.

## 🔒 **Security Improvements Made:**

### **Removed Public Registration**
- ❌ Removed the public registration route and form
- ❌ Removed registration links from login page
- ✅ Only admins can now create user accounts

### **Admin-Only User Management**
- ✅ **Create Users**: Admins can create accounts for students, teachers, and parents
- ✅ **Edit Users**: Full user profile editing capabilities
- ✅ **Reset Passwords**: Secure password reset with strong password generation
- ✅ **Delete Users**: Secure user deletion with confirmation
- ✅ **User List**: Comprehensive user management interface with search and filtering
- ✅ **Role-Based Access**: Only admins can access user management features

### **Enhanced Admin Dashboard**
- ✅ Real-time statistics (student, teacher, parent counts)
- ✅ Quick access to user management functions
- ✅ Recent user activity tracking
- ✅ Improved navigation with user management dropdown

### **Security Features**
- ✅ **Permission Checks**: `@user_passes_test(is_admin)` decorator ensures only admins can manage users
- ✅ **Password Management**: Admins can reset user passwords with strong password generation
- ✅ **Form Security**: Password fields are optional for editing (admins don't need to reset passwords unless required)
- ✅ **Confirmation Dialogs**: Delete operations require explicit confirmation
- ✅ **Audit Trail**: Track when users were created and by whom

### **User Experience Improvements**
- ✅ **Search & Filter**: Find users by name, username, email, or user type
- ✅ **Pagination**: Handle large numbers of users efficiently
- ✅ **Visual Indicators**: Clear badges for user types and status
- ✅ **Profile Pictures**: Support for user profile images
- ✅ **Responsive Design**: Works on all device sizes

## 🎯 **Current System Flow:**

1. **Admin Login** → Access admin dashboard
2. **User Creation** → Admin creates accounts for students/teachers/parents
3. **User Management** → Edit, delete, or reset passwords for existing users
4. **Role-Based Access** → Each user type gets appropriate dashboard and permissions

The system now follows proper institutional security practices where only authorized administrators can manage user accounts, making it suitable for real educational institutions.

---

## 🚀 Features

### 👥 Multi-Role Access System
- **Admin**: Full system control, user management, and system administration
- **Student**: Academic progress tracking and information access
- **Teacher**: Class management and student evaluation
- **Parent**: Child's academic progress monitoring

**Note**: Only administrators can create new user accounts. There is no public registration system.

### 🔐 Authentication & Authorization
- Role-based login system (no public registration)
- Admin-only user creation and management
- Secure password encryption
- Session management
- Permission-based access control
- Role-based dashboard redirection

### 📚 Academic Management
- Department management
- Course management
- Subject management
- Class allocation
- Teacher assignment
- Student enrollment

### 🧑‍💼 Admin User Management
- Create new users for all roles (Student, Teacher, Parent)
- Edit existing user information and profiles
- Reset user passwords with strong password generation
- Delete users with confirmation dialogs
- Search and filter users by type and criteria
- Bulk user management capabilities
- User status management (active/inactive)
- Profile picture management
- Automatic ID generation for students and employees
### 🧑‍🎓 Student Management
- Student profile management (admin-created accounts)
- Academic records tracking
- Parent linking
- Status tracking (active/inactive)

### 🧑‍🏫 Teacher Management
- Teacher profile management (admin-created accounts)
- Department linking
- Subject assignment
- Schedule management

### 🕒 Attendance System
- Daily attendance tracking
- Class-wise attendance
- Student attendance history
- Reports and analytics

### 📝 Examination & Grading
- Exam scheduling
- Grade entry and management
- Result generation
- Report cards
- Performance analytics

### 🔔 Notification System
- System alerts and notifications
- Academic reminders
- Exam alerts
- Attendance warnings

### 🔐 Password Management
- Admin-controlled password resets
- Strong password generation
- Password visibility toggle
- Copy password to clipboard functionality

## 🛠️ Technology Stack

- **Backend**: Django 4.2.7 (Python)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5
- **Database**: SQLite (default, easily configurable to PostgreSQL/MySQL)
- **UI Framework**: Bootstrap 5 with custom CSS
- **Forms**: Django Crispy Forms with Bootstrap 5
- **Icons**: Font Awesome 6
- **Additional Libraries**: 
  - Pillow (image handling)
  - ReportLab (PDF generation)
  - OpenPyXL (Excel export)

## 📋 Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## 🚀 Installation & Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd student-project
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run database migrations**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

4. **Create an admin user**
   ```bash
   python manage.py create_admin
   ```
   Or create with parameters:
   ```bash
   python manage.py create_admin --username admin --email admin@sms.com --password admin123
   ```

5. **Create sample data (optional)**
   ```bash
   python manage.py create_sample_data
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   - Open your browser and go to `http://127.0.0.1:8000/`
   - You'll be redirected to the login page

## 👤 Default User Accounts

After running `create_sample_data`, you can use these accounts:

| Role | Username | Password | Description |
|------|----------|----------|-------------|
| Admin | admin | admin123 | System administrator |
| Teacher | teacher1 | teacher123 | Sample teacher account |
| Student | student1 | student123 | Sample student account |
| Parent | parent1 | parent123 | Sample parent account |

## 📁 Project Structure

```
student-project/
├── student_management_system/    # Main project settings
├── accounts/                     # User authentication and profiles
├── academic/                     # Academic management (departments, courses, subjects)
├── attendance/                   # Attendance tracking system
├── examination/                  # Examination and grading system
├── notifications/                # Notification system
├── templates/                    # HTML templates
├── static/                       # Static files (CSS, JS, images)
├── media/                        # User uploaded files
├── requirements.txt              # Python dependencies
└── manage.py                     # Django management script
```

## 🎨 User Interface

### Dashboard Features by Role

#### Admin Dashboard
- System statistics overview
- User creation and management interface
- Quick actions for system administration
- Recent activities tracking
- Department and course management links
- Complete user lifecycle management

#### Student Dashboard
- Personal profile overview
- Academic performance tracking
- Upcoming exams and assignments
- Attendance summary
- Recent grades display

#### Teacher Dashboard
- Today's class schedule
- Quick attendance marking
- Student performance overview
- Exam management tools
- Notification sending capabilities

#### Parent Dashboard
- Children's academic progress
- Attendance monitoring
- Exam schedules and results
- Communication with teachers
- Performance analytics

## 🔧 Configuration

### Database Configuration
The system uses SQLite by default. To use PostgreSQL or MySQL, update the `DATABASES` setting in `settings.py`:

```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_db_name',
        'USER': 'your_db_user',
        'PASSWORD': 'your_db_password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Email Configuration
Update email settings in `settings.py` for notification functionality:

```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'your-smtp-server.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@example.com'
EMAIL_HOST_PASSWORD = 'your-email-password'
```

## 📊 Key Models

### User Management
- **User**: Extended Django user model with role-based access
- **StudentProfile**: Student-specific information
- **TeacherProfile**: Teacher-specific information
- **ParentProfile**: Parent-specific information
- **AdminProfile**: Administrator-specific information

### Academic Management
- **Department**: Academic departments
- **Course**: Degree programs
- **Subject**: Individual subjects/courses
- **Class**: Class sections
- **StudentEnrollment**: Student-class relationships
- **TeacherSubjectAssignment**: Teacher-subject assignments

### Attendance & Examination
- **AttendanceRecord**: Daily attendance tracking
- **AttendanceSummary**: Monthly attendance summaries
- **Examination**: Exam scheduling and details
- **ExamResult**: Student exam results and grades

## 🚀 Future Enhancements

- [ ] Real-time notifications with WebSockets
- [ ] Mobile application (React Native/Flutter)
- [ ] Advanced reporting and analytics
- [ ] Fee management system
- [ ] Library management integration
- [ ] Timetable management
- [ ] Online examination system
- [ ] Parent-teacher communication portal
- [ ] Student assignment submission system
- [ ] Hostel management system

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Support

For support and questions, please contact:
- Email: support@sms.com
- Documentation: [Project Wiki](link-to-wiki)
- Issues: [GitHub Issues](link-to-issues)

## 🙏 Acknowledgments

- Django community for the excellent framework
- Bootstrap team for the responsive UI framework
- Font Awesome for the beautiful icons
- All contributors who helped make this project better

---

**Note**: This is a educational/demonstration project. For production use, please ensure proper security measures, testing, and deployment configurations are in place.