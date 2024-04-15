"""
models.py

This module is used to register django models
"""

import django
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.db import models
from django.contrib.auth.models import User
from horilla.models import HorillaModel
from horilla_audit.models import HorillaAuditInfo, HorillaAuditLog
from base.horilla_company_manager import HorillaCompanyManager
from base.thread_local_middleware import _thread_locals

# Create your models here.


def validate_time_format(value):
    """
    this method is used to validate the format of duration like fields.
    """
    if len(value) > 6:
        raise ValidationError(_("Invalid format, it should be HH:MM format"))
    try:
        hour, minute = value.split(":")
        hour = int(hour)
        minute = int(minute)
        if len(str(hour)) > 3 or minute not in range(60):
            raise ValidationError(_("Invalid time, excepted HH:MM"))
    except ValueError as e:
        raise ValidationError(_("Invalid format,  excepted HH:MM")) from e


def clear_messages(request):
    storage = messages.get_messages(request)
    for message in storage:
        pass


class Company(HorillaModel):
    """
    Company model
    """

    company = models.CharField(max_length=50)
    hq = models.BooleanField(default=False)
    address = models.TextField(max_length=255)
    country = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    zip = models.CharField(max_length=20)
    icon = models.FileField(
        upload_to="base/icon",
        null=True,
    )
    objects = models.Manager()
    date_format = models.CharField(max_length=30, blank=True, null=True)
    time_format = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Company")
        verbose_name_plural = _("Companies")
        unique_together = ["company", "address"]
        app_label = "base"

    def __str__(self) -> str:
        return str(self.company)


class Department(HorillaModel):
    """
    Department model
    """

    department = models.CharField(max_length=50, blank=False)
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))

    objects = HorillaCompanyManager()

    class Meta:
        verbose_name = _("Department")
        verbose_name_plural = _("Departments")

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        request = getattr(_thread_locals, "request", None)
        if request and request.POST:
            company = request.POST.getlist("company_id", None)
            department = request.POST.get("department", None)
            if (
                Department.objects.filter(
                    company_id__id__in=company, department=department
                )
                .exclude(id=self.id)
                .exists()
            ):
                raise ValidationError("This department already exists in this company")
        return

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.clean(*args, **kwargs)
        return self

    def __str__(self):
        return str(self.department)


class JobPosition(HorillaModel):
    """
    JobPosition model
    """

    job_position = models.CharField(max_length=50, blank=False, null=False, unique=True)
    department_id = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="job_position",
        verbose_name=_("Department"),
    )
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))

    objects = HorillaCompanyManager("department_id__company_id")

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Job Position")
        verbose_name_plural = _("Job Positions")

    def __str__(self):
        return str(self.job_position)


class JobRole(HorillaModel):
    """JobRole model"""

    job_position_id = models.ForeignKey(
        JobPosition, on_delete=models.PROTECT, verbose_name=_("Job Position")
    )
    job_role = models.CharField(max_length=50, blank=False, null=True)
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))

    objects = HorillaCompanyManager("job_position_id__department_id__company_id")

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Job Role")
        verbose_name_plural = _("Job Roles")
        unique_together = ("job_position_id", "job_role")

    def __str__(self):
        return f"{self.job_role} - {self.job_position_id.job_position}"


class WorkType(HorillaModel):
    """
    WorkType model
    """

    work_type = models.CharField(max_length=50)
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))

    objects = HorillaCompanyManager()

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Work Type")
        verbose_name_plural = _("Work Types")

    def __str__(self) -> str:
        return str(self.work_type)

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        request = getattr(_thread_locals, "request", None)
        if request and request.POST:
            company = request.POST.getlist("company_id", None)
            work_type = request.POST.get("work_type", None)
            if (
                WorkType.objects.filter(company_id__id__in=company, work_type=work_type)
                .exclude(id=self.id)
                .exists()
            ):
                raise ValidationError("This work type already exists in this company")
        return

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.clean(*args, **kwargs)
        return self


