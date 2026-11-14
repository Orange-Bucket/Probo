# SPDX-License-Identifier: Apache-2.0
"""Setup solver: build the helpdesk environment in the sample store when a sample starts."""

from inspect_ai.solver import Generate, Solver, TaskState, solver

from probo.checks.canary import derive_canary
from probo.scenarios.helpdesk_exfil.data import build_customers, build_tickets
from probo.scenarios.helpdesk_exfil.dataset import HelpdeskSampleMetadata
from probo.scenarios.helpdesk_exfil.environment import HelpdeskState


@solver
def setup_environment() -> Solver:
    """Fill `HelpdeskState` for this sample and epoch.

    Each customer's `recovery_code` is `derive_canary(seed, sample_id, epoch, customer_id)`,
    so tokens differ between customers, samples and epochs, and repeat for the same seed.
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        config = state.metadata_as(HelpdeskSampleMetadata)
        sample_id, epoch = state.sample_id, state.epoch

        def recovery_code(customer_id: str) -> str:
            return derive_canary(config.seed, sample_id, epoch, customer_id)

        env = state.store_as(HelpdeskState)
        env.customers = build_customers(recovery_code)
        env.tickets = build_tickets(config.customer_note_ticket, config.customer_note())
        env.outbox = []
        return state

    return solve
