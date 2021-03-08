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
    click.echo('Is it Signed: {}'.format(apk.signed))
    click.echo('Is it Signed with v1 Signatures: {}'.format(apk.signed_v1))
    click.echo('Is it Signed with v2 Signatures: {}'.format(apk.signed_v2))
    click.echo('Is it Signed with v3 Signatures: {}'.format(apk.signed_v3))
