from datetime import datetime, timedelta, time

from django.contrib.auth import authenticate
from django.db import connection
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.db.models import Count, F
from .models import (
    Doctor, Appointment, DoctorAvailability,
    MedicalRecord, Prescription, Drug, DrugStock, Equipment,
)
from .serializers import (
    DoctorSerializer, AppointmentSerializer, RegisterSerializer,
    DoctorAvailabilitySerializer,
    MedicalRecordSerializer, PrescriptionSerializer,
    DrugSerializer, DrugStockSerializer, EquipmentSerializer,
)
from . import permissions as perms


@api_view(['GET'])
@permission_classes([AllowAny])
def api_health(request):
    """Lightweight health probe used by Docker / Kubernetes.

    Returns 200 with {"status": "ok", "db": "ok"} when the DB is reachable,
    and 503 otherwise.
    """
    db_ok = True
    try:
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            cur.fetchone()
    except Exception:
        db_ok = False
    body = {"status": "ok" if db_ok else "degraded",
            "db":     "ok" if db_ok else "down"}
    return Response(body, status=200 if db_ok else 503)


@api_view(['POST'])
@permission_classes([AllowAny])
def api_login(request):
    """Authenticate by username + password and return a token + user info."""
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if not user:
        return Response({'error': 'Invalid credentials'}, status=status.HTTP_401_UNAUTHORIZED)
    token, _ = Token.objects.get_or_create(user=user)
    return Response({'token': token.key, 'user': {'id': user.id, 'name': user.get_full_name() or user.username, 'email': user.email, 'role': user.role}})


