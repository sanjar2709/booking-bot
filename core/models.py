# Every model has to be imported here, so Alembic can see it when generating migrations
from apps.bookings.models import Booking
from apps.catalog.models import Service, Specialist, WorkingHours, specialist_services
from apps.users.models import User

__all__ = ('Booking', 'Service', 'Specialist', 'User', 'WorkingHours', 'specialist_services')