class RotatingWorkType(HorillaModel):
    """
    RotatingWorkType model
    """

    name = models.CharField(max_length=50)
    work_type1 = models.ForeignKey(
        WorkType,
        on_delete=models.PROTECT,
        related_name="work_type1",
        verbose_name=_("Work Type 1"),
    )
    work_type2 = models.ForeignKey(
        WorkType,
        on_delete=models.PROTECT,
        related_name="work_type2",
        verbose_name=_("Work Type 2"),
    )
    employee_id = models.ManyToManyField(
        "employee.Employee",
        through="RotatingWorkTypeAssign",
        verbose_name=_("Employee"),
    )
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Rotating Work Type")
        verbose_name_plural = _("Rotating Work Types")

    def __str__(self) -> str:
        return str(self.name)

    def clean(self):
        if self.work_type1 == self.work_type2:
            raise ValidationError(_("Choose different work type"))


DAY_DATE = [(str(i), str(i)) for i in range(1, 32)]
DAY_DATE.append(("last", _("Last Day")))
DAY = [
    ("monday", _("Monday")),
    ("tuesday", _("Tuesday")),
    ("wednesday", _("Wednesday")),
    ("thursday", _("Thursday")),
    ("friday", _("Friday")),
    ("saturday", _("Saturday")),
    ("sunday", _("Sunday")),
]
BASED_ON = [
    ("after", _("After")),
    ("weekly", _("Weekend")),
    ("monthly", _("Monthly")),
]


class RotatingWorkTypeAssign(HorillaModel):
    """
    RotatingWorkTypeAssign model
    """

    employee_id = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        null=True,
        verbose_name=_("Employee"),
    )
    rotating_work_type_id = models.ForeignKey(
        RotatingWorkType, on_delete=models.PROTECT, verbose_name=_("Rotating Work Type")
    )
    start_date = models.DateField(
        default=django.utils.timezone.now, verbose_name=_("Start Date")
    )
    next_change_date = models.DateField(null=True, verbose_name=_("Next Switch"))
    current_work_type = models.ForeignKey(
        WorkType,
        null=True,
        on_delete=models.PROTECT,
        related_name="current_work_type",
        verbose_name=_("Current Work Type"),
    )
    next_work_type = models.ForeignKey(
        WorkType,
        null=True,
        on_delete=models.PROTECT,
        related_name="next_work_type",
        verbose_name=_("Next Work Type"),
    )
    based_on = models.CharField(
        max_length=10,
        choices=BASED_ON,
        null=False,
        blank=False,
        verbose_name=_("Based On"),
    )
    rotate_after_day = models.IntegerField(
        default=7, verbose_name=_("Rotate After Day")
    )
    rotate_every_weekend = models.CharField(
        max_length=10,
        default="monday",
        choices=DAY,
        blank=True,
        null=True,
        verbose_name=_("Rotate Every Weekend"),
    )
    rotate_every = models.CharField(
        max_length=10,
        default="1",
        choices=DAY_DATE,
        verbose_name=_("Rotate Every Month"),
    )

    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Rotating Work Type Assign")
        verbose_name_plural = _("Rotating Work Type Assigns")
        ordering = ["-next_change_date", "-employee_id__employee_first_name"]

    def clean(self):
        if self.is_active and self.employee_id is not None:
            # Check if any other active record with the same parent already exists
            siblings = RotatingWorkTypeAssign.objects.filter(
                is_active=True, employee_id=self.employee_id
            )
            if siblings.exists() and siblings.first().id != self.id:
                raise ValidationError(_("Only one active record allowed per employee"))
        if self.start_date < django.utils.timezone.now().date():
            raise ValidationError(_("Date must be greater than or equal to today"))


class EmployeeType(HorillaModel):
    """
    EmployeeType model
    """

    employee_type = models.CharField(max_length=50)
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))

    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Employee Type")
        verbose_name_plural = _("Employee Types")

    def __str__(self) -> str:
        return str(self.employee_type)

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        request = getattr(_thread_locals, "request", None)
        if request and request.POST:
            company = request.POST.getlist("company_id", None)
            employee_type = request.POST.get("employee_type", None)
            if (
                EmployeeType.objects.filter(
                    company_id__id__in=company, employee_type=employee_type
                )
                .exclude(id=self.id)
                .exists()
            ):
                raise ValidationError(
                    "This employee type already exists in this company"
                )
        return

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.clean(*args, **kwargs)
        return self


