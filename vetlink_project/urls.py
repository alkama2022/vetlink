from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('accounts.urls')),
    path('api/clinics/', include('clinics.urls')),
    path('api/patients/', include('patients.urls')),
    path('api/appointments/', include('appointments.urls')),
    path('api/treatments/', include('treatments.urls')),
    path('api/inventory/', include('inventory.urls')),
    path('api/billing/', include('billing.urls')),
    path('api/dashboard/', include('dashboard.urls')),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]