# Description

Juju plugin for defining a system upgrade plan.

## Example

The following is an example configuration used by this plugin. (WIP)

```yaml
juju-core:
  upgrade: true
  version: latest
  failure: abort

charms:
#Here you define the upgrade steps
  0:
    postgresql:
      charm-store-revision: 3
      #branch: "@revision=foo,,@tag=foo"
      failure: continue
      force: false

      pre-upgrade:
        failure: continue
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

#This will run , before any upgrade is applied
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
