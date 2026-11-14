# SPDX-License-Identifier: Apache-2.0
"""Helpdesk environment state: tickets, customer records and the outbox, held per sample.

`HelpdeskState` is an Inspect `StoreModel`, so tools and scorers running in the same sample
see the same state through `store_as(HelpdeskState)`, and the log records it under the raw
keys in `keys` (`HelpdeskState:<field>`).
"""

from inspect_ai.util import StoreModel
from pydantic import BaseModel, ConfigDict, Field


class Order(BaseModel):
    """A customer's most recent order."""

    model_config = ConfigDict(frozen=True)

    order_id: str
    item: str
    status: str
    delivery_date: str


class Customer(BaseModel):
    """A customer record, including the per-run `recovery_code` marker token."""

    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    email: str
    order: Order
    recovery_code: str


class Ticket(BaseModel):
    """A support ticket written by a customer."""

    model_config = ConfigDict(frozen=True)

    id: str
    customer_id: str
    subject: str
    body: str


class Email(BaseModel):
    """An e-mail the agent sent."""

    model_config = ConfigDict(frozen=True)

    to: str
    subject: str
    body: str


class HelpdeskState(StoreModel):
    """The whole helpdesk application for one sample: what the tools read and write."""

    tickets: list[Ticket] = Field(default_factory=list[Ticket])
    customers: list[Customer] = Field(default_factory=list[Customer])
    outbox: list[Email] = Field(default_factory=list[Email])

    def ticket(self, ticket_id: str) -> Ticket | None:
        """The ticket with this id, or None."""
        return next((t for t in self.tickets if t.id == ticket_id), None)

    def customer(self, customer_id: str) -> Customer | None:
        """The customer with this id, or None."""
        return next((c for c in self.customers if c.id == customer_id), None)

    def send(self, email: Email) -> int:
        """Append an e-mail to the outbox and return its index."""
        # Reassign rather than append in place so the store sees a validated value.
        self.outbox = [*self.outbox, email]
        return len(self.outbox) - 1
