"""
seed_data.py — Django management command to seed the Hospital Management System
with realistic demonstration data.

PLACE THIS FILE AT:
    accounts/management/commands/seed_data.py

USAGE:
    python manage.py seed_data            # idempotent: top up missing rows
    python manage.py seed_data --reset    # WIPE all seed data and recreate

DATA PROVENANCE:
    Drug catalog is sampled from the WHO Model List of Essential Medicines
    (https://www.who.int/publications/i/item/WHO-MHP-HPS-EML-2023.02), a public
    reference list maintained by the World Health Organization.
    All patients, doctors, nurses, and other personal data are FICTIONAL.

DEFAULT PASSWORDS:
    All seeded users have password `Pass1234!` for demo purposes only.
"""

from datetime import timedelta, time, datetime
import random

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import (
    User, Patient, Doctor, Nurse, Pharmacist, Manager,
    Department, Appointment, MedicalRecord, Prescription,
    Drug, DrugStock, Equipment,
    DoctorAvailability, Room,
)


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------

DEPARTMENTS = [
    ("Cardiology", "Heart and circulatory system"),
    ("Pediatrics", "Care for infants, children, and adolescents"),
    ("Neurology", "Disorders of the nervous system"),
    ("General Medicine", "Primary internal medicine and general care"),
    ("Orthopedics", "Bones, joints, ligaments, tendons and muscles"),
]

# WHO Model List of Essential Medicines — selected entries
DRUGS = [
    ("Paracetamol", "Acetaminophen", "ANALGESIC", "Generic Pharma", "tablet"),
    ("Ibuprofen", "Ibuprofen", "ANALGESIC", "Generic Pharma", "tablet"),
    ("Aspirin", "Acetylsalicylic acid", "ANALGESIC", "Bayer", "tablet"),
    ("Diclofenac", "Diclofenac sodium", "ANALGESIC", "Novartis", "tablet"),
    ("Morphine", "Morphine sulfate", "ANALGESIC", "Generic Pharma", "vial"),
    ("Tramadol", "Tramadol HCl", "ANALGESIC", "Grunenthal", "tablet"),
    ("Codeine", "Codeine phosphate", "ANALGESIC", "Generic Pharma", "tablet"),
    ("Amoxicillin", "Amoxicillin trihydrate", "ANTIBIOTIC", "GSK", "tablet"),
    ("Azithromycin", "Azithromycin", "ANTIBIOTIC", "Pfizer", "tablet"),
    ("Ciprofloxacin", "Ciprofloxacin HCl", "ANTIBIOTIC", "Bayer", "tablet"),
    ("Doxycycline", "Doxycycline hyclate", "ANTIBIOTIC", "Pfizer", "tablet"),
    ("Metronidazole", "Metronidazole", "ANTIBIOTIC", "Generic Pharma", "tablet"),
    ("Acyclovir", "Acyclovir", "ANTIVIRAL", "GSK", "tablet"),
    ("Oseltamivir", "Oseltamivir phosphate", "ANTIVIRAL", "Roche", "capsule"),
    ("Atorvastatin", "Atorvastatin calcium", "CARDIO", "Pfizer", "tablet"),
    ("Lisinopril", "Lisinopril", "CARDIO", "Merck", "tablet"),
    ("Amlodipine", "Amlodipine besylate", "CARDIO", "Pfizer", "tablet"),
    ("Metoprolol", "Metoprolol tartrate", "CARDIO", "AstraZeneca", "tablet"),
    ("Furosemide", "Furosemide", "CARDIO", "Sanofi", "tablet"),
    ("Warfarin", "Warfarin sodium", "CARDIO", "BMS", "tablet"),
    ("Heparin", "Heparin sodium", "CARDIO", "Pfizer", "vial"),
    ("Metformin", "Metformin HCl", "ENDOCRINE", "Merck", "tablet"),
    ("Insulin (Regular)", "Insulin human", "ENDOCRINE", "Novo Nordisk", "vial"),
    ("Levothyroxine", "Levothyroxine sodium", "ENDOCRINE", "Abbott", "tablet"),
    ("Omeprazole", "Omeprazole", "GI", "AstraZeneca", "capsule"),
    ("Loperamide", "Loperamide HCl", "GI", "J&J", "tablet"),
    ("Salbutamol", "Salbutamol sulfate", "RESP", "GSK", "inhaler"),
    ("Prednisolone", "Prednisolone", "RESP", "Sanofi", "tablet"),
    ("Loratadine", "Loratadine", "OTHER", "Bayer", "tablet"),
    ("Diazepam", "Diazepam", "PSYCH", "Roche", "tablet"),
    ("Fluoxetine", "Fluoxetine HCl", "PSYCH", "Eli Lilly", "capsule"),
    ("Sertraline", "Sertraline HCl", "PSYCH", "Pfizer", "tablet"),
]

