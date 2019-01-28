#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals, print_function

import os
import sys
import argparse
from codecs import open

try:
    from .__init__ import (
        __version__, __title__, __package_name__, APK, AXMLPrinter)
    from . import utils
except (ValueError, ImportError):
    from __init__ import  (
        __version__, __title__, __package_name__, APK, AXMLPrinter)
    import utils


def get_files(args):
    check_files = []
    if args.path:
        for item_path in args.path:
            if isinstance(item_path, utils.string_types) and \
               item_path and os.path.exists(item_path):
                if os.path.isdir(item_path):
                    for root, dirs, files in os.walk(item_path):
                        for item_file in files:
                            if item_file not in check_files:
                                check_files.append(os.path.join(root, item_file))
                else:
                    if item_path not in check_files:
                        check_files.append(item_path)
    return check_files


def get_info(args):
    check_files = get_files(args)
    if check_files:
        for item_file in check_files:
            error = ''
            try:
                apk = APK(item_file, debug=args.debug)
            except Exception as error_message:
                apk = None
                error = str(error_message)
            message = 'APK {} :\n'.format(item_file)
            if apk:
                message += '  App name: {}\n'.format(apk.application)
                message += '  Package: {}\n'.format(apk.package)
                message += '  Version name: {}\n'.format(apk.version_name)
                message += '  Version code: {}\n'.format(apk.version_code)
            else:
                message += '  Can\'t get info with error: {}\n'.format(error)
            print(message)
    else:
        print('Error. path for check APK - {0} not found'.format(args.path), file=sys.stderr)
        exit(1)


def get_xml(args):
    output = None
    if isinstance(args.output, utils.string_types) and \
       args.output and os.path.exists(os.path.dirname(args.output)):
        output = args.output
    check_files = get_files(args)
    if check_files:
        for item_file in check_files:
            try:
                xml_string = AXMLPrinter(item_file, debug=args.debug).get_xml()
            except Exception as error_message:
                xml_string = None
                print(str(error_message), file=sys.stderr)
                exit(1)
            if xml_string:
                if output:
                    with open(output, 'wb', encoding='utf-8') as xml_file:
                        xml_file.write(xml_string)
                else:
                    print(xml_string)
    else:
        print('Error. path for output xml - {0} not found'.format(args.path), file=sys.stderr)
        exit(1)


def get_parser():
    parser = argparse.ArgumentParser(
        prog='python -m {}'.format(__package_name__),
        description='Help for work with {} version {}'.format(__title__, __version__),
        usage='%(prog)s [-h] [options]',
        add_help=True, formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '--version', action='version',
        version='{} version {}'.format(__title__, __version__))

    parser.add_argument(
        '-d', '--debug', action='store_true', default=False,
        help='Enable debug message.')

    parser.add_argument(
        'path', nargs='+', type=str,
        default=None, help='path for file or dir.')

    subparsers = parser.add_subparsers(help='List of commands')

    info_parser = \
        subparsers.add_parser(
            'info', help='output info from file')
    info_parser.set_defaults(func=get_info)

    xml_parser = \
        subparsers.add_parser(
            'xml', help='output xml from file')
    xml_parser.add_argument('-o', '--output', action='store',
                            type=str, default=None,
                            help='save xml to file.')
    xml_parser.set_defaults(func=get_xml)

    help_message = parser.format_help() + '\n '
    # retrieve subparsers from parser
    subparsers_actions = [
        action for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)]
    # there will probably only be one subparser_action,
    # but better save than sorry
    for subparsers_action in subparsers_actions:
        # get all subparsers and print help
        for choice, subparser in subparsers_action.choices.items():
            help_message += 'Subparser \'{0}\'\n {1}\n'.format(
                choice, find_options(subparser.format_help(), choice))
    parser.epilog = help_message
    return parser.parse_args()


def find_options(help_text=None, choice=None):
    """
    Return a substring with the optional arguments
    :param help_text: Help text, as it's called
    :param choice: Name subparser name, as it's called
    :return:
    """
    if not isinstance(help_text, utils.string_types):
        help_text = ''
    if not isinstance(choice, utils.string_types):
        choice = 'unknown'
    new_list = []
    for line in help_text.split('\n'):
        if line == 'optional arguments:':
            new_list.append('optional arguments for {0}:'.format(choice))
        else:
            new_list.append(line)
    return '\n'.join(new_list)


def main():
    args = get_parser()
    args.func(args)


if __name__ == '__main__':
    main()
