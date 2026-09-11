from datetime import datetime

from pydantic import BaseModel


class AnalyticsOverview(BaseModel):
    orders_total: int
    successful_payments: int
    failed_payments: int
    cancelled_payments: int
    refunded_payments: int
    gross_revenue: int
    refunded_amount: int
    net_revenue: int
    average_payment_amount: float


class OrderAnalytics(BaseModel):
    orders_total: int
    cancelled_orders: int
    failed_orders: int
    orders_by_status: dict[str, int]
    average_order_value: float


class PaymentAnalytics(BaseModel):
    payments_total: int
    successful_payments: int
    failed_payments: int
    cancelled_payments: int
    refunded_payments: int
    gross_revenue: int
    refunded_amount: int
    success_rate: float
    refund_rate: float
    average_payment_amount: float


class RevenuePoint(BaseModel):
    period: datetime
    successful_payments: int
    gross_revenue: int
    refunded_amount: int
    net_revenue: int


class TopProduct(BaseModel):
    product_id: str
    product_name: str
    units_ordered: int
    orders_count: int
    revenue: int
