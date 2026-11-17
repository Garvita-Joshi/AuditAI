"""Typed purchase-request data shared by procurement and the LLM service."""
from datetime import date
from decimal import Decimal
from pydantic import BaseModel, Field, ConfigDict, field_validator


class PurchaseLine(BaseModel):
    model_config = ConfigDict(extra='ignore', str_strip_whitespace=True)
    description: str = Field(default='', max_length=500)
    line_type: str = Field(default='Item', max_length=40)
    quantity: int = Field(default=1, gt=0, le=1000000)
    unit_price: Decimal | None = Field(None, ge=0, max_digits=15, decimal_places=2)
    item_category: str | None = Field(None, max_length=100)
    department: str | None = Field(None, max_length=100)
    project: str | None = Field(None, max_length=200)
    location: str | None = Field(None, max_length=300)
    contract_start: date | None = None
    contract_end: date | None = None
    purchasing_method: str | None = Field(None, max_length=100)
    service_unit: str | None = Field(None, max_length=40)
    service_level: str | None = Field(None, max_length=2000)
    acceptance_owner: str | None = Field(None, max_length=200)
    verification_method: str | None = Field(None, max_length=100)

    @field_validator('quantity', mode='before')
    @classmethod
    def clean_line_qty(cls, v):
        if v is None or str(v).strip() in ('', '0'):
            return 1
        try:
            val = int(v)
            return max(1, val)
        except Exception:
            return 1

    @field_validator('unit_price', mode='before')
    @classmethod
    def clean_line_price(cls, v):
        if v is None or str(v).strip() == '':
            return None
        try:
            return Decimal(str(v).strip())
        except Exception:
            return None

    @field_validator('contract_start', 'contract_end', mode='before')
    @classmethod
    def clean_line_dates(cls, v):
        if not v or str(v).strip() == '':
            return None
        return v


class Requirements(BaseModel):
    model_config = ConfigDict(extra='ignore', str_strip_whitespace=True)
    department: str | None = Field(None, max_length=100)
    category: str | None = Field(None, max_length=100)
    business_purpose: str | None = Field(None, max_length=2000)
    shares_personal_data: bool | None = None
    data_sharing_choice: str | None = None
    data_types: list[str] = Field(default_factory=list, max_length=20)
    data_usage: str | None = Field(None, max_length=2000)
    payment_terms: str | None = Field(None, max_length=100)
    product: str | None = Field(None, max_length=500)
    quantity: int | None = None
    budget: Decimal | None = None
    currency: str | None = None
    delivery_deadline: date | None = None
    delivery_location: str | None = Field(None, max_length=300)
    specifications: str | None = Field(None, max_length=3000)
    mandatory_conditions: str | None = Field(None, max_length=3000)
    line_items: list[PurchaseLine] = Field(default_factory=list, max_length=100)
    vendor_preference: str | None = Field(None, max_length=30)
    preferred_vendors: str | None = Field(None, max_length=1000)
    purchase_type: str | None = Field(None, max_length=100)
    ai_selects_vendor: bool = True
    contract_start: date | None = None
    contract_end: date | None = None
    is_invoice_upload: bool = False

    @field_validator('contract_start', 'contract_end', 'delivery_deadline', mode='before')
    @classmethod
    def clean_dates(cls, v):
        if not v or str(v).strip() == '':
            return None
        return v

    @field_validator('budget', mode='before')
    @classmethod
    def clean_budget(cls, v):
        if v is None or str(v).strip() in ('', '0'):
            return None
        try:
            d = Decimal(str(v).strip())
            return d if d > 0 else None
        except Exception:
            return None

    @field_validator('quantity', mode='before')
    @classmethod
    def clean_qty(cls, v):
        if v is None or str(v).strip() in ('', '0'):
            return None
        try:
            val = int(v)
            return max(1, val)
        except Exception:
            return None

    @field_validator('product', 'delivery_location', 'specifications', 'mandatory_conditions',
                     'category', 'department', 'purchase_type', 'currency', 'payment_terms',
                     'data_sharing_choice', mode='before')
    @classmethod
    def clean_strings(cls, v):
        if not v or str(v).strip() == '':
            return None
        return v


QUESTIONS = {
    'product': 'What product or service do you need?',
    'quantity': 'How many units do you need?',
    'budget': 'What is your maximum total budget, including shipping and tax?',
    'currency': 'Which currency is the budget in (for example USD or INR)?',
    'delivery_deadline': 'What is the required delivery date?',
    'delivery_location': 'Which city and country should it be delivered to?',
    'specifications': 'Which specifications matter? Enter “None” if there are no preferences.',
    'mandatory_conditions': 'Which conditions are mandatory, such as warranty? Enter “None” if there are none.',
}


def missing(requirements):
    return [key for key in QUESTIONS if getattr(requirements, key) is None]
