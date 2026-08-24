"""Typed row models for the structured data."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Account:
    account_id: str
    account_name: str
    plan: str
    status: str
    csm: str
    contract_file: str | None
    premium_support: bool
    notes: str


@dataclass(frozen=True)
class Order:
    order_id: str
    account_id: str
    carrier: str
    status: str
    booked_at: str
    pickup_window_start: str
    pickup_window_end: str
    pickup_actual_at: str | None
    shipment_fee_inr: int
    carrier_fault: bool
    customer_fault: bool
    cancellation_requested_at: str | None
    notes: str


@dataclass(frozen=True)
class Ticket:
    ticket_id: str
    account_id: str
    created_at: str
    status: str
    subject: str
    description: str
    channel: str
    assigned_to: str
    last_customer_message_at: str
    historical_resolution: str | None
