let subjectCounter = 0;
let classCounter = 0;
let studentCounter = 0;

// Get data from Django
const academicYears = window.academicYearsData || [];
const teachers = window.teachersData || [];
const students = window.studentsData || [];

function addSubject() {
    const container = document.getElementById('subjects-container');
    const subjectHtml = 
        '<div class="dynamic-form-row position-relative" id="subject-' + subjectCounter + '">' +
            '<button type="button" class="btn btn-sm btn-outline-danger remove-btn" onclick="removeElement(\'subject-' + subjectCounter + '\')">' +
                '<i class="fas fa-times"></i>' +
            '</button>' +
            '<div class="row">' +
                '<div class="col-md-6">' +
                    '<div class="mb-3">' +
                        '<label class="form-label">Subject Name *</label>' +
                        '<input type="text" name="subject_name_' + subjectCounter + '" class="form-control" required>' +
                    '</div>' +
                '</div>' +
                '<div class="col-md-6">' +
                    '<div class="mb-3">' +
                        '<label class="form-label">Subject Code *</label>' +
                        '<input type="text" name="subject_code_' + subjectCounter + '" class="form-control" required>' +
                    '</div>' +
                '</div>' +
            '</div>' +
            '<div class="row">' +
                '<div class="col-md-4">' +
                    '<div class="mb-3">' +
                        '<label class="form-label">Year *</label>' +
                        '<select name="subject_year_' + subjectCounter + '" class="form-select" required>' +
                            '<option value="">Select Year</option>' +
                            '<option value="1">1st Year</option>' +
                            '<option value="2">2nd Year</option>' +
                            '<option value="3">3rd Year</option>' +
                            '<option value="4">4th Year</option>' +
                            '<option value="5">5th Year</option>' +
                            '<option value="6">6th Year</option>' +
                        '</select>' +
                    '</div>' +
                '</div>' +
                '<div class="col-md-4">' +
                    '<div class="mb-3">' +
                        '<label class="form-label">Semester *</label>' +
                        '<select name="subject_semester_' + subjectCounter + '" class="form-select" required>' +
                            '<option value="">Select Semester</option>' +
                            '<option value="1">1st Semester</option>' +
                            '<option value="2">2nd Semester</option>' +
                        '</select>' +
                    '</div>' +
                '</div>' +
                '<div class="col-md-4">' +
                    '<div class="mb-3">' +
                        '<label class="form-label">Credits</label>' +
                        '<input type="number" name="subject_credits_' + subjectCounter + '" class="form-control" min="1" max="10" value="3">' +
                    '</div>' +
                '</div>' +
            '</div>' +
        '</div>';
    container.insertAdjacentHTML('beforeend', subjectHtml);
    subjectCounter++;
}

function addClass() {
    const container = document.getElementById('classes-container');
    
    let academicYearOptions = '<option value="">Select Academic Year</option>';
    academicYears.forEach(year => {
        academicYearOptions += '<option value="' + year.id + '">' + year.year + '</option>';
    });
    
    let teacherOptions = '<option value="">Select Class Teacher</option>';
    teachers.forEach(teacher => {
        teacherOptions += '<option value="' + teacher.id + '">' + teacher.name + '</option>';
    });
    
    const classHtml = 
        '<div class="dynamic-form-row position-relative" id="class-' + classCounter + '">' +
            '<button type="button" class="btn btn-sm btn-outline-danger remove-btn" onclick="removeElement(\'class-' + classCounter + '\')">' +
                '<i class="fas fa-times"></i>' +
            '</button>' +
            '<div class="row">' +
                '<div class="col-md-6">' +
                    '<div class="mb-3">' +
                        '<label class="form-label">Class Name *</label>' +
                        '<input type="text" name="class_name_' + classCounter + '" class="form-control" required>' +
                    '</div>' +
                '</div>' +
                '<div class="col-md-6">' +
                    '<div class="mb-3">' +
                        '<label class="form-label">Section *</label>' +
                        '<input type="text" name="class_section_' + classCounter + '" class="form-control" placeholder="A, B, C, etc." required>' +
                    '</div>' +
                '</div>' +
            '</div>' +
            '<div class="row">' +
                '<div class="col-md-3">' +
                    '<div class="mb-3">' +
                        '<label class="form-label">Year *</label>' +
                        '<select name="class_year_' + classCounter + '" class="form-select" required>' +
                            '<option value="">Select Year</option>' +
                            '<option value="1">1st Year</option>' +
                            '<option value="2">2nd Year</option>' +
                            '<option value="3">3rd Year</option>' +
                            '<option value="4">4th Year</option>' +
                            '<option value="5">5th Year</option>' +
                            '<option value="6">6th Year</option>' +
                        '</select>' +
                    '</div>' +
                '</div>' +
                '<div class="col-md-3">' +
                    '<div class="mb-3">' +
                        '<label class="form-label">Semester *</label>' +
                        '<select name="class_semester_' + classCounter + '" class="form-select" required>' +
                            '<option value="">Select Semester</option>' +
                            '<option value="1">1st Semester</option>' +
                            '<option value="2">2nd Semester</option>' +
                        '</select>' +
                    '</div>' +
                '</div>' +
                '<div class="col-md-3">' +
                    '<div class="mb-3">' +
                        '<label class="form-label">Academic Year *</label>' +
                        '<select name="class_academic_year_' + classCounter + '" class="form-select" required>' +
                            academicYearOptions +
                        '</select>' +
                    '</div>' +
                '</div>' +
                '<div class="col-md-3">' +
                    '<div class="mb-3">' +
                        '<label class="form-label">Class Teacher</label>' +
                        '<select name="class_teacher_' + classCounter + '" class="form-select">' +
                            teacherOptions +
                        '</select>' +
                    '</div>' +
                '</div>' +
            '</div>' +
        '</div>';
    container.insertAdjacentHTML('beforeend', classHtml);
    classCounter++;
    
    // Show student enrollment section when first class is added
    if (classCounter === 1) {
        document.querySelector('.student-enrollment-section').style.display = 'block';
    }
    
    updateStudentClassOptions();
}