EQUIPMENT = [
    # Cardiology
    ("ECG Machine", "MAC-2000", "GE Healthcare", "ECG-CAR-001", "Cardiology", "AVAILABLE"),
    ("Defibrillator", "LIFEPAK-15", "Stryker", "DEF-CAR-001", "Cardiology", "AVAILABLE"),
    ("Ultrasound Machine", "Vivid-T8", "GE Healthcare", "USG-CAR-001", "Cardiology", "IN_USE"),
    ("Cardiac Monitor", "IntelliVue MX450", "Philips", "MON-CAR-001", "Cardiology", "AVAILABLE"),
    ("Holter Monitor", "DR400", "NorthEast Monitoring", "HOL-CAR-001", "Cardiology", "MAINTENANCE"),
    # Pediatrics
    ("Infant Incubator", "Giraffe Omnibed", "GE Healthcare", "INC-PED-001", "Pediatrics", "AVAILABLE"),
    ("Phototherapy Unit", "BiliBlanket Plus", "GE Healthcare", "PHO-PED-001", "Pediatrics", "MAINTENANCE"),
    ("Pulse Oximeter", "Radical-7", "Masimo", "POX-PED-001", "Pediatrics", "AVAILABLE"),
    ("Infant Warmer", "Panda Warmer", "GE Healthcare", "WAR-PED-001", "Pediatrics", "AVAILABLE"),
    # Neurology
    ("EEG Machine", "NicoletOne", "Natus", "EEG-NEU-001", "Neurology", "AVAILABLE"),
    ("CT Scanner", "Revolution CT", "GE Healthcare", "CT-NEU-001", "Neurology", "IN_USE"),
    ("MRI Scanner", "MAGNETOM Vida", "Siemens", "MRI-NEU-001", "Neurology", "AVAILABLE"),
    ("Neuro Stim", "Vyvanse 200", "Medtronic", "STIM-NEU-001", "Neurology", "RETIRED"),
    # General Medicine
    ("Hospital Bed", "TotalCare SpO2RT", "Hill-Rom", "BED-GEN-001", "General Medicine", "AVAILABLE"),
    ("IV Drip Stand", "IV-S2", "Generic Medical", "IV-GEN-001", "General Medicine", "AVAILABLE"),
    ("Wheelchair", "Breezy 600", "Sunrise Medical", "WHC-GEN-001", "General Medicine", "AVAILABLE"),
    ("Blood Pressure Monitor", "BP-700", "Omron", "BPM-GEN-001", "General Medicine", "IN_USE"),
    # Orthopedics
    ("X-Ray Machine", "MobileDiagnost", "Philips", "XR-ORT-001", "Orthopedics", "AVAILABLE"),
    ("Bone Drill", "Anspach eMax 2", "DePuy Synthes", "DRL-ORT-001", "Orthopedics", "AVAILABLE"),
    ("Plaster Trolley", "ORT-TR-2", "Hill-Rom", "TRL-ORT-001", "Orthopedics", "IN_USE"),
    ("Surgical Table", "Trumpf Mars", "Trumpf", "OPT-ORT-001", "Orthopedics", "MAINTENANCE"),
]

