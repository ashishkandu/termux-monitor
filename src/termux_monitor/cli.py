import click

from .core import check_and_restart_wifi


@click.command()
def main():
    """
    Command line interface to check and restart Wi-Fi based on network operator and country.
    """
    result = check_and_restart_wifi()
    if result:
        click.echo("Wi-Fi restarted successfully.")
    else:
        click.echo("No action taken.")


if __name__ == "__main__":
    main()
