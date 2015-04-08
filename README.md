# Description

Juju plugin for defining a system upgrade plan.

## Example

The following is an example configuration used by this plugin. (WIP)

```yaml
juju-core:
  upgrade: true
  version: latest # pick the latest, or use "1.23.0"
  failure: abort  # on failure, abort your upgrade plan

steps:
#Here you define your upgrade plan steps
  0:
    postgresql:
      charm-store-revision: 3
      #branch: "@revision=foo,,@tag=foo"
      failure: continue  # on failure, continue with your upgrade plan
      force: false
      pre-upgrade:
        failure: continue # if any of the commands fails ( local or on the service unit ) continue.
        run:
          local:
              - "juju status"
          unit:
              - "ps -fea | grep pg"

      post-upgrade:
        failure: continue
        run:
          local:
            - "juju status"
          unit:
            - "ps -fea | grep mysql"
  1:
    rabbitmq-server:
      charm-store-revision: 4
      failure: continue
      force: true

#This will run , before any upgrade is applied (only local)
pre-upgrade:
  failure: abort
  run:
    local:
      - "juju status"

#This will run , after all the upgrades are applied
post-upgrade:
  failure: continue
  run:
    local:
    - "juju add-relation foo:bar bar:foo"

```