class EmployeeShiftDay(models.Model):
    """
    EmployeeShiftDay model
    """

    day = models.CharField(max_length=20, choices=DAY)
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))

    objects = HorillaCompanyManager()

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Employee Shift Day")
        verbose_name_plural = _("Employee Shift Days")

    def __str__(self) -> str:
        return str(_(self.day).capitalize())


class EmployeeShift(HorillaModel):
    """
    EmployeeShift model
    """

    employee_shift = models.CharField(
        max_length=50,
        null=False,
        blank=False,
    )
    days = models.ManyToManyField(EmployeeShiftDay, through="EmployeeShiftSchedule")
    weekly_full_time = models.CharField(
        max_length=6,
        default="40:00",
        null=True,
        blank=True,
        validators=[validate_time_format],
    )
    full_time = models.CharField(
        max_length=6, default="200:00", validators=[validate_time_format]
    )
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))
    grace_time_id = models.ForeignKey(
        "attendance.GraceTime",
        null=True,
        blank=True,
        related_name="employee_shift",
        on_delete=models.PROTECT,
        verbose_name=_("Grace Time"),
    )

    objects = HorillaCompanyManager("employee_shift__company_id")

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Employee Shift")
        verbose_name_plural = _("Employee Shifts")

    def __str__(self) -> str:
        return str(self.employee_shift)

    def clean(self, *args, **kwargs):
        super().clean(*args, **kwargs)
        request = getattr(_thread_locals, "request", None)
        if request and request.POST:
            company = request.POST.getlist("company_id", None)
            employee_shift = request.POST.get("employee_shift", None)
            if (
                EmployeeShift.objects.filter(
                    company_id__id__in=company, employee_shift=employee_shift
                )
                .exclude(id=self.id)
                .exists()
            ):
                raise ValidationError(
                    "This employee shift already exists in this company"
                )
        return

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.clean(*args, **kwargs)
        return self


class EmployeeShiftSchedule(HorillaModel):
    """
    EmployeeShiftSchedule model
    """

    day = models.ForeignKey(
        EmployeeShiftDay, on_delete=models.PROTECT, related_name="day_schedule"
    )
    shift_id = models.ForeignKey(
        EmployeeShift, on_delete=models.PROTECT, verbose_name=_("Shift")
    )
    minimum_working_hour = models.CharField(
        default="08:15", max_length=5, validators=[validate_time_format]
    )
    start_time = models.TimeField(null=True)
    end_time = models.TimeField(null=True)
    is_night_shift = models.BooleanField(default=False)
    company_id = models.ManyToManyField(Company, blank=True, verbose_name=_("Company"))

    objects = HorillaCompanyManager("shift_id__employee_shift__company_id")

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Employee Shift Schedule")
        verbose_name_plural = _("Employee Shift Schedules")
        unique_together = [["shift_id", "day"]]

    def __str__(self) -> str:
        return f"{self.shift_id.employee_shift} {self.day}"

    def save(self, *args, **kwargs):
        if self.start_time and self.end_time:
            self.is_night_shift = self.start_time > self.end_time
        super().save(*args, **kwargs)


class RotatingShift(HorillaModel):
    """
    RotatingShift model
    """

    name = models.CharField(max_length=50)
    employee_id = models.ManyToManyField(
        "employee.Employee", through="RotatingShiftAssign", verbose_name=_("Employee")
    )
    shift1 = models.ForeignKey(
        EmployeeShift,
        related_name="shift1",
        on_delete=models.PROTECT,
        verbose_name=_("Shift 1"),
    )
    shift2 = models.ForeignKey(
        EmployeeShift,
        related_name="shift2",
        on_delete=models.PROTECT,
        verbose_name=_("Shift 2"),
    )
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Rotating Shift")
        verbose_name_plural = _("Rotating Shifts")

    def __str__(self) -> str:
        return str(self.name)

    def clean(self):
        if self.shift1 == self.shift2:
            raise ValidationError(_("Choose different shifts"))


