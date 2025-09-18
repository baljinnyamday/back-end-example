from dataclasses import dataclass
from ldap3 import Server, Connection, ALL, SUBTREE
from ldap3.core.exceptions import LDAPBindError

from app.core.config import settings
import json
from typing import List, Any
from datetime import datetime


@dataclass
class Attributes:
    department: List[str]
    display_name: List[str]
    distinguished_name: List[str]
    mail: List[str]
    mail_nickname: List[str]
    member_of: List[str]
    telephone_number: List[Any]
    title: List[str]


@dataclass
class LDAPUSER:
    attributes: Attributes
    dn: str


def authenticate_ldap(username, password):
    user_dn = rf"CORP\{username}"
    try:
        server = Server(settings.LDAP_SERVER_URI, get_info="NO_INFO")
        conn = Connection(server, user=user_dn, password=password, auto_bind=True)
        print(f"[+] Authentication successful for {username}")
        search_filter = f"(sAMAccountName={username})"
        conn.search(
            search_base=settings.LDAP_BASE,
            search_filter=search_filter,
            search_scope=SUBTREE,
            attributes=[
                "memberOf",
                "displayName",
                "mail",
                "telephoneNumber",
                "title",
                "department",
                "distinguishedName",
                "whenCreated",
                "mailNickname",
            ],
        )
        user_entry = None

        if not conn.entries:
            print("[-] User found, but no groups or info listed.")
            conn.unbind()
            return None, "User found, but no groups or info listed."
        else:
            # conn.entries can contain multiple entries if the search filter matches more than one user.
            # Normally, with (sAMAccountName={username}), only one user should match.
            # If there are multiple entries, they could be duplicate users or unexpected results.
            user_entry = conn.entries[0]

            groups = user_entry.memberOf.values if "memberOf" in user_entry else []
            # & gives the common elements between both sets, if its empty no intersection thus DAT USER AINT ALLOWED TO visit ZE WEB

            print(set(settings.LDAP_ALLOWED_GROUP) & set(groups))
            if not set(settings.LDAP_ALLOWED_GROUP) & set(groups):
                user_entry = None

        conn.unbind()
        # Convert LDAP entry to a dictionary
        return (
            (json.loads(user_entry.entry_to_json()), "Success")
            if user_entry
            else (
                None,
                r"""You are not in the ACCESS GROUP, contact support or your supervisor to get access.
                Check if you can visit following folder.---------------------------------------------
                \\burd\Data\T&IP\UG Geosciences\Geotechnical\45.Cave Management\05. Cave Monitoring\16. Weekly Inspection Photo
                """,
            )
        )

    except LDAPBindError:
        print(f"[!] Authentication failed for {username}. Wrong credentials?")
        return (
            None,
            f"Authentication failed. (Wrong credentials)",
        )
    except Exception as e:
        print(f"[!] LDAP error: {e}")
        return None, "LDAP error, (catostrophic failure.)"
