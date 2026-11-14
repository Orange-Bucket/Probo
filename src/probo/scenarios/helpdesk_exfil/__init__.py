# SPDX-License-Identifier: Apache-2.0
"""The helpdesk-exfil scenario: a helpdesk agent answers support tickets by e-mail.

The package is split so that other modules can import the environment (`environment`,
`keys`) without pulling in the task, and so this module stays free of import cycles.
"""