class RotatingShiftAssign(HorillaModel):
    """
    RotatingShiftAssign model
    """

    employee_id = models.ForeignKey(
        "employee.Employee", on_delete=models.PROTECT, verbose_name=_("Employee")
    )
    rotating_shift_id = models.ForeignKey(
        RotatingShift, on_delete=models.PROTECT, verbose_name=_("Rotating Shift")
    )
    start_date = models.DateField(
        default=django.utils.timezone.now, verbose_name=_("Start Date")
    )
    next_change_date = models.DateField(null=True, verbose_name=_("Next Switch"))
    current_shift = models.ForeignKey(
        EmployeeShift,
        on_delete=models.PROTECT,
        null=True,
        related_name="current_shift",
        verbose_name=_("Current Shift"),
    )
    next_shift = models.ForeignKey(
        EmployeeShift,
        on_delete=models.PROTECT,
        null=True,
        related_name="next_shift",
        verbose_name=_("Next Shift"),
    )
    based_on = models.CharField(
        max_length=10,
        choices=BASED_ON,
        null=False,
        blank=False,
        verbose_name=_("Based On"),
    )
    rotate_after_day = models.IntegerField(
        null=True, blank=True, default=7, verbose_name=_("Rotate After Day")
    )
    rotate_every_weekend = models.CharField(
        max_length=10,
        default="monday",
        choices=DAY,
        blank=True,
        null=True,
        verbose_name=_("Rotate Every Weekend"),
    )
    rotate_every = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        default="1",
        choices=DAY_DATE,
        verbose_name=_("Rotate Every Month"),
    )
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Rotating Shift Assign")
        verbose_name_plural = _("Rotating Shift Assigns")
        ordering = ["-next_change_date", "-employee_id__employee_first_name"]

    def clean(self):
        if self.is_active and self.employee_id is not None:
            # Check if any other active record with the same parent already exists
            siblings = RotatingShiftAssign.objects.filter(
                is_active=True, employee_id=self.employee_id
            )
            if siblings.exists() and siblings.first().id != self.id:
                raise ValidationError(_("Only one active record allowed per employee"))
        if self.start_date < django.utils.timezone.now().date():
            raise ValidationError(_("Date must be greater than or equal to today"))


class BaserequestFile(models.Model):
    file = models.FileField(upload_to="base/request_files")
    objects = models.Manager()


class WorkTypeRequest(HorillaModel):
    """
    WorkTypeRequest model
    """

    employee_id = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        null=True,
        related_name="work_type_request",
        verbose_name=_("Employee"),
    )
    work_type_id = models.ForeignKey(
        WorkType,
        on_delete=models.PROTECT,
        related_name="requested_work_type",
        verbose_name=_("Requesting Work Type"),
    )
    previous_work_type_id = models.ForeignKey(
        WorkType,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="previous_work_type",
        verbose_name=_("Previous Work Type"),
    )
    requested_date = models.DateField(
        null=True, default=django.utils.timezone.now, verbose_name=_("Requested Date")
    )
    requested_till = models.DateField(
        null=True, blank=True, verbose_name=_("Requested Till")
    )
    description = models.TextField(null=True, verbose_name=_("Description"))
    is_permanent_work_type = models.BooleanField(
        default=False, verbose_name=_("Permanent Request")
    )
    approved = models.BooleanField(default=False, verbose_name=_("Approved"))
    canceled = models.BooleanField(default=False, verbose_name=_("Canceled"))
    work_type_changed = models.BooleanField(default=False)
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Work Type Request")
        verbose_name_plural = _("Work Type Requests")
        permissions = (
            ("approve_worktyperequest", "Approve Work Type Request"),
            ("cancel_worktyperequest", "Cancel Work Type Request"),
        )
        ordering = [
            "-id",
        ]

    def delete(self, *args, **kwargs):
        request = getattr(_thread_locals, "request", None)
        if not self.approved:
            super().delete(*args, **kwargs)
        else:
            if request:
                clear_messages(request)
                messages.warning(request, "The request entry cannot be deleted.")

    def is_any_work_type_request_exists(self):
        approved_work_type_requests_range = WorkTypeRequest.objects.filter(
            employee_id=self.employee_id,
            approved=True,
            canceled=False,
            requested_date__range=[self.requested_date, self.requested_till],
            requested_till__range=[self.requested_date, self.requested_till],
        ).exclude(id=self.id)
        if approved_work_type_requests_range:
            return True
        approved_work_type_requests = WorkTypeRequest.objects.filter(
            employee_id=self.employee_id,
            approved=True,
            canceled=False,
            requested_date__lte=self.requested_date,
            requested_till__gte=self.requested_date,
        ).exclude(id=self.id)
        if approved_work_type_requests:
            return True
        if self.requested_till:
            approved_work_type_requests_2 = WorkTypeRequest.objects.filter(
                employee_id=self.employee_id,
                approved=True,
                canceled=False,
                requested_date__lte=self.requested_till,
                requested_till__gte=self.requested_till,
            ).exclude(id=self.id)
            if approved_work_type_requests_2:
                return True
        approved_permanent_req = WorkTypeRequest.objects.filter(
            employee_id=self.employee_id,
            approved=True,
            canceled=False,
            requested_date__exact=self.requested_date,
        )
        if approved_permanent_req:
            return True
        return False

    def clean(self):
        if self.requested_date < django.utils.timezone.now().date():
            raise ValidationError(_("Date must be greater than or equal to today"))
        if self.requested_till and self.requested_till < self.requested_date:
            raise ValidationError(
                _("End date must be greater than or equal to start date")
            )
        if self.is_any_work_type_request_exists():
            raise ValidationError(
                _("A work type request already exists during this time period.")
            )
        if not self.is_permanent_work_type:
            if not self.requested_till:
                raise ValidationError(_("Requested till field is required."))

    def __str__(self) -> str:
        return f"{self.employee_id.employee_first_name} \
            {self.employee_id.employee_last_name} - {self.requested_date}"


