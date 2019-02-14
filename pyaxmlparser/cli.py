import os

import click

from pyaxmlparser import APK


@click.command()
@click.argument('filename')
def main(filename):
    filename = os.path.expanduser(filename)
    apk = APK(filename)

    click.echo('APK: {}'.format(filename))
    click.echo('App name: {}'.format(apk.application))
    click.echo('Package: {}'.format(apk.packagename))
    click.echo('Version name: {}'.format(apk.version_name))
    click.echo('Version code: {}'.format(apk.version_code))