ROOMS_PER_DEPT = {
    # (number, room_type, floor, capacity, status)
    "Cardiology": [
        ("C-101", "CHECKUP", 1, 1, "AVAILABLE"),
        ("C-102", "CHECKUP", 1, 1, "AVAILABLE"),
        ("C-103", "EXAM", 1, 1, "OCCUPIED"),
        ("C-201", "OPERATING", 2, 1, "AVAILABLE"),
        ("C-301", "WARD", 3, 4, "OCCUPIED"),
        ("C-302", "WARD", 3, 4, "CLEANING"),
        ("C-401", "ICU", 4, 2, "AVAILABLE"),
    ],
    "Pediatrics": [
        ("P-101", "CHECKUP", 1, 1, "AVAILABLE"),
        ("P-102", "EXAM", 1, 1, "AVAILABLE"),
        ("P-103", "WARD", 1, 6, "OCCUPIED"),
        ("P-201", "WARD", 2, 4, "AVAILABLE"),
        ("P-202", "ICU", 2, 2, "OCCUPIED"),
        ("P-203", "OPERATING", 2, 1, "MAINTENANCE"),
    ],
    "Neurology": [
        ("N-101", "EXAM", 1, 1, "AVAILABLE"),
        ("N-102", "EXAM", 1, 1, "CLEANING"),
        ("N-201", "CHECKUP", 2, 1, "AVAILABLE"),
        ("N-301", "OPERATING", 3, 1, "AVAILABLE"),
        ("N-302", "ICU", 3, 2, "OCCUPIED"),
        ("N-401", "WARD", 4, 4, "AVAILABLE"),
    ],
    "General Medicine": [
        ("G-101", "CHECKUP", 1, 1, "AVAILABLE"),
        ("G-102", "CHECKUP", 1, 1, "OCCUPIED"),
        ("G-103", "EXAM", 1, 1, "AVAILABLE"),
        ("G-201", "WARD", 2, 8, "OCCUPIED"),
        ("G-202", "WARD", 2, 8, "CLEANING"),
        ("G-301", "ICU", 3, 2, "AVAILABLE"),
    ],
    "Orthopedics": [
        ("O-101", "CHECKUP", 1, 1, "AVAILABLE"),
        ("O-102", "EXAM", 1, 1, "AVAILABLE"),
        ("O-201", "OPERATING", 2, 1, "OCCUPIED"),
        ("O-202", "OPERATING", 2, 1, "AVAILABLE"),
        ("O-301", "WARD", 3, 6, "OCCUPIED"),
        ("O-302", "WARD", 3, 6, "MAINTENANCE"),
    ],
}