class WorkTypeRequestComment(HorillaModel):
    """
    WorkTypeRequestComment Model
    """

    from employee.models import Employee

    request_id = models.ForeignKey(WorkTypeRequest, on_delete=models.CASCADE)
    employee_id = models.ForeignKey(Employee, on_delete=models.CASCADE)
    comment = models.TextField(null=True, verbose_name=_("Comment"))
    files = models.ManyToManyField(BaserequestFile, blank=True)
    objects = models.Manager()

    def __str__(self) -> str:
        return f"{self.comment}"


class ShiftRequest(HorillaModel):
    """
    ShiftRequest model
    """

    employee_id = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        null=True,
        related_name="shift_request",
        verbose_name=_("Employee"),
    )
    shift_id = models.ForeignKey(
        EmployeeShift,
        on_delete=models.PROTECT,
        related_name="requested_shift",
        verbose_name=_("Requesting Shift"),
    )
    previous_shift_id = models.ForeignKey(
        EmployeeShift,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="previous_shift",
        verbose_name=_("Previous Shift"),
    )
    requested_date = models.DateField(
        null=True, default=django.utils.timezone.now, verbose_name=_("Requested Date")
    )
    reallocate_to = models.ForeignKey(
        "employee.Employee",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reallocate_shift_request",
        verbose_name=_("Reallocate Employee"),
    )
    reallocate_approved = models.BooleanField(default=False, verbose_name=_("Approved"))
    reallocate_canceled = models.BooleanField(default=False, verbose_name=_("Canceled"))
    requested_till = models.DateField(
        null=True, blank=True, verbose_name=_("Requested Till")
    )
    description = models.TextField(null=True, verbose_name=_("Description"))
    is_permanent_shift = models.BooleanField(
        default=False, verbose_name=_("Permanent Request")
    )
    approved = models.BooleanField(default=False, verbose_name=_("Approved"))
    canceled = models.BooleanField(default=False, verbose_name=_("Canceled"))
    shift_changed = models.BooleanField(default=False)
    history = HorillaAuditLog(
        related_name="history_set",
        bases=[
            HorillaAuditInfo,
        ],
    )
    objects = HorillaCompanyManager("employee_id__employee_work_info__company_id")

    class Meta:
        """
        Meta class to add additional options
        """

        verbose_name = _("Shift Request")
        verbose_name_plural = _("Shift Requests")
        permissions = (
            ("approve_shiftrequest", "Approve Shift Request"),
            ("cancel_shiftrequest", "Cancel Shift Request"),
        )
        ordering = [
            "-id",
        ]

    def clean(self):
        if not self.pk and self.requested_date < django.utils.timezone.now().date():
            raise ValidationError(_("Date must be greater than or equal to today"))
        if self.requested_till and self.requested_till < self.requested_date:
            raise ValidationError(
                _("End date must be greater than or equal to start date")
            )
        if self.is_any_request_exists():
            raise ValidationError(
                _("An approved shift request already exists during this time period.")
            )
        if not self.is_permanent_shift:
            if not self.requested_till:
                raise ValidationError(_("Requested till field is required."))

    def is_any_request_exists(self):
        approved_shift_requests_range = ShiftRequest.objects.filter(
            employee_id=self.employee_id,
            approved=True,
            canceled=False,
            requested_date__range=[self.requested_date, self.requested_till],
            requested_till__range=[self.requested_date, self.requested_till],
        ).exclude(id=self.id)
        if approved_shift_requests_range:
            return True
        approved_shift_requests = ShiftRequest.objects.filter(
            employee_id=self.employee_id,
            approved=True,
            canceled=False,
            requested_date__lte=self.requested_date,
            requested_till__gte=self.requested_date,
        ).exclude(id=self.id)
        if approved_shift_requests:
            return True
        if self.requested_till:
            approved_shift_requests_2 = ShiftRequest.objects.filter(
                employee_id=self.employee_id,
                approved=True,
                canceled=False,
                requested_date__lte=self.requested_till,
                requested_till__gte=self.requested_till,
            ).exclude(id=self.id)
            if approved_shift_requests_2:
                return True
        approved_permanent_req = ShiftRequest.objects.filter(
            employee_id=self.employee_id,
            approved=True,
            canceled=False,
            requested_date__exact=self.requested_date,
        )
        if approved_permanent_req:
            return True
        return False

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        request = getattr(_thread_locals, "request", None)
        if not self.approved:
            super().delete(*args, **kwargs)
        else:
            if request:
                clear_messages(request)
                messages.warning(request, "The request entry cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.employee_id.employee_first_name} \
            {self.employee_id.employee_last_name} - {self.requested_date}"


class ShiftRequestComment(HorillaModel):
    """
    ShiftRequestComment Model
    """

    from employee.models import Employee

    request_id = models.ForeignKey(ShiftRequest, on_delete=models.CASCADE)
    employee_id = models.ForeignKey(Employee, on_delete=models.CASCADE)
    files = models.ManyToManyField(BaserequestFile, blank=True)
    comment = models.TextField(null=True, verbose_name=_("Comment"))
    objects = models.Manager()

    def __str__(self) -> str:
        return f"{self.comment}"


class Tags(HorillaModel):
    title = models.CharField(max_length=30)
    color = models.CharField(max_length=30)
    company_id = models.ForeignKey(
        Company, null=True, editable=False, on_delete=models.PROTECT
    )
    objects = HorillaCompanyManager(related_company_field="company_id")

    def __str__(self):
        return self.title


class DynamicEmailConfiguration(HorillaModel):
    """
    SingletonModel to keep the mail server configurations
    """

    is_primary = models.BooleanField(
        default=False, verbose_name=_("Primary Mail Server")
    )

    host = models.CharField(
        blank=True, null=True, max_length=256, verbose_name=_("Email Host")
    )

    port = models.SmallIntegerField(blank=True, null=True, verbose_name=_("Email Port"))

    from_email = models.CharField(
        blank=True, null=True, max_length=256, verbose_name=_("Default From Email")
    )

    username = models.CharField(
        blank=True,
        null=True,
        max_length=256,
        verbose_name=_("Email Host Username"),
    )

    display_name = models.CharField(
        blank=True,
        null=True,
        max_length=256,
        verbose_name=_("Display Name"),
    )

    password = models.CharField(
        blank=True,
        null=True,
        max_length=256,
        verbose_name=_("Email Authentication Password"),
    )

    use_tls = models.BooleanField(default=True, verbose_name=_("Use TLS"))

    use_ssl = models.BooleanField(default=False, verbose_name=_("Use SSL"))

    fail_silently = models.BooleanField(default=False, verbose_name=_("Fail Silently"))

    timeout = models.SmallIntegerField(
        blank=True, null=True, verbose_name=_("Email Send Timeout (seconds)")
    )
    company_id = models.OneToOneField(
        Company, on_delete=models.CASCADE, null=True, blank=True
    )

    def clean(self):
        if self.use_ssl and self.use_tls:
            raise ValidationError(
                _(
                    '"Use TLS" and "Use SSL" are mutually exclusive, '
                    "so only set one of those settings to True."
                )
            )
        if not self.company_id:
            raise ValidationError({"company_id": _("This field is required")})

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs) -> None:
        if self.is_primary:
            DynamicEmailConfiguration.objects.filter(is_primary=True).update(
                is_primary=False
            )
        super().save(*args, **kwargs)
        servers_same_company = DynamicEmailConfiguration.objects.filter(
            company_id=self.company_id
        ).exclude(id=self.id)
        if servers_same_company.exists():
            self.delete()
        return

    class Meta:
        verbose_name = _("Email Configuration")


