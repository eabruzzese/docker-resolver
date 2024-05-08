import re

from pathlib import Path

class ResolvConf:
    """A utility class for parsing the resolv.conf file."""

    search: list[str]
    nameserver: list[str]
    sortlist: list[str]
    options: dict[str, str]

    def __init__(self, path: str | Path = "/etc/resolv.conf") -> None:
        self._path = Path(path)
        self._raw = self._path.read_text()
        self.search = []
        self.nameserver = []
        self.sortlist = []
        self.options = {}
        self.parse()

    def parse(self) -> None:
        """Parse the resolve.conf file."""
        in_sortlist = False

        for lineno, line in enumerate(self._raw.splitlines()):
            # Strip comments
            line = re.sub(r"#.*$", "", line)

            # Strip whitespace
            line = line.strip()

            # Skip empty lines
            if not line:
                continue

            directive, *params = line.split()

            if directive == "sortlist":
                in_sortlist = True

            if directive == "search":
                self.search.extend(params)
            elif directive == "nameserver":
                self.nameserver.append(params[0])
            elif directive == "options":
                for param in params:
                    if ":" not in param:
                        self.options[param] = True
                    else:
                        key, value = param.split(":")
                        self.options[param] = value
            else:
                if in_sortlist:
                    self.sortlist.append(directive)
                else:
                    raise ValueError(f"Unknown resolve directive {directive} on line {lineno}.")