# (username, first, last, role, extra)
USERS = [
    ("admin", "Hospital", "Admin", "ADMIN", {"is_superuser": True, "is_staff": True, "phone": "+1-555-0100"}),
    ("pharmacist1", "Sara", "Khan", "PHARMACIST", {"license": "PH-1001", "phone": "+1-555-0101"}),
    ("pharmacist2", "Rami", "Halabi", "PHARMACIST", {"license": "PH-1002", "phone": "+1-555-0111"}),
    ("manager1", "John", "Reed", "MANAGEMENT", {"title": "Operations Manager", "phone": "+1-555-0102"}),
    ("manager2", "Priya", "Shah", "MANAGEMENT", {"title": "Chief of Staff", "phone": "+1-555-0112"}),
    # Doctors — covers every department, varied specialty + years 3..25
    ("doctor_cardio", "Lisa", "Adams", "DOCTOR", {"dept": "Cardiology", "specialization": "Cardiologist", "license": "MD-2001", "years": 14, "phone": "+1-555-0201"}),
    ("doctor_cardio2", "Khaled", "Aziz", "DOCTOR", {"dept": "Cardiology", "specialization": "Interventional Cardiologist", "license": "MD-2011", "years": 22, "phone": "+1-555-0211"}),
    ("doctor_pediatric", "Omar", "Said", "DOCTOR", {"dept": "Pediatrics", "specialization": "Pediatrician", "license": "MD-2002", "years": 9, "phone": "+1-555-0202"}),
    ("doctor_pediatric2", "Heba", "Nasr", "DOCTOR", {"dept": "Pediatrics", "specialization": "Neonatologist", "license": "MD-2012", "years": 7, "phone": "+1-555-0212"}),
    ("doctor_neuro", "Nina", "Cole", "DOCTOR", {"dept": "Neurology", "specialization": "Neurologist", "license": "MD-2003", "years": 18, "phone": "+1-555-0203"}),
    ("doctor_general", "Ahmed", "Younis", "DOCTOR", {"dept": "General Medicine", "specialization": "General Practitioner", "license": "MD-2004", "years": 5, "phone": "+1-555-0204"}),
    ("doctor_general2", "Maya", "Robles", "DOCTOR", {"dept": "General Medicine", "specialization": "Internist", "license": "MD-2014", "years": 11, "phone": "+1-555-0214"}),
    ("doctor_ortho", "David", "Levin", "DOCTOR", {"dept": "Orthopedics", "specialization": "Orthopedic Surgeon", "license": "MD-2005", "years": 25, "phone": "+1-555-0215"}),
    ("doctor_ortho2", "Fatima", "Bakr", "DOCTOR", {"dept": "Orthopedics", "specialization": "Sports Medicine", "license": "MD-2015", "years": 3, "phone": "+1-555-0216"}),
    # Nurses
    ("nurse_cardio", "Mona", "Hassan", "NURSE", {"dept": "Cardiology", "license": "RN-3001", "shift": "DAY", "phone": "+1-555-0301"}),
    ("nurse_pediatric", "Yara", "Fahmy", "NURSE", {"dept": "Pediatrics", "license": "RN-3002", "shift": "NIGHT", "phone": "+1-555-0302"}),
    ("nurse_neuro", "Tom", "Berg", "NURSE", {"dept": "Neurology", "license": "RN-3003", "shift": "DAY", "phone": "+1-555-0303"}),
    ("nurse_general", "Lara", "Park", "NURSE", {"dept": "General Medicine", "license": "RN-3004", "shift": "DAY", "phone": "+1-555-0304"}),
    ("nurse_ortho", "Sami", "Greer", "NURSE", {"dept": "Orthopedics", "license": "RN-3005", "shift": "NIGHT", "phone": "+1-555-0305"}),
    ("nurse_oncall", "Iris", "Lopez", "NURSE", {"dept": "General Medicine", "license": "RN-3006", "shift": "ON_CALL", "phone": "+1-555-0306"}),
    # Patients (15+)
    ("patient1",  "Aisha",   "Rahman",   "PATIENT", {"dob": "1985-03-12", "gender": "F", "blood": "A+",  "phone": "+1-555-0401", "address": "12 Maple Street, Apt 4B, Boston MA 02108"}),
    ("patient2",  "Ben",     "Cohen",    "PATIENT", {"dob": "1972-07-04", "gender": "M", "blood": "O-",  "phone": "+1-555-0402", "address": "47 Elm Avenue, Cambridge MA 02139"}),
    ("patient3",  "Carla",   "Gomez",    "PATIENT", {"dob": "1990-11-22", "gender": "F", "blood": "B+",  "phone": "+1-555-0403", "address": "88 Oak Drive, Somerville MA 02143"}),
    ("patient4",  "Daniel",  "Park",     "PATIENT", {"dob": "2015-02-18", "gender": "M", "blood": "AB+", "phone": "+1-555-0404", "address": "201 Pine Road, Brookline MA 02446"}),
    ("patient5",  "Eva",     "Schmidt",  "PATIENT", {"dob": "1965-09-30", "gender": "F", "blood": "A-",  "phone": "+1-555-0405", "address": "33 Cedar Lane, Newton MA 02458"}),
    ("patient6",  "Faisal",  "Ali",      "PATIENT", {"dob": "1988-06-15", "gender": "M", "blood": "O+",  "phone": "+1-555-0406", "address": "9 Birch Court, Quincy MA 02169"}),
    ("patient7",  "Grace",   "Liu",      "PATIENT", {"dob": "1995-12-03", "gender": "F", "blood": "B-",  "phone": "+1-555-0407", "address": "150 Walnut Street, Medford MA 02155"}),
    ("patient8",  "Hassan",  "Omar",     "PATIENT", {"dob": "1958-04-27", "gender": "M", "blood": "A+",  "phone": "+1-555-0408", "address": "76 Spruce Way, Watertown MA 02472"}),
    ("patient9",  "Ines",    "Costa",    "PATIENT", {"dob": "2002-08-09", "gender": "F", "blood": "AB-", "phone": "+1-555-0409", "address": "5 Larch Lane, Belmont MA 02478"}),
    ("patient10", "Julian",  "Becker",   "PATIENT", {"dob": "1978-01-14", "gender": "M", "blood": "O+",  "phone": "+1-555-0410", "address": "44 Aspen Way, Arlington MA 02474"}),
    ("patient11", "Kara",    "Singh",    "PATIENT", {"dob": "2010-05-20", "gender": "F", "blood": "B+",  "phone": "+1-555-0411", "address": "21 Hickory Ct, Lexington MA 02420"}),
    ("patient12", "Leon",    "Mwangi",   "PATIENT", {"dob": "1992-10-02", "gender": "M", "blood": "A-",  "phone": "+1-555-0412", "address": "60 Sycamore Pl, Waltham MA 02451"}),
    ("patient13", "Mei",     "Tanaka",   "PATIENT", {"dob": "1969-03-29", "gender": "F", "blood": "O-",  "phone": "+1-555-0413", "address": "13 Cypress Rd, Malden MA 02148"}),
    ("patient14", "Nadir",   "Ahmadi",   "PATIENT", {"dob": "1981-11-11", "gender": "O", "blood": "A+",  "phone": "+1-555-0414", "address": "8 Magnolia Ave, Revere MA 02151"}),
    ("patient15", "Olivia",  "Bennett",  "PATIENT", {"dob": "2018-06-07", "gender": "F", "blood": "AB+", "phone": "+1-555-0415", "address": "99 Sequoia Dr, Chelsea MA 02150"}),
]

