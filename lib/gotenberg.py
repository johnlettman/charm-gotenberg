#!/usr/bin/env python3
# Copyright 2023 John P. Lettman <the@johnlettman.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os
from subprocess import check_call, CalledProcessError
from typing import Iterable, Union
from jinja2 import Environment, FileSystemLoader
import shutil
import pwd
import stat


def set_owner_and_permissions(path, user, group, permissions):
    """Set owner and permissions for a file or directory."""
    if os.path.exists(path):
        current_owner = os.stat(path).st_uid
        current_group = os.stat(path).st_gid
        desired_owner = pwd.getpwnam(user).pw_uid
        desired_group = pwd.getpwnam(user).pw_gid
        if current_owner != desired_owner or current_group != desired_group:
            shutil.chown(path, user, group)

        current_permissions = stat.S_IMODE(os.lstat(path).st_mode)
        if current_permissions != permissions:
            os.chmod(path, permissions)


class TemplateRenderer:
    """Helper class to render a template file."""

    def __init__(self, template_dir) -> None:
        self.template_dir = template_dir
        self.env = Environment(loader=FileSystemLoader(self.template_dir))
        pass

    def render(self, template, target, context, user="root", group="root", permissions=0o644):
        """Render a template to a file."""
        template = self.env.get_template(template)
        with open(target, "w") as f:
            f.write(template.render(context))
        set_owner_and_permissions(target, user, group, permissions)


def apt_update() -> None:
    """Update the apt package cache."""
    cmd = ["apt-get", "update"]
    check_call(cmd, universal_newlines=True)


def apt_satisfy(packages: Union[Iterable[str], str]) -> None:
    """Satisfy package dependencies through apt."""
    if is_iterish(packages):
        packages = ", ".join(packages)

    cmd = ["apt", "satisfy", "-y", packages]
    env = {**os.environ, "DEBIAN_FRONTEND": "noninteractive"}
    check_call(cmd, universal_newlines=True, env=env)


def is_iterish(obj: any) -> bool:
    """Check whether an object is strictly a list-like iterable."""
    try:
        iter(obj)  # Will raise TypeError if not iterable
        return not isinstance(obj, (str, bytes, bytearray))
    except TypeError:
        return False

def sd_daemon_reload() -> None:
    cmd = ["systemctl", "daemon-reload"]
    check_call(cmd, universal_newlines=True)


def sd_enable(unit: str, now: bool = False) -> None:
    cmd = ["systemctl", "enable", unit]
    if now:
        cmd.append("--now")

    check_call(cmd, universal_newlines=True)

# Credit: Przemyslaw Lal @przemeklal
# https://github.com/canonical/charm-local-juju-users/blob/e96fcd6319cda3743b237c8090deba3b32b37de0/lib/local_juju_users.py#L114
def linux_user_exists(user):
    """Return True if the user exists on the system."""
    cmd = ["getent", "passwd", user]
    try:
        check_call(cmd)
        return True
    except CalledProcessError:
        return False