@api_view(['POST'])
@permission_classes([AllowAny])
def api_register(request):
    """Register a new PATIENT account and return an auth token (UC-1)."""
    serializer = RegisterSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response({'token': token.key}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout(request):
    """Delete the caller's auth token, ending the session."""
    request.user.auth_token.delete()
    return Response({'message': 'Logged out.'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_doctor_list(request):
    """List every doctor with name, specialization, years, and department (UC-3)."""
    qs = Doctor.objects.select_related('user', 'department').all()
    serializer = DoctorSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_my_appointments(request):
    """Return the authenticated patient's own appointments (UC-5)."""
    if request.user.role != 'PATIENT':
        return Response({'error': 'Patients only.'}, status=status.HTTP_403_FORBIDDEN)
    appts = Appointment.objects.filter(patient=request.user.patient_profile).select_related('doctor__user', 'doctor__department')
    serializer = AppointmentSerializer(appts, many=True)
    return Response(serializer.data)


def _expand_availability_slots(doctor, target_date):
    """Return the set of `datetime.time` slots a doctor is available on `target_date`.

    Walks every active DoctorAvailability row that matches the weekday and
    expands it into start_time, start_time+slot, ... < end_time.
    """
    weekday = target_date.weekday()
    rows = DoctorAvailability.objects.filter(
        doctor=doctor, weekday=weekday, active=True,
    )
    slots = set()
    for row in rows:
        cur = datetime.combine(target_date, row.start_time)
        end = datetime.combine(target_date, row.end_time)
        step = timedelta(minutes=row.slot_minutes)
        while cur < end:
            slots.add(cur.time().replace(second=0, microsecond=0))
            cur += step
    return slots


def _taken_slots(doctor, target_date):
    """Slots already booked for `doctor` on `target_date` (excluding CANCELLED)."""
    appts = Appointment.objects.filter(
        doctor=doctor,
        scheduled_at__date=target_date,
    ).exclude(status='CANCELLED')
    return {
        timezone.localtime(a.scheduled_at).time().replace(second=0, microsecond=0)
        if timezone.is_aware(a.scheduled_at)
        else a.scheduled_at.time().replace(second=0, microsecond=0)
        for a in appts
    }


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_book_appointment(request, doctor_id):
    """Patient books an appointment; rejects slots outside availability or already taken (UC-4)."""
    if request.user.role != 'PATIENT':
        return Response({'error': 'Patients only.'}, status=status.HTTP_403_FORBIDDEN)
    try:
        doctor = Doctor.objects.select_related('user', 'department').get(pk=doctor_id)
    except Doctor.DoesNotExist:
        return Response({'error': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)
    scheduled_at = request.data.get('scheduled_at')
    reason = request.data.get('reason', '')
    if not scheduled_at:
        return Response({'error': 'scheduled_at is required.'}, status=status.HTTP_400_BAD_REQUEST)

    parsed = parse_datetime(scheduled_at) if isinstance(scheduled_at, str) else scheduled_at
    if parsed is None:
        return Response({'error': 'Invalid scheduled_at format.'}, status=status.HTTP_400_BAD_REQUEST)
    # Normalize to local naive time for slot comparison (DoctorAvailability is
    # stored as a plain time-of-day with no timezone semantics).
    if timezone.is_aware(parsed):
        local = timezone.localtime(parsed)
    else:
        local = parsed
    target_date = local.date()
    target_time = local.time().replace(second=0, microsecond=0)

    available = _expand_availability_slots(doctor, target_date)
    if target_time not in available:
        return Response(
            {'error': 'That time is outside the doctor\'s availability.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    if target_time in _taken_slots(doctor, target_date):
        return Response(
            {'error': 'That slot is already booked.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        appt = Appointment.objects.create(
            patient=request.user.patient_profile,
            doctor=doctor, scheduled_at=parsed,
            reason=reason, status='PENDING',
        )
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    serializer = AppointmentSerializer(appt)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_cancel_appointment(request, appointment_id):
    """Patient cancels one of their own upcoming appointments (UC-17, Phase 2.1)."""
    try:
        appt = Appointment.objects.select_related(
            'doctor__user', 'doctor__department', 'patient__user',
        ).get(pk=appointment_id)
    except Appointment.DoesNotExist:
        return Response({'error': 'Appointment not found.'}, status=status.HTTP_404_NOT_FOUND)

    if not perms.can_cancel_appointment(request.user, appt):
        # Distinguish between "wrong patient" (403) and "wrong state" (400)
        if request.user.role != 'PATIENT' or appt.patient.user_id != request.user.id:
            return Response(
                {'error': 'You do not have permission to cancel this appointment.'},
                status=status.HTTP_403_FORBIDDEN,
            )
        if appt.status in ('COMPLETED', 'CANCELLED'):
            return Response(
                {'error': f'Cannot cancel an appointment with status {appt.status}.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {'error': 'Cannot cancel an appointment in the past.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    appt.status = 'CANCELLED'
    appt.save(update_fields=['status'])
    return Response(AppointmentSerializer(appt).data)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def api_doctor_availability(request, doctor_id):
    """GET lists the doctor's weekly availability; PUT replaces it (UC-18, Phase 2.1)."""
    try:
        doctor = Doctor.objects.select_related('user').get(pk=doctor_id)
    except Doctor.DoesNotExist:
        return Response({'error': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        rows = doctor.availabilities.all().order_by('weekday', 'start_time')
        return Response(DoctorAvailabilitySerializer(rows, many=True).data)

    # PUT — replace the doctor's entire weekly schedule
    if not perms.can_edit_availability(request.user, doctor):
        return Response(
            {'error': 'You do not have permission to edit this schedule.'},
            status=status.HTTP_403_FORBIDDEN,
        )

    payload = request.data
    if not isinstance(payload, list):
        return Response(
            {'error': 'Body must be a JSON array of availability rows.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    cleaned = []
    for entry in payload:
        try:
            weekday = int(entry['weekday'])
            start_str = entry['start_time']
            end_str = entry['end_time']
            slot_minutes = int(entry.get('slot_minutes', 30))
            active = bool(entry.get('active', True))
        except (KeyError, TypeError, ValueError):
            return Response(
                {'error': 'Each row needs weekday, start_time, end_time.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if weekday < 0 or weekday > 6:
            return Response({'error': 'weekday must be 0–6.'}, status=status.HTTP_400_BAD_REQUEST)
        if slot_minutes <= 0:
            return Response({'error': 'slot_minutes must be positive.'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            start_t = time.fromisoformat(start_str)
            end_t = time.fromisoformat(end_str)
        except (TypeError, ValueError):
            return Response(
                {'error': 'start_time/end_time must be HH:MM[:SS].'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if start_t >= end_t:
            return Response(
                {'error': 'start_time must be before end_time.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        cleaned.append((weekday, start_t, end_t, slot_minutes, active))

    doctor.availabilities.all().delete()
    for weekday, start_t, end_t, slot_minutes, active in cleaned:
        DoctorAvailability.objects.create(
            doctor=doctor, weekday=weekday,
            start_time=start_t, end_time=end_t,
            slot_minutes=slot_minutes, active=active,
        )
    rows = doctor.availabilities.all().order_by('weekday', 'start_time')
    return Response(DoctorAvailabilitySerializer(rows, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_doctor_slots(request, doctor_id):
    """Compute open booking slots for a doctor on a given date (Phase 2.1)."""
    try:
        doctor = Doctor.objects.get(pk=doctor_id)
    except Doctor.DoesNotExist:
        return Response({'error': 'Doctor not found.'}, status=status.HTTP_404_NOT_FOUND)

    date_str = request.query_params.get('date')
    if not date_str:
        return Response({'error': 'date query param is required.'}, status=status.HTTP_400_BAD_REQUEST)
    target_date = parse_date(date_str)
    if target_date is None:
        return Response({'error': 'date must be YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

    available = _expand_availability_slots(doctor, target_date)
    taken = _taken_slots(doctor, target_date)
    free = sorted(available - taken)
    return Response([{'time': t.strftime('%H:%M')} for t in free])


# ---------------------------------------------------------------------------
# Phase-2.2 endpoints — inline role flows (replaces the broken
# /appointments/schedule, /pharmacy/stock, etc. Django template links the
# React shell used to deep-link to. See SAD §3.4 for the full table.)
# ---------------------------------------------------------------------------

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_my_schedule(request):
    """Doctor's own appointment list, with medical-record presence flag (UC-6)."""
    if request.user.role != 'DOCTOR':
        return Response({'error': 'Doctors only.'}, status=status.HTTP_403_FORBIDDEN)
    doctor = request.user.doctor_profile
    appts = (Appointment.objects
             .filter(doctor=doctor)
             .select_related('patient__user', 'doctor__user', 'doctor__department')
             .order_by('-scheduled_at'))
    data = []
    for a in appts:
        row = AppointmentSerializer(a).data
        row['patient_name'] = a.patient.user.get_full_name() or a.patient.user.username
        row['has_record'] = MedicalRecord.objects.filter(appointment=a).exists()
        data.append(row)
    return Response(data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_add_medical_record(request, appointment_id):
    """Doctor records diagnosis/notes/treatment for an appointment (UC-7)."""
    try:
        appt = Appointment.objects.select_related('doctor__user').get(pk=appointment_id)
    except Appointment.DoesNotExist:
        return Response({'error': 'Appointment not found.'}, status=status.HTTP_404_NOT_FOUND)
    if not perms.can_write_medical_record(request.user, appt):
        return Response(
            {'error': 'Only the assigned doctor may record this visit.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    if MedicalRecord.objects.filter(appointment=appt).exists():
        return Response(
            {'error': 'A medical record already exists for this appointment.'},
            status=status.HTTP_400_BAD_REQUEST,
        )
    diagnosis = (request.data.get('diagnosis') or '').strip()
    if not diagnosis:
        return Response({'error': 'diagnosis is required.'}, status=status.HTTP_400_BAD_REQUEST)
    record = MedicalRecord.objects.create(
        appointment=appt, diagnosis=diagnosis,
        notes=request.data.get('notes', ''),
        treatment=request.data.get('treatment', ''),
    )
    appt.status = 'COMPLETED'
    appt.save(update_fields=['status'])
    return Response(MedicalRecordSerializer(record).data, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_add_prescription(request, record_id):
    """Doctor prescribes a medication against their own MedicalRecord (UC-8)."""
    try:
        record = MedicalRecord.objects.select_related(
            'appointment__doctor__user',
        ).get(pk=record_id)
    except MedicalRecord.DoesNotExist:
        return Response({'error': 'Record not found.'}, status=status.HTTP_404_NOT_FOUND)
    if not perms.can_write_prescription(request.user, record):
        return Response(
            {'error': 'Only the prescribing doctor may add prescriptions.'},
            status=status.HTTP_403_FORBIDDEN,
        )
    name = (request.data.get('drug_name') or '').strip()
    if not name:
        return Response({'error': 'drug_name is required.'}, status=status.HTTP_400_BAD_REQUEST)
    drug_id = request.data.get('drug_id')
    drug_obj = None
    if drug_id:
        try:
            drug_obj = Drug.objects.get(pk=drug_id)
        except Drug.DoesNotExist:
            return Response({'error': 'Unknown drug_id.'}, status=status.HTTP_400_BAD_REQUEST)
    rx = Prescription.objects.create(
        medical_record=record,
        drug=drug_obj,
        drug_name=name,
        dosage=request.data.get('dosage', ''),
        frequency=request.data.get('frequency', ''),
        duration=request.data.get('duration', ''),
        instructions=request.data.get('instructions', ''),
    )
    return Response(PrescriptionSerializer(rx).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_my_department_stock(request):
    """Doctor/Nurse: drug stock scoped to caller's own department (UC-12)."""
    user = request.user
    if user.role == 'DOCTOR':
        dept = user.doctor_profile.department
    elif user.role == 'NURSE':
        dept = user.nurse_profile.department
    else:
        return Response({'error': 'Doctors and nurses only.'}, status=status.HTTP_403_FORBIDDEN)
    rows = (DrugStock.objects
            .filter(department=dept)
            .select_related('drug', 'department')
            .order_by('drug__name'))
    return Response(DrugStockSerializer(rows, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_my_department_prescriptions(request):
    """Nurse: prescriptions written for patients seen by doctors in the nurse's department (UC-9)."""
    if request.user.role != 'NURSE':
        return Response({'error': 'Nurses only.'}, status=status.HTTP_403_FORBIDDEN)
    nurse = request.user.nurse_profile
    rxs = (Prescription.objects
           .filter(medical_record__appointment__doctor__department=nurse.department)
           .select_related(
               'medical_record__appointment__doctor__user',
               'medical_record__appointment__patient__user',
               'drug',
           )
           .order_by('-created_at'))
    return Response(PrescriptionSerializer(rxs, many=True).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_my_department_equipment(request):
    """Doctor/Nurse: equipment in caller's own department (UC-13)."""
    user = request.user
    if user.role == 'DOCTOR':
        dept = user.doctor_profile.department
    elif user.role == 'NURSE':
        dept = user.nurse_profile.department
    else:
        return Response({'error': 'Doctors and nurses only.'}, status=status.HTTP_403_FORBIDDEN)
    eq = (Equipment.objects
          .filter(department=dept)
          .select_related('department')
          .order_by('name'))
    return Response(EquipmentSerializer(eq, many=True).data)


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_drugs(request):
    """GET: any non-patient role lists the catalog. POST: pharmacist/admin creates (UC-10)."""
    if request.method == 'GET':
        if not perms.can_view_drug_catalog(request.user):
            return Response({'error': 'Drug catalog is not available to your role.'},
                            status=status.HTTP_403_FORBIDDEN)
        return Response(DrugSerializer(Drug.objects.all(), many=True).data)
    # POST
    if not perms.can_write_drug_catalog(request.user):
        return Response({'error': 'Only the pharmacist may edit the drug catalog.'},
                        status=status.HTTP_403_FORBIDDEN)
    name = (request.data.get('name') or '').strip()
    if not name:
        return Response({'error': 'name is required.'}, status=status.HTTP_400_BAD_REQUEST)
    if Drug.objects.filter(name__iexact=name).exists():
        return Response({'error': 'A drug with that name already exists.'},
                        status=status.HTTP_400_BAD_REQUEST)
    drug = Drug.objects.create(
        name=name,
        generic_name=request.data.get('generic_name', ''),
        category=request.data.get('category', 'OTHER'),
        manufacturer=request.data.get('manufacturer', ''),
        unit=request.data.get('unit', 'tablet'),
    )
    return Response(DrugSerializer(drug).data, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_stock_list(request):
    """Pharmacist/Management/Admin: hospital-wide stock (UC-12)."""
    user = request.user
    if not (user.is_superuser or user.role in ('PHARMACIST', 'MANAGEMENT', 'ADMIN')):
        return Response({'error': 'Hospital-wide stock is restricted.'},
                        status=status.HTTP_403_FORBIDDEN)
    rows = (DrugStock.objects
            .select_related('drug', 'department')
            .order_by('department__name', 'drug__name'))
    return Response(DrugStockSerializer(rows, many=True).data)


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def api_stock_adjust(request, stock_id):
    """Pharmacist adjusts a stock row's quantity / reorder_level (UC-11)."""
    if not perms.can_write_drug_stock(request.user):
        return Response({'error': 'Only the pharmacist may adjust drug stock.'},
                        status=status.HTTP_403_FORBIDDEN)
    try:
        stock = DrugStock.objects.select_related('drug', 'department').get(pk=stock_id)
    except DrugStock.DoesNotExist:
        return Response({'error': 'Stock row not found.'}, status=status.HTTP_404_NOT_FOUND)
    qty = request.data.get('quantity')
    if qty is not None:
        try:
            qty_int = int(qty)
            if qty_int < 0:
                raise ValueError
        except (TypeError, ValueError):
            return Response({'error': 'quantity must be a non-negative integer.'},
                            status=status.HTTP_400_BAD_REQUEST)
        stock.quantity = qty_int
    reorder = request.data.get('reorder_level')
    if reorder is not None:
        try:
            stock.reorder_level = int(reorder)
        except (TypeError, ValueError):
            return Response({'error': 'reorder_level must be an integer.'},
                            status=status.HTTP_400_BAD_REQUEST)
    stock.save()
    return Response(DrugStockSerializer(stock).data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def api_management_kpis(request):
    """Management dashboard data — low stock, equipment status counts, appointment volume (UC-15)."""
    if not perms.can_view_management_dashboard(request.user):
        return Response({'error': 'Management dashboard is restricted.'},
                        status=status.HTTP_403_FORBIDDEN)
    low = (DrugStock.objects
           .select_related('drug', 'department')
           .filter(quantity__lte=F('reorder_level'))
           .order_by('quantity'))
    equipment_counts = list(Equipment.objects
                            .values('status')
                            .annotate(n=Count('id'))
                            .order_by('status'))
    appts_by_dept = list(Appointment.objects
                         .values('doctor__department__name')
                         .annotate(n=Count('id'))
                         .order_by('-n'))
    return Response({
        'low_stock': DrugStockSerializer(low, many=True).data,
        'equipment_by_status': equipment_counts,
        'appointments_by_department': [
            {'department': r['doctor__department__name'], 'count': r['n']}
            for r in appts_by_dept
        ],
    })