DEFAULT_PASSWORD = "Pass1234!"


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

class Command(BaseCommand):
    help = "Seed the Hospital Management System with realistic demo data."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset', action='store_true',
            help='Wipe all existing data before re-seeding.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            self.stdout.write(self.style.WARNING("Resetting all data..."))
            self._reset()

        depts = self._seed_departments()
        drugs = self._seed_drugs()
        self._seed_equipment(depts)
        self._seed_rooms(depts)
        self._seed_drug_stock(depts, drugs)
        self._seed_users(depts)
        self._seed_doctor_availability()
        self._seed_appointments_and_records(depts, drugs)

        self.stdout.write(self.style.SUCCESS(
            f"\nSeed complete. Default password for all seeded users: '{DEFAULT_PASSWORD}'"
        ))
        self.stdout.write(
            "Try logging in as: admin, pharmacist1, manager1, doctor_cardio, "
            "nurse_cardio, patient1, etc."
        )

    # -- reset ---------------------------------------------------------------

    def _reset(self):
        Prescription.objects.all().delete()
        MedicalRecord.objects.all().delete()
        Appointment.objects.all().delete()
        DoctorAvailability.objects.all().delete()
        Room.objects.all().delete()
        DrugStock.objects.all().delete()
        Equipment.objects.all().delete()
        Drug.objects.all().delete()
        Patient.objects.all().delete()
        Doctor.objects.all().delete()
        Nurse.objects.all().delete()
        Pharmacist.objects.all().delete()
        Manager.objects.all().delete()
        User.objects.filter(role__in=['PATIENT', 'DOCTOR', 'NURSE', 'PHARMACIST', 'MANAGEMENT']).delete()
        Department.objects.all().delete()

    # -- departments / drugs / equipment / rooms / stock ---------------------

    def _seed_departments(self):
        depts = {}
        for name, desc in DEPARTMENTS:
            obj, _ = Department.objects.update_or_create(
                name=name, defaults={'description': desc}
            )
            depts[name] = obj
        self.stdout.write(f"  Departments: {len(depts)}")
        return depts

    def _seed_drugs(self):
        drugs = {}
        for name, generic, category, mfr, unit in DRUGS:
            obj, _ = Drug.objects.update_or_create(
                name=name,
                defaults={
                    'generic_name': generic, 'category': category,
                    'manufacturer': mfr, 'unit': unit,
                },
            )
            drugs[name] = obj
        self.stdout.write(f"  Drugs:       {len(drugs)} (WHO Essential Medicines list)")
        return drugs

    def _seed_equipment(self, depts):
        for name, model, mfr, serial, dept_name, status in EQUIPMENT:
            Equipment.objects.update_or_create(
                serial_number=serial,
                defaults={
                    'name': name, 'model_number': model, 'manufacturer': mfr,
                    'department': depts[dept_name], 'status': status,
                    'last_serviced': timezone.now().date() - timedelta(days=random.randint(10, 180)),
                },
            )
        self.stdout.write(f"  Equipment:   {len(EQUIPMENT)}")

    def _seed_rooms(self, depts):
        n = 0
        for dept_name, rooms in ROOMS_PER_DEPT.items():
            dept = depts[dept_name]
            for number, room_type, floor, capacity, status in rooms:
                Room.objects.update_or_create(
                    department=dept, number=number,
                    defaults={
                        'room_type': room_type, 'floor': floor,
                        'capacity': capacity, 'status': status,
                    },
                )
                n += 1
        self.stdout.write(f"  Rooms:       {n} across {len(depts)} departments")

    def _seed_drug_stock(self, depts, drugs):
        """Every (drug, department) gets a row. ~20% intentionally low for
        the management low-stock dashboard. Quantities span 10..200, with a
        handful below reorder_level (default 10)."""
        random.seed(42)
        n = 0
        for dept in depts.values():
            for drug in drugs.values():
                if random.random() < 0.20:
                    qty = random.randint(2, 9)  # below reorder
                else:
                    qty = random.randint(15, 200)
                expiry = timezone.now().date() + timedelta(days=random.randint(60, 720))
                DrugStock.objects.update_or_create(
                    drug=drug, department=dept,
                    defaults={
                        'quantity': qty, 'reorder_level': 10,
                        'expiry_date': expiry,
                    },
                )
                n += 1
        self.stdout.write(f"  Drug stock:  {n} rows ({len(drugs)} drugs × {len(depts)} departments)")

    # -- users ---------------------------------------------------------------

    def _seed_users(self, depts):
        hashed = make_password(DEFAULT_PASSWORD)
        n = 0
        for username, first, last, role, extra in USERS:
            user, created = User.objects.update_or_create(
                username=username,
                defaults={
                    'first_name': first, 'last_name': last,
                    'email': f"{username}@hospital.demo",
                    'role': role, 'password': hashed,
                    'phone': extra.get('phone', ''),
                    'is_superuser': extra.get('is_superuser', False),
                    'is_staff': extra.get('is_staff', False),
                },
            )
            if role == 'PATIENT':
                Patient.objects.update_or_create(
                    user=user,
                    defaults={
                        'date_of_birth': extra['dob'],
                        'gender': extra['gender'],
                        'blood_type': extra['blood'],
                        'address': extra.get('address', ''),
                    },
                )
            elif role == 'DOCTOR':
                Doctor.objects.update_or_create(
                    user=user,
                    defaults={
                        'department': depts[extra['dept']],
                        'specialization': extra['specialization'],
                        'license_number': extra['license'],
                        'years_of_experience': extra.get('years', random.randint(3, 25)),
                    },
                )
            elif role == 'NURSE':
                Nurse.objects.update_or_create(
                    user=user,
                    defaults={
                        'department': depts[extra['dept']],
                        'license_number': extra['license'],
                        'shift': extra['shift'],
                    },
                )
            elif role == 'PHARMACIST':
                Pharmacist.objects.update_or_create(
                    user=user,
                    defaults={'license_number': extra['license']},
                )
            elif role == 'MANAGEMENT':
                Manager.objects.update_or_create(
                    user=user,
                    defaults={'title': extra['title']},
                )
            n += 1
        self.stdout.write(
            f"  Users:       {n} (1 admin, 2 pharmacists, 2 managers, "
            f"8 doctors, 6 nurses, 15 patients)"
        )

    # -- doctor availability -------------------------------------------------

    def _seed_doctor_availability(self):
        """Every doctor gets Mon–Fri 09:00–17:00 in 30-min slots. Two specific
        doctors also get weekend / evening hours to demonstrate variety."""
        weekend_evening = {
            'doctor_cardio2': [(5, time(10, 0), time(14, 0))],   # Saturday morning
            'doctor_general': [(6, time(8, 0), time(12, 0)),     # Sunday morning
                               (2, time(17, 0), time(20, 0))],   # Wed evening clinic
        }
        total = 0
        for doc in Doctor.objects.select_related('user').all():
            # Weekday business hours (Mon=0 .. Fri=4)
            for weekday in range(0, 5):
                DoctorAvailability.objects.update_or_create(
                    doctor=doc, weekday=weekday, start_time=time(9, 0),
                    defaults={
                        'end_time': time(17, 0),
                        'slot_minutes': 30, 'active': True,
                    },
                )
                total += 1
            extras = weekend_evening.get(doc.user.username, [])
            for weekday, start_t, end_t in extras:
                DoctorAvailability.objects.update_or_create(
                    doctor=doc, weekday=weekday, start_time=start_t,
                    defaults={
                        'end_time': end_t,
                        'slot_minutes': 30, 'active': True,
                    },
                )
                total += 1
        self.stdout.write(f"  Availability: {total} rows across all doctors")

    # -- appointments + records + prescriptions ------------------------------

    def _seed_appointments_and_records(self, depts, drugs):
        now = timezone.now()
        # Look up doctors and patients we'll attach appointments to
        def doc(username):
            return Doctor.objects.get(user__username=username)
        def pat(username):
            return Patient.objects.get(user__username=username)

        cardio = doc('doctor_cardio')
        ped = doc('doctor_pediatric')
        neuro = doc('doctor_neuro')
        gen = doc('doctor_general')
        ortho = doc('doctor_ortho')

        # Mix of COMPLETED, CONFIRMED, PENDING + one CANCELLED so dashboards
        # have visible variety.
        appts = [
            (pat('patient1'), cardio, now - timedelta(days=2, hours=now.hour - 10, minutes=now.minute),
             "Chest pain on exertion", 'COMPLETED',
             {'diagnosis': 'Stable angina',
              'notes': 'ECG normal at rest. Recommend stress test.',
              'treatment': 'Lifestyle changes + statin therapy.',
              'rxs': [('Atorvastatin', '20 mg', 'once daily at night', '90 days', 'Take with food'),
                      ('Aspirin', '75 mg', 'once daily', 'ongoing', 'Low-dose cardioprotective')]}),
            (pat('patient2'), gen, now - timedelta(days=1, hours=now.hour - 14, minutes=now.minute),
             "Sore throat and fever", 'COMPLETED',
             {'diagnosis': 'Bacterial pharyngitis',
              'notes': 'Throat erythematous, tonsillar exudate. Strep test +.',
              'treatment': 'Oral antibiotics, hydration, rest.',
              'rxs': [('Amoxicillin', '500 mg', 'three times daily', '7 days', 'Complete the full course'),
                      ('Paracetamol', '500 mg', 'every 6 hours as needed', '5 days', 'For fever or pain')]}),
            (pat('patient5'), ortho, now - timedelta(days=4, hours=now.hour - 11, minutes=now.minute),
             "Knee pain after fall", 'COMPLETED',
             {'diagnosis': 'Meniscus tear (grade II)',
              'notes': 'MRI confirmed posterior horn tear.',
              'treatment': 'PT + NSAIDs; surgical referral if no improvement.',
              'rxs': [('Ibuprofen', '400 mg', 'three times daily', '14 days', 'Take with food')]}),
            (pat('patient3'), neuro, now + timedelta(days=3, hours=10 - now.hour), "Recurrent migraines", 'CONFIRMED', None),
            (pat('patient4'), ped, now + timedelta(days=5, hours=11 - now.hour), "Routine pediatric checkup", 'PENDING', None),
            (pat('patient6'), cardio, now + timedelta(days=7, hours=14 - now.hour), "Follow-up: hypertension", 'CONFIRMED', None),
            (pat('patient7'), gen, now + timedelta(days=4, hours=9 - now.hour), "Persistent cough", 'PENDING', None),
            (pat('patient10'), ortho, now + timedelta(days=10, hours=15 - now.hour), "Lower back assessment", 'CANCELLED', None),
        ]

        # Normalize all times to :00 or :30 so they land on real availability slots
        def normalize(dt):
            minute = 30 if dt.minute >= 30 else 0
            return dt.replace(minute=minute, second=0, microsecond=0)

        n_created = 0
        for patient, doctor, when, reason, status, record_data in appts:
            when = normalize(when)
            appt, _ = Appointment.objects.update_or_create(
                doctor=doctor, scheduled_at=when,
                defaults={
                    'patient': patient, 'reason': reason, 'status': status,
                },
            )
            n_created += 1
            if record_data:
                record, _ = MedicalRecord.objects.update_or_create(
                    appointment=appt,
                    defaults={
                        'diagnosis': record_data['diagnosis'],
                        'notes': record_data['notes'],
                        'treatment': record_data['treatment'],
                    },
                )
                record.prescriptions.all().delete()
                for drug_name, dose, freq, dur, instr in record_data['rxs']:
                    Prescription.objects.create(
                        medical_record=record,
                        drug=drugs.get(drug_name),
                        drug_name=drug_name,
                        dosage=dose, frequency=freq, duration=dur,
                        instructions=instr,
                    )

        self.stdout.write(
            f"  Appointments: {n_created} (3 completed with records + prescriptions, "
            f"4 upcoming, 1 cancelled)"
        )