function addStudent() {
    const container = document.getElementById('students-container');
    
    let studentOptions = '<option value="">Select Student</option>';
    students.forEach(student => {
        studentOptions += '<option value="' + student.id + '">' + student.name + ' (' + student.student_id + ')</option>';
    });
    
    let classOptions = getClassOptions();
    
    const studentHtml = 
        '<div class="dynamic-form-row position-relative" id="student-' + studentCounter + '">' +
            '<button type="button" class="btn btn-sm btn-outline-danger remove-btn" onclick="removeElement(\'student-' + studentCounter + '\')">' +
                '<i class="fas fa-times"></i>' +
            '</button>' +
            '<div class="row">' +
                '<div class="col-md-6">' +
                    '<div class="mb-3">' +
                        '<label class="form-label">Student *</label>' +
                        '<select name="student_' + studentCounter + '" class="form-select" required>' +
                            studentOptions +
                        '</select>' +
                    '</div>' +
                '</div>' +
                '<div class="col-md-6">' +
                    '<div class="mb-3">' +
                        '<label class="form-label">Enroll in Class *</label>' +
                        '<select name="student_class_' + studentCounter + '" class="form-select student-class-select" required>' +
                            classOptions +
                        '</select>' +
                    '</div>' +
                '</div>' +
            '</div>' +
        '</div>';
    container.insertAdjacentHTML('beforeend', studentHtml);
    studentCounter++;
}

function getClassOptions() {
    let classOptions = '<option value="">Select Class</option>';
    
    // Get all class forms that are currently in the DOM
    const classElements = document.querySelectorAll('[id^="class-"]');
    classElements.forEach((element, index) => {
        const classNameInput = element.querySelector('input[name^="class_name_"]');
        const classSectionInput = element.querySelector('input[name^="class_section_"]');
        const classYearSelect = element.querySelector('select[name^="class_year_"]');
        const classSemesterSelect = element.querySelector('select[name^="class_semester_"]');
        
        if (classNameInput && classSectionInput && classYearSelect && classSemesterSelect) {
            const className = classNameInput.value || 'New Class';
            const section = classSectionInput.value || 'A';
            const year = classYearSelect.value || '1';
            const semester = classSemesterSelect.value || '1';
            
            classOptions += '<option value="temp_' + index + '">' + className + ' - Year ' + year + ', Sem ' + semester + ' - ' + section + '</option>';
        }
    });
    
    return classOptions;
}

function updateStudentClassOptions() {
    const classOptions = getClassOptions();
    const studentClassSelects = document.querySelectorAll('.student-class-select');
    
    studentClassSelects.forEach(select => {
        const currentValue = select.value;
        select.innerHTML = classOptions;
        if (currentValue) {
            select.value = currentValue;
        }
    });
}

function removeElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.remove();
        
        // Hide student enrollment section if no classes exist
        const classElements = document.querySelectorAll('[id^="class-"]');
        if (classElements.length === 0) {
            document.querySelector('.student-enrollment-section').style.display = 'none';
            // Clear all student enrollments
            document.getElementById('students-container').innerHTML = '';
            studentCounter = 0;
        }
        
        updateStudentClassOptions();
    }
}

// Add initial subject and class
document.addEventListener('DOMContentLoaded', function() {
    addSubject();
    addClass();
});

// Update class options when class details change
document.addEventListener('input', function(e) {
    if (e.target.matches('input[name^="class_name_"], input[name^="class_section_"], select[name^="class_year_"], select[name^="class_semester_"]')) {
        updateStudentClassOptions();
    }
});

// Form submission handling
document.getElementById('courseForm').addEventListener('submit', function(e) {
    // Update student class selections with actual class indices
    const studentClassSelects = document.querySelectorAll('.student-class-select');
    studentClassSelects.forEach(select => {
        if (select.value.startsWith('temp_')) {
            const tempIndex = select.value.replace('temp_', '');
            select.value = tempIndex;
        }
    });
});