FIELD_CHOICE = [
    ("", "---------"),
    ("requested_days", _("Leave Requested Days")),
]
CONDITION_CHOICE = [
    ("equal", _("Equal (==)")),
    ("notequal", _("Not Equal (!=)")),
    ("range", _("Range")),
    ("lt", _("Less Than (<)")),
    ("gt", _("Greater Than (>)")),
    ("le", _("Less Than or Equal To (<=)")),
    ("ge", _("Greater Than or Equal To (>=)")),
    ("icontains", _("Contains")),
]


class MultipleApprovalCondition(HorillaModel):
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    condition_field = models.CharField(
        max_length=255,
        choices=FIELD_CHOICE,
    )
    condition_operator = models.CharField(
        max_length=255, choices=CONDITION_CHOICE, null=True, blank=True
    )
    condition_value = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("Condition Value"),
    )
    condition_start_value = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("Starting Value"),
    )
    condition_end_value = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name=_("Ending Value"),
    )
    objects = models.Manager()

    def __str__(self) -> str:
        return f"{self.condition_field} {self.condition_operator}"

    def clean(self, *args, **kwargs):
        if self.condition_value:
            instance = MultipleApprovalCondition.objects.filter(
                department=self.department,
                condition_field=self.condition_field,
                condition_operator=self.condition_operator,
                condition_value=self.condition_value,
            ).exclude(id=self.pk)
            if instance:
                raise ValidationError(
                    _("A condition with the provided fields already exists")
                )
        if self.condition_field == "requested_days":
            if self.condition_operator != "range":
                if not self.condition_value:
                    raise ValidationError(
                        {
                            "condition_operator": _(
                                "Please enter a numeric value for condition value"
                            )
                        }
                    )
                try:
                    float_value = float(self.condition_value)
                except ValueError as e:
                    raise ValidationError(
                        {
                            "condition_operator": _(
                                "Please enter a valid numeric value for the condition value when the condition field is Leave Requested Days."
                            )
                        }
                    )
            else:
                if not self.condition_start_value or not self.condition_end_value:
                    raise ValidationError(
                        {
                            "condition_operator": _(
                                "Please specify condition value range"
                            )
                        }
                    )
                try:
                    start_value = float(self.condition_start_value)
                except ValueError as e:
                    raise ValidationError(
                        {
                            "condition_operator": _(
                                "Please enter a valid numeric value for the starting value when the condition field is Leave Requested Days."
                            )
                        }
                    )
                try:
                    end_value = float(self.condition_end_value)
                except ValueError as e:
                    raise ValidationError(
                        {
                            "condition_operator": _(
                                "Please enter a valid numeric value for the ending value when the condition field is Leave Requested Days."
                            )
                        }
                    )

                if start_value == end_value:
                    raise ValidationError(
                        {
                            "condition_operator": _(
                                "End value must be different from the start value in a range."
                            )
                        }
                    )
                if end_value <= start_value:
                    raise ValidationError(
                        {
                            "condition_operator": _(
                                "End value must be greater than the start value in a range."
                            )
                        }
                    )
        super().clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        if self.condition_operator != "range":
            self.condition_start_value = None
            self.condition_end_value = None
        else:
            self.condition_value = None
        super().save(*args, **kwargs)

    def approval_managers(self, *args, **kwargs):
        managers = []
        from employee.models import Employee

        queryset = MultipleApprovalManagers.objects.filter(
            condition_id=self.pk
        ).order_by("sequence")
        for query in queryset:
            employee = Employee.objects.get(id=query.employee_id)
            managers.append(employee)

        return managers


