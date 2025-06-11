import stripe
from src.config.settings import settings

stripe.api_key = settings.STRIPE_SECRET_KEY
