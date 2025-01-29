"""A module to interact with the aglint package"""

import json
from pathlib import Path
import subprocess
import re
from typing import Iterator, List
from pynpm import YarnPackage, NPMPackage
from tqdm import tqdm

__file__ = Path(__file__).resolve()
__dir__ = __file__.parent

AGLINT_PKG_PATH = __dir__ / "aglint-util"


def is_program_installed(program: str) -> bool:
    """Check if npm or yarn is installed on the system.
    Args:
        program (str): The program to check for. Either 'npm' or 'yarn'.

    Returns:
        bool: True if the program is installed, False otherwise.
    """

    assert program in ["npm", "yarn"], "Program must be either 'npm' or 'yarn'"

    try:
        subprocess.run(
            [program, "--version"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True

    except Exception:
        return False


def install_and_get_aglint(manager: str) -> YarnPackage | NPMPackage:
    """Make sure that the aglint package is installed.
    Args:
        manager (str): The package manager to use. Either 'npm' or 'yarn'.

    Returns:
        YarnPackage | NPMPackage: The package object.

    """

    Package = YarnPackage if manager == "yarn" else NPMPackage

    pkg = Package(
        (AGLINT_PKG_PATH / "package.json").absolute(), commands=["install", "run"]
    )

    if not (AGLINT_PKG_PATH / "node_modules").exists():
        pkg.install()

    return pkg


class AGLintBinding:
    """A class to interact with the aglint package"""

    class ParsingError(Exception):
        """Raised when there is an error parsing a rule"""

    @staticmethod
    def _get_pkg():
        manager = (
            "yarn"
            if is_program_installed("yarn")
            else "npm" if is_program_installed("npm") else None
        )

        if not manager:
            raise OSError("Neither npm nor yarn is installed")

        return install_and_get_aglint(manager)

    @staticmethod
    def parse_filter_list(fp: Path) -> Iterator["AdblockRule"]:
        """Parse a filter list file using aglint, turning each rule line into an AdblockRule object.

        Args:
            fp (Path): The path to the filter list file.

        Returns:
            Iterator[AdblockRule]: An iterator of AdblockRule rules.
        """

        pkg = AGLintBinding._get_pkg()

        # npm run parse file /path/to/file
        with pkg.run("parse", "file", str(fp.absolute()), wait=False) as process:
            # process line by line
            reading = False

            for line in process.stdout:
                if line.startswith(b"START_OUTPUT"):
                    reading = True
                    continue

                if line.startswith(b"END_OUTPUT"):
                    reading = False
                    continue

                if reading:
                    try:
                        rule_ats = json.loads(line)

                        if is_parser_error(rule_ats):
                            continue
                        if rule_ats["category"] == "Comment":
                            continue

                        yield AdblockRule(rule_ats)
                    except json.JSONDecodeError:
                        tqdm.write(f"Error parsing line: {line}")

    @staticmethod
    def parse_filter_rule(rule_text: str) -> "AdblockRule":
        """Parse a single filter rule using aglint, turning the rule into an AdblockRule object.

        Args:
            rule_text (str): The filter rule text.

        Returns:
            AdblockRule: The AdblockRule object.
        """

        pkg = AGLintBinding._get_pkg()

        with pkg.run("parse", "rule", json.dumps(rule_text), wait=False) as process:
            # process line by line
            reading = False

            for line in process.stdout:

                if line.startswith(b"START_OUTPUT"):
                    reading = True
                    continue

                if line.startswith(b"END_OUTPUT"):
                    reading = False
                    continue

                if reading:
                    try:
                        rule_ats = json.loads(line)

                        if is_parser_error(rule_ats):
                            raise AGLintBinding.ParsingError("Parser error")

                        return AdblockRule(rule_ats)
                    except json.JSONDecodeError:
                        tqdm.write(f"Error parsing line: {line}")

    @staticmethod
    def _parse_filter_rules_sync(rule_texts: list[str]) -> Iterator["AdblockRule"]:
        """
        Parse a list of filter rules using aglint, turning each rule line into 
        an AdblockRule object. All of these rules are passed to nodejs 
        in one command. it is not recommended to use this method for large lists.

        Args:
            rule_texts (list[str]): The filter rule texts.

        Returns:
            Iterator[AdblockRule]: An iterator of AdblockRule rules.

        """

        pkg = AGLintBinding._get_pkg()

        with pkg.run("parse", "rules", json.dumps(rule_texts), wait=False) as process:
            # process line by line
            reading = False

            for line in process.stdout:

                if line.startswith(b"START_OUTPUT"):
                    reading = True
                    continue

                if line.startswith(b"END_OUTPUT"):
                    reading = False
                    continue

                if reading:
                    try:
                        rule_ats = json.loads(line)

                        if is_parser_error(rule_ats):
                            yield None

                        yield AdblockRule(rule_ats)
                    except json.JSONDecodeError:
                        tqdm.write(f"Error parsing line: {line}")

    @staticmethod
    def parse_filter_rules(
        rule_texts: list[str], batch_size=10
    ) -> Iterator["AdblockRule"]:
        """Parse a list of filter rules using aglint, turning each rule line into an AdblockRule object.

        Args:
            rule_texts (list[str]): The filter rule texts.
            batch_size (int, optional): The batch size to use when parsing the rules. Each batch is passed to nodejs in one command. Defaults to 10.

        Returns:
            Iterator[AdblockRule]: An iterator of AdblockRule rules.

        """

        rules = []
        n_rules = len(rule_texts)
        n_iterations = n_rules // batch_size + 1

        for i in range(n_iterations):

            start = i * batch_size
            end = (i + 1) * batch_size if i != n_iterations - 1 else n_rules

            rules.extend(AGLintBinding._parse_filter_rules_sync(rule_texts[start:end]))

        return rules


def is_parser_error(rule: dict) -> bool:
    """Check if a rule dictionary output from nodejs is a parser error."""
    return rule["category"] == "ParserError"


class AdblockRule(object):
    """A representation of a filter rule with useful attributes and methods"""

    RESOURCE_TYPES = [
        "script",
        "image",
        "stylesheet",
        "object",
        "xmlhttprequest",
        "object-subrequest",
        "subdocument",
        "document",
        "other",
    ]

    BINARY_OPTIONS = [
        "script",
        "image",
        "stylesheet",
        "object",
        "xmlhttprequest",
        "object-subrequest",
        "subdocument",
        "document",
        "elemhide",
        "other",
        "background",
        "xbl",
        "ping",
        "dtd",
        "media",
        "third-party",
        "match-case",
        "collapse",
        "donottrack",
        "websocket",
        "doc",
    ]

    ADVANCED_OPTIONS = [
        "all",
        "badfilter",
        "cookie",
        "csp",
        "hls",
        "inline-font",
        "inline-script",
        "jsonprune",
        "network",
        "permissions",
        "redirect",
        "redirect-rule",
        "referrerpolicy",
        "removeheader",
        "removeparam",
        "replace",
        "noop",
        "empty",
        "mp4",
    ]

    JS_PATTERN = re.compile(r"/*\.js[^\w]*")
    IMG_PATTERN = re.compile(r"/*\.(png|jpg|jpeg|gif|webp|svg|bmp|ico)[^\w]*")
    STYLESHEET_PATTERN = re.compile(r"/*\.css[^\w]*")
    DOCUMENT_PATTERN = re.compile(
        r"/*\.(html|htm|php|asp|aspx|jsp|jspx|cfm|cgi|pl|py|rb|xml|json)[^\w]*"
    )

    __slots__ = [
        "raw_rule_text",
        "is_comment",
        "is_cosmetic_rule",
        "is_network_rule",
        "is_extended_css",
        "is_html_rule",
        "is_js_rule",
        "is_exception",
        "cosmetic_how",  # hide or remove
        "network_how",  # block or advanced
        "resource_type",  # script, image, stylesheet, etc.
        "raw_options",
        "options",
        "_options_keys",
        "rule_text",
        "regex",
        "regex_re",
        "_rule_ats",
    ]

    def __init__(self, rule_ats: dict):

        # defaults
        self.is_extended_css = False
        self.cosmetic_how = None
        self.network_how = None
        self.regex = None
        self._rule_ats = rule_ats

        self.raw_rule_text = self.rule_text = json.dumps(rule_ats["raws"]["text"])

        if self.raw_rule_text[0] == '"' and self.raw_rule_text[-1] == '"':
            self.raw_rule_text = self.raw_rule_text[1:-1]

        self.is_comment = rule_ats["category"] == "Comment"
        self.is_cosmetic_rule = rule_ats["category"] == "Cosmetic"
        self.is_network_rule = rule_ats["category"] == "Network"
        self.is_js_rule = rule_ats["type"] in (
            "JsInjectionRule",
            "ScriptletInjectionRule",
        )
        self.is_html_rule = rule_ats["type"] == "HtmlRule"
        self.is_exception = rule_ats.get("exception", False)

        # check cosmetic attributes
        if self.is_cosmetic_rule and not self.is_js_rule and not self.is_html_rule:

            self.is_extended_css = rule_ats["separator"]["value"] in (
                "#?#",
                "#@?#",
                "#$?#",
                "#@$?#",
            )

            if rule_ats["type"] == "ElementHidingRule":
                self.cosmetic_how = "hide"

            else:
                # there might be css injection ways to hide elements
                if any(
                    token in self.raw_rule_text
                    for token in [
                        "visibility: hidden",
                        "display: none",
                        "display:none",
                        "visibility:hidden",
                    ]
                ):
                    self.cosmetic_how = "hide"

                else:
                    # check if removed
                    if any(
                        token in self.raw_rule_text
                        for token in [
                            "remove()",
                            "remove: 1",
                            "remove:1",
                            "remove: true",
                            "remove:true",
                        ]
                    ):
                        self.cosmetic_how = "remove"

                    else:
                        self.cosmetic_how = "other"

        # if it is an html rule it is cosmetically removing
        if self.is_html_rule:
            self.cosmetic_how = "remove"

        self.options = {}
        if "modifiers" in rule_ats:
            for modifier in rule_ats["modifiers"]["children"]:
                if modifier["type"] == "Modifier":

                    if "value" in modifier:
                        modifier_value = modifier["value"]["value"]
                    else:
                        modifier_value = not modifier["exception"]

                    self.options[modifier["modifier"]["value"]] = modifier_value

        # check network attributes
        if self.is_network_rule:
            self.rule_text = json.dumps(rule_ats["pattern"]["value"])

            # check for how the network rule is blocking
            if any(key in self.ADVANCED_OPTIONS for key in self.options):
                self.network_how = "advanced"
            else:
                self.network_how = "block"

        self.resource_type = self.get_blocked_resource()

    @property
    def is_generic_rule(self) -> bool:
        """Check if the rule has a 'generic' scope"""

        return (
            (
                (self.is_network_rule and not self.is_exception)
                or (self.is_cosmetic_rule and (self.raw_rule_text.startswith("#")))
                or (self.is_js_rule and self.raw_rule_text.startswith("#%#"))
            )
            and "domain" not in self.options
            and "app" not in self.options
        )

    @property
    def activating_domains(self) -> List[str]:
        """Get the source domains where the rule would be checked in their contexts"""

        domains = []

        if self.is_cosmetic_rule:

            try:
                _domains, _ = self.raw_rule_text.split("#", 1)
            except ValueError:
                _domains = ""

            separator = ","
            if "|" in _domains:
                separator = "|"

            if len(_domains) > 0:
                domains.extend(_domains.split(separator))

        if self.is_network_rule:

            _domains = self.options.get("domain", "")

            separator = ","
            if "|" in _domains:
                separator = "|"

            domains = _domains.split(separator)
            # remove negatives
            domains = [domain for domain in domains if not domain.startswith("~")]

        return domains

    @property
    def is_third_party_rule(self):
        """
        Check if the rule is a third-party rule, i.e. flags domain only if found
        as third-party request in another domain
        """

        return (
            any(
                token in self.raw_rule_text
                for token in ("third-party", "3p", "3rd-party")
            )
            or "domain" in self.options
        )

    @property
    def is_well_formed(self):
        """Always True. Aglint will throw an error otherwise."""
        return True

    def get_blocked_resource(self):
        """
        Get the type of resource that the rule is blocking.
        Valid types are: script, image, stylesheet, script, domcument.
        Returns None if the type is not known or if the rule is not a network rule.
        """

        if not self.is_network_rule:
            return None

        if "script" in self.options or self.JS_PATTERN.search(self.rule_text):
            return "script"

        if "image" in self.options or self.IMG_PATTERN.search(self.rule_text):
            return "image"

        if "stylesheet" in self.options or self.STYLESHEET_PATTERN.search(
            self.rule_text
        ):
            return "stylesheet"

        if "document" in self.options or self.DOCUMENT_PATTERN.search(self.rule_text):
            return "document"

        return None

    def __repr__(self):
        return "AdblockRule(%r, is_network_rule=%r)" % (
            self.raw_rule_text,
            self.is_network_rule,
        )
