from django.core.management.base import BaseCommand, CommandError

from academic.models import (
    AcademicYear,
    Assignment,
    AssignmentSubmission,
    Class,
    Course,
    Department,
    SemesterEnrollment,
    StudentEnrollment,
    Subject,
    TeacherSubjectAssignment,
)
from attendance.models import (
    AttendanceRecord,
    AttendanceSession,
    AttendanceSummary,
    GeofenceLocation,
    TeacherActivityLog,
    TeacherAttendance,
    TeacherLeave,
    TeacherSchedule,
)
from accounts.models import User
from saas.models import Organization


class Command(BaseCommand):
    help = 'Assign existing unscoped users and academic records to an organization.'

    def add_arguments(self, parser):
        parser.add_argument('--slug', required=True, help='Target organization slug')
        parser.add_argument(
            '--include-users',
            action='store_true',
            help='Assign users with no organization to the target organization.',
        )

    def handle(self, *args, **options):
        try:
            organization = Organization.objects.get(slug=options['slug'])
        except Organization.DoesNotExist as exc:
            raise CommandError(f'Organization "{options["slug"]}" does not exist.') from exc

        updated_counts = {}

        if options['include_users']:
            updated_counts['users'] = User.objects.filter(organization__isnull=True).update(organization=organization)

        academic_models = [
            AcademicYear,
            Department,
            Course,
            Subject,
            Class,
            StudentEnrollment,
            SemesterEnrollment,
            TeacherSubjectAssignment,
            Assignment,
            AssignmentSubmission,
        ]

        for model in academic_models:
            updated_counts[model.__name__] = model.objects.filter(organization__isnull=True).update(organization=organization)

        attendance_models = [
            AttendanceSession,
            AttendanceRecord,
            AttendanceSummary,
            TeacherSchedule,
            TeacherAttendance,
            TeacherActivityLog,
            TeacherLeave,
            GeofenceLocation,
        ]

        for model in attendance_models:
            updated_counts[model.__name__] = model.objects.filter(organization__isnull=True).update(organization=organization)

        for label, count in updated_counts.items():
            self.stdout.write(f'{label}: {count}')

        self.stdout.write(self.style.SUCCESS(f'Assigned existing unscoped data to organization {organization.slug}.'))