class MultipleApprovalManagers(models.Model):
    condition_id = models.ForeignKey(
        MultipleApprovalCondition, on_delete=models.CASCADE
    )
    sequence = models.IntegerField(null=False, blank=False)
    employee_id = models.IntegerField(null=False, blank=False)
    objects = models.Manager()


class DynamicPagination(models.Model):
    """
    model for storing pagination for employees
    """

    from django.contrib.auth.models import User
    from django.core.validators import MinValueValidator

    user_id = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="dynamic_pagination",
        verbose_name=_("User"),
    )
    pagination = models.IntegerField(default=50, validators=[MinValueValidator(1)])
    objects = models.Manager()

    def save(self, *args, **kwargs):
        request = getattr(_thread_locals, "request", None)
        user = request.user
        self.user_id = user
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user_id}|{self.pagination}"


class Attachment(models.Model):
    """
    Attachment model for multiple attachments in announcements.
    """

    file = models.FileField(upload_to="attachments/")

    def __str__(self):
        return self.file.name


class AnnouncementExpire(models.Model):
    """
    This model for setting a expire days for announcement if no expire date for announcement
    """

    days = models.IntegerField(null=True, blank=True, default=30)
    objects = models.Manager()


class Announcement(HorillaModel):
    """
    Announcement Model for storing all announcements.
    """

    from employee.models import Employee

    title = models.CharField(max_length=30)
    description = models.TextField(null=True, max_length=255)
    attachments = models.ManyToManyField(
        Attachment, related_name="announcement_attachments", blank=True
    )
    expire_date = models.DateField(null=True, blank=True)
    employees = models.ManyToManyField(
        Employee, related_name="announcement_employees", blank=True
    )
    department = models.ManyToManyField(Department, blank=True)
    job_position = models.ManyToManyField(JobPosition, blank=True)
    disable_comments = models.BooleanField(default=False)

    def get_views(self):
        """
        This method is used to get the view count of the announcement
        """
        return self.announcementview_set.filter(viewed=True)

    def __str__(self):
        return self.title


