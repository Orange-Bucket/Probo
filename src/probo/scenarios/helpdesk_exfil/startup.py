# SPDX-License-Identifier: Apache-2.0
"""Setup solver: build the helpdesk environment in the sample store when a sample starts."""

from inspect_ai.solver import Generate, Solver, TaskState, solver

from probo.checks.canary import derive_canary
from probo.scenarios.helpdesk_exfil.data import build_customers, build_tickets
from probo.scenarios.helpdesk_exfil.dataset import HelpdeskSampleMetadata
from probo.scenarios.helpdesk_exfil.environment import HelpdeskState
from probo.scenarios.helpdesk_exfil.keys import SCENARIO_ID


def marker_token(seed: int, sample_id: str | int, epoch: int, customer_id: str) -> str:
    """The `recovery_code` of a customer record in one sample and epoch.

    It is `derive_canary(seed, SCENARIO_ID, sample_id, epoch, customer_id)`. Pass the seed
    from the sample's own metadata (`keys.META_SEED`) to reproduce a logged token.
    """
    return derive_canary(seed, SCENARIO_ID, sample_id, epoch, customer_id)


@solver
def setup_environment() -> Solver:
    """Fill `HelpdeskState` for this sample and epoch.

    Each customer's `recovery_code` is `marker_token(...)` with the seed from the sample's
    own metadata, so tokens differ between customers, samples, epochs and scenarios, and
    repeat for the same seed.
    """

    async def solve(state: TaskState, generate: Generate) -> TaskState:
        config = state.metadata_as(HelpdeskSampleMetadata)
        sample_id, epoch = state.sample_id, state.epoch

        def recovery_code(customer_id: str) -> str:
            return marker_token(config.seed, sample_id, epoch, customer_id)

        env = state.store_as(HelpdeskState)
        env.customers = build_customers(recovery_code)
        env.tickets = build_tickets(config.customer_note_ticket, config.customer_note_text)
        env.outbox = []
        return state

    return solve
