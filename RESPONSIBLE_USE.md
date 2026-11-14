# Responsible use

Probo is a harness for attacking AI agents. This page sets out what it is for and how it is meant
to be run. Probo 0.1.0 contains one scenario and one injection template (see the
[README](README.md#limits)). This policy applies to every use of the code in this repository and
to every contribution, and will continue to apply to later releases.

## What Probo is for

- **The bundled range.** Releases on the current roadmap target only the scenario applications
  Probo ships. It is not designed as a general scanner for other systems.
- **Systems you are authorised to test.** Beyond the bundled range, use Probo only against
  systems you own, or that you have written authorisation from their owner to test.
- **Not third-party services.** Do not point Probo at third-party hosted agents, chat products,
  APIs or other services, including those of model providers, unless you have that written
  authorisation. Calling a model provider's API as the model under test inside the bundled range
  is the intended use and is different from attacking the provider's own products.

You are responsible for obtaining authorisation and for complying with the terms of service of any
model provider you use and with the law that applies to you. Nothing in this repository is legal
advice.

## Scope enforcement

Scope will be enforced at the network layer, not by instructions in a prompt. This is planned for
the containerised range (roadmap v0.2), which is to have an internal-only network, an egress
proxy, a declared scope file and a self-test of that isolation. Until that exists, nothing in Probo prevents a misconfigured run from reaching other
hosts, so do not rely on Probo to keep a run in scope.

## Treat the range as hostile

The range exists to feed adversarial text to agents, and an agent under attack may run tools or
code chosen by that text. Run it on the assumption that anything inside it can be controlled by
the attacker:

- do not mount host directories into range containers;
- do not expose the Docker socket to the range;
- do not place model provider keys or any other credentials inside the range; keep them on the
  host side of the harness;
- do not run the range on a machine or network that holds data you could not afford to leak.

## Reading results

A Probo result is evidence that a system is vulnerable to the attacks that were tried, under the
conditions of the run. It is never proof that a system is robust. A low attack success rate means
only that those attacks did not succeed in those trials. See the Limits section of the
[README](README.md#limits).

## Injection templates

The injection templates Probo ships are written for regression testing of the bundled range:
to check that its scenarios stay exploitable and that its checks keep detecting the result. They
are not a catalogue of attacks for use against other systems.

## Reporting

Report security problems in Probo itself, such as a way for range content to escape the sandbox
or reach the operator's credentials, as described in [SECURITY.md](SECURITY.md).