class AnnouncementComment(HorillaModel):
    """
    AnnouncementComment Model
    """

    from employee.models import Employee

    announcement_id = models.ForeignKey(Announcement, on_delete=models.CASCADE)
    employee_id = models.ForeignKey(Employee, on_delete=models.CASCADE)
    comment = models.TextField(null=True, verbose_name=_("Comment"), max_length=255)


class AnnouncementView(models.Model):
    """
    Announcement View Model
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE)
    viewed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)


class EmailLog(models.Model):
    """
    EmailLog Keeping model
    """

    statuses = [("sent", "Sent"), ("failed", "Failed")]
    subject = models.CharField(max_length=255)
    body = models.TextField(max_length=255)
    from_email = models.EmailField()
    to = models.EmailField()
    status = models.CharField(max_length=6, choices=statuses)
    created_at = models.DateTimeField(auto_now_add=True)
    company_id = models.ForeignKey(
        Company, on_delete=models.CASCADE, null=True, editable=False
    )


class DriverViewed(models.Model):
    """
    Model to store driver viewed status
    """

    choices = [
        ("dashboard", "dashboard"),
        ("pipeline", "pipeline"),
        ("settings", "settings"),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    viewed = models.CharField(max_length=10, choices=choices)

    def user_viewed(self):
        """
        This method is used to access all the viewd driver
        """
        return self.user.driverviewed_set.values_list("viewed", flat=True)


class DashboardEmployeeCharts(HorillaModel):
    from employee.models import Employee
    
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    charts = models.JSONField(default=list, blank=True, null=True)

    def __str__(self):
        return f"{self.employee} - charts"
    