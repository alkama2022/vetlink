from rest_framework import viewsets, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import timedelta
from appointments.models import Appointment
from patients.models import AnimalPatient
from treatments.models import Treatment
from billing.models import Invoice

class DashboardViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    
    @action(detail=False, methods=['get'])
    def vet_dashboard(self, request):
        clinic = request.user.clinic_set.first()
        if not clinic:
            return Response({'error': 'Clinic not found'}, status=404)
        
        today = timezone.now().date()
        start_of_day = timezone.make_aware(datetime.combine(today, time.min))
        end_of_day = timezone.make_aware(datetime.combine(today, time.max))
        
        # Get today's metrics
        today_appointments = Appointment.objects.filter(
            clinic=clinic,
            appointment_date__range=[start_of_day, end_of_day]
        ).count()
        
        today_patients = AnimalPatient.objects.filter(
            clinic=clinic,
            created_at__date=today
        ).count()
        
        today_income = Invoice.objects.filter(
            clinic=clinic,
            created_at__date=today
        ).aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        pending_lab = LabTest.objects.filter(
            clinic=clinic,
            status='PENDING'
        ).count()
        
        return Response({
            'appointments': today_appointments,
            'patients_seen': today_patients,
            'today_income': today_income,
            'pending_lab': pending_lab,
        })