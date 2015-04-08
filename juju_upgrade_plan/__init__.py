import yaml
import os
import subprocess
import shlex
import sys
import logging

__author__ = "Jorge Niedbalski <jnr@metaklass.org>"


logger = logging.getLogger(__name__)
dot = os.path.abspath(os.path.dirname(__file__))


def run_unit(service, cmd):
    return yaml.load(run(
        'juju run --service {0} "{1}"--format=yaml'.format(
            service, cmd)))


def run(cmd):
    return subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)


def check(cmd):
    return subprocess.check_call(shlex.split(cmd), stderr=subprocess.STDOUT,
                                 stdout=subprocess.PIPE)


def get_environment():
    environment = os.environ.get("JUJU_ENV", None)
    if not environment:
        try:
            environment = run("juju env").strip()
        except:
            environment = None
    return environment


def load_config(filepath=os.path.join(dot, "config.yaml")):
    print filepath
    with open(filepath) as config:
        return yaml.load(config.read())


def get_juju_version():
    return run("juju --version").split("-")[0].split(".")


def must_upgrade_juju(major, minor, fix):
    c_major, c_minor, c_fix = get_juju_version()
    if major > c_major:
        return True
    if major > c_major and minor > c_minor:
        return True
    if major > c_major and minor > c_minor and fix > c_fix:
        return True
    return False


class JujuUpgradeError(Exception):
    pass


class HookNotFound(Exception):
    pass


class HookAbort(Exception):
    pass


def run_hook(name, config, service=None):
    hook = config.get(name, False)

    if not hook:
        raise HookNotFound(name)

    run = hook.get("run", None)
    failure = hook.get('failure', 'abort')

    if run:
        (local, unit) = (run.get("local", None),
                         run.get("unit", None))

        if local:
            logger.info("Running %s hooks on local machine" % name)
            for cmd in local:
                logger.info("Executing '%s'" % cmd)
                try:
                    check(cmd)
                except Exception as ex:
                    if failure in ('abort', ):
                        msg = "failure set to abort: Error executing hook: %s, cmd: %s, error: %s" % \
                              (name, cmd, ex)
                        logger.warn(msg)
                        raise HookAbort(msg)
                    else:
                        logger.warn(
                            "Hook:%s failed, but failure mode has been set to continue, error:%s" % (name, ex))

        if unit:
            for cmd in unit:
                try:
                    output = run_unit(service, cmd)
                except Exception as ex:
                    if failure in ("abort", ):
                        msg = "Error executing hook: %s, error: %s" % (
                            name, ex)
                        logger.warn(msg)
                        raise HookAbort(msg)
                    else:
                        logger.warn(
                            "Hook:%s failed, but failure mode has been set to continue, error:%s" % (
                                name, ex))
                else:
                    for unit in output:
                        unit_id = unit.get("MachineId")
                        logger.info(
                            "Running hook: %s on remote unit: %s" % (name,
                                                                     unit_id))
                        if 'Stderr' in unit:
                            err = unit.get('Stderr')
                            if failure in ("abort", ):
                                msg = "failure set to abort: Error executing hook: %s, cmd: %s, error: %s, unit: %s" % \
                                      (name, cmd, err, unit_id)
                                logger.warn(msg)
                                raise HookAbort(msg)
                            else:
                                logger.warn(
                                    "Hook:%s failed, but failure mode has been set to continue, error:%s" % (
                                        name, err))


def upgrade_charm_from_cs(service, revision, force=False):
    cmd = "juju upgrade-charm --revision %s" % revision
    if force:
        cmd += " --force"
    logger.info("Upgrading service: %s, cmd: %s" % (service, cmd))
    return check(cmd + " %s" % service)


def upgrade_juju(config):
    version = config.get("version", None)

    if not version == "latest":
        if must_upgrade_juju(*version.split(".")):
                upgrade_cmd = "juju upgrade-juju --yes --version {0}".format(
                    version)
        else:
            upgrade_cmd = "juju upgrade-juju --yes".strip("\n")
        try:
            logger.info("Performing juju-core upgrade: %s" % upgrade_cmd)
            check(upgrade_cmd)
        except Exception as ex:
            logger.warn(ex)
            if config.get('failure', 'abort') in ('abort', ):
                raise JujuUpgradeError(
                    "Error updating juju-core: %s" % ex)


def do_upgrade(config):

    try:
        run_hook("pre-upgrade", config)
    except HookNotFound as ex:
        logger.warn("Hook: %s not defined" % ex)

    juju_core_config = config.get('juju-core', None)

    if juju_core_config and juju_core_config.get("upgrade", False):
        try:
            upgrade_juju(juju_core_config)
        except JujuUpgradeError:
            raise

    steps = config.get('steps', None)

    if not steps:
        logger.warn("Not defined upgrade steps to perform")

    for step, services in steps.items():
        logger.info("Performing upgrade step %d" % step)

        for service, service_config in services.items():
            logger.info("Upgrading service: %s" % service)

            try:
                run_hook("pre-upgrade", service_config,
                         service=service)
            except HookNotFound as ex:
                logger.info("Hook:%s not defined on service: %s" % (ex, service))

            charm_store_revision = service_config.get(
                "charm-store-revision",
                None)

            if charm_store_revision:
                failure = service_config.get('failure', 'abort')
                try:
                    upgrade_charm_from_cs(
                        service, charm_store_revision,
                        force=service_config.get("force",
                                                 False))
                except Exception as ex:
                    if failure in ('abort', ):
                        msg = "Cannot upgrade service:%s, error:%s" % (service,
                                                                       ex)
                        logger.warn(msg)
                        raise Exception(msg)
                    else:
                        logger.warn(
                            "Upgrade for service:%s failed, but failure mode has been set to continue, error:%s" % (
                                service, ex))
                else:
                    try:
                        run_hook("post-upgrade", service_config,
                                 service=service)
                    except HookNotFound as ex:
                        logger.warn("Hook:%s not defined on service: %s" % (ex,
                                    service))

    try:
        run_hook("post-upgrade", config)
    except HookNotFound as ex:
        logger.warn("Hook: %s not defined" % ex)


def main():
    logging.basicConfig(level=logging.INFO)
    do_upgrade(load_config(filepath=sys.argv[1]))
