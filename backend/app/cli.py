"""Command-line administration: `python -m app.cli create-admin --email you@example.com`."""

import argparse
import asyncio
import getpass
import sys

from pydantic import TypeAdapter, ValidationError

from app.core.settings import get_settings
from app.data_models.common import Email
from app.database.session import create_engine, create_session_factory
from app.domain.auth import create_admin
from app.domain.passwords import MIN_PASSWORD_LENGTH


async def _create_admin(email: str, password: str) -> None:
    engine = create_engine(get_settings().database_url)
    try:
        async with create_session_factory(engine)() as session:
            user = await create_admin(session, email, password)
            print(f"Admin ready: {user.email}. Sign in and enable two-factor authentication.")
    finally:
        await engine.dispose()


def main() -> None:
    """Parse arguments and run the requested command."""
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    admin = commands.add_parser("create-admin", help="create or promote an admin account")
    admin.add_argument("--email", required=True)
    args = parser.parse_args()

    try:
        email = TypeAdapter(Email).validate_python(args.email)
    except ValidationError:
        sys.exit("Invalid e-mail address.")
    password = getpass.getpass("Password: ")
    if len(password) < MIN_PASSWORD_LENGTH:
        sys.exit(f"Password must have at least {MIN_PASSWORD_LENGTH} characters.")
    if password != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match.")
    asyncio.run(_create_admin(email, password))


if __name__ == "__main__":
    main()
