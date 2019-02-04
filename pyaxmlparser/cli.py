import os

import click

from pyaxmlparser import APK


@click.command()
@click.argument('filename')
def main(filename):
    filename = os.path.expanduser(filename)
    apk = APK(filename)

    click.echo('APK: {}'.format(filename))
    click.echo('App name: {}'.format(apk.get_app_name()))
    click.echo('Package: {}'.format(apk.get_package()))
    click.echo('Version name: {}'.format(apk.get_androidversion_name()))
    click.echo('Version code: {}'.format(apk.get_androidversion_code()))
