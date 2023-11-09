#!/usr/bin/env python3
import os
from pwd import getpwnam
from grp import getgrnam
import subprocess
from functools import lru_cache

from ops.charm import CharmBase
from ops.model import MaintenanceStatus, ActiveStatus
from ops.main import main

from constants import (
    GOTENBERG_USER,
    GOTENBERG_USER_SHELL,
    GOTENBERG_USER_HOME,
    GOTENBERG_GROUP,

    FONTS_PACKAGES,
    CHROMIUM_PACKAGES,
    LIBREOFFICE_PACKAGES,
    PDF_ENGINE_PACKAGES,
)

from gotenberg import (
    apt_update,
    apt_satisfy,

    TemplateRenderer
)


class GotenbergCharm(CharmBase):
    """Gotenberg charm operator class."""

    def __init__(self, *args):
        super().__init__(*args)
        self.framework.observe(self.on.install, self.on_install)

        self.renderer = TemplateRenderer("templates")

    @property
    def binary(self) -> str:
        return os.path.join(self.charm_dir, "gotenberg")

    @property
    def args(self) -> str:
        args = []

        string_options = [
            "api-timeout",
            "api-root-path",
            "api-trace-header",
            "chromium-allow-list",
            "chromium-deny-list",
            "chromium-host-resolver-rules",
            "chromium-proxy-server",
        ]

        boolean_options = [
            "chromium-allow-file-access-from-files",
            "chromium-allow-insecure-localhost",
            "chromium-ignore-certificate-errors",
            "chromium-disable-web-security",
            "chromium-incognito",
            "chromium-disable-javascript",
            "chromium-disable-routes",
            "libreoffice-disable-routes"
        ]

        int_options = [
            "chromium-failed-starts-threshold",
            "uno-listener-start-timeout",
            "uno-listener-restart-threshold"
        ]

        for arg in string_options:
            if self.model.config[arg] and not self.model.config[arg].isspace():
                args.append(f"--{arg}")
                args.append(self.model.config[arg])

        for arg in boolean_options:
            if self.model.config[arg]:
                args.append(f"--{arg}")

        for arg in int_options:
            args.append(f"--{arg}")
            args.append(self.model.config[arg])

        return " ".join(args)

    @property
    @lru_cache(1)
    def uid() -> int:
        try:
            return getpwnam(GOTENBERG_USER).pw_uid
        except KeyError:
            return GotenbergCharm.create_user()[1]

    @property
    @lru_cache(1)
    def gid() -> int:
        try:
            return getgrnam(GOTENBERG_GROUP).pw_gid
        except KeyError:
            return GotenbergCharm.create_group()[1]

    @staticmethod
    def create_user() -> (str, int):
        (group, gid) = GotenbergCharm.create_group()

        try:
            subprocess.run(["id", GOTENBERG_USER], check=True)
        except subprocess.CalledProcessError:
            subprocess.run([
                "useradd",
                "--gid", group,
                "--shell", GOTENBERG_USER_SHELL,
                "--home", GOTENBERG_USER_HOME,
                "--no-create-home",
                GOTENBERG_USER
            ])

            os.mkdir(GOTENBERG_USER_HOME)
            os.chown(GOTENBERG_USER_HOME, GotenbergCharm.uid, gid)

    @staticmethod
    def create_group() -> (str, int):
        try:
            subprocess.run(["getent", "group", GOTENBERG_GROUP], check=True)
        except subprocess.SubprocessError:
            subprocess.run(["groupadd", GOTENBERG_GROUP])

        return (GOTENBERG_GROUP, GotenbergCharm.gid)

    def install_dependencies(self) -> None:
        """Install the operating system dependencies for Gotenberg."""
        # Update the package cache
        apt_update()

        # Install font packages
        self.unit.status = MaintenanceStatus("Installing fonts...")
        apt_satisfy(FONTS_PACKAGES)

        # Install Chromium packages
        self.unit.status = MaintenanceStatus("Installing Chromium...")
        apt_satisfy(CHROMIUM_PACKAGES)

        # Install LibreOffice packages
        self.unit.status = MaintenanceStatus("Installing LibreOffice...")
        apt_satisfy(LIBREOFFICE_PACKAGES)

        # Install PDF engine packages
        self.unit.status = MaintenanceStatus("Installing PDF engine...")
        apt_satisfy(PDF_ENGINE_PACKAGES)

        self.unit.status = ActiveStatus()



    def render_service(self) -> None:
        self.renderer.render(
            "gotenberg.service.j2",
            "/etc/systemd/system/gotenberg.service",
            {
                "uid": self.uid,
                "gid": self.gid,
                "args": self.args,
                "binary": self.binary
            }
        )


    def on_install(self, _) -> None:
        """Install the requirements of the charm."""
        self.install_dependencies()

        self.render_service()







if __name__ == "__main__":
    main(GotenbergCharm)
