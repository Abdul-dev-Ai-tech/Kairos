"""Offline adapters. Future providers must verify signed webhooks and persist idempotent events.

Never trust a browser redirect as proof of payment. Add providers to this registry
only after implementing server-side confirmation and currency/amount matching.
"""
from dataclasses import dataclass
from django.core.exceptions import ValidationError

@dataclass(frozen=True)
class PaymentResult:
    status: str

class CashOnDelivery:
    def start(self, order):
        return PaymentResult('pending')

class ManualBankTransfer:
    def start(self, order):
        return PaymentResult('awaiting_verification')

PROVIDERS = {'cod': CashOnDelivery(), 'bank': ManualBankTransfer()}

def provider_for(code):
    if code not in PROVIDERS:
        raise ValidationError('This payment provider is not available.')
    return PROVIDERS[code]
