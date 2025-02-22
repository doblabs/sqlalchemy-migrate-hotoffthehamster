#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The migrate command-line tool."""

import sys
from inspect import getdoc, signature, Parameter
import logging
from optparse import OptionParser, BadOptionError

from sqlalchemy_migrate_hotoffthehamster import exceptions
from sqlalchemy_migrate_hotoffthehamster.versioning import api
from sqlalchemy_migrate_hotoffthehamster.versioning.config import *
from sqlalchemy_migrate_hotoffthehamster.versioning.util import asbool
import six


alias = dict(
    s=api.script,
    vc=api.version_control,
    dbv=api.db_version,
    v=api.version,
)

def alias_setup():
    global alias
    for key, val in six.iteritems(alias):
        setattr(api, key, val)
alias_setup()


class PassiveOptionParser(OptionParser):

    def _process_args(self, largs, rargs, values):
        """little hack to support all --some_option=value parameters"""

        while rargs:
            arg = rargs[0]
            if arg == "--":
                del rargs[0]
                return
            elif arg[0:2] == "--":
                # if parser does not know about the option
                # pass it along (make it anonymous)
                try:
                    opt = arg.split('=', 1)[0]
                    self._match_long_opt(opt)
                except BadOptionError:
                    largs.append(arg)
                    del rargs[0]
                else:
                    self._process_long_opt(rargs, values)
            elif arg[:1] == "-" and len(arg) > 1:
                self._process_short_opts(rargs, values)
            elif self.allow_interspersed_args:
                largs.append(arg)
                del rargs[0]

def main(argv=None, **kwargs):
    """Shell interface to :mod:`sqlalchemy_migrate_hotoffthehamster.versioning.api`.

    kwargs are default options that can be overriden with passing
    --some_option as command line option

    :param disable_logging: Let migrate configure logging
    :type disable_logging: bool
    """
    if argv is not None:
        argv = argv
    else:
        argv = list(sys.argv[1:])
    commands = list(api.__all__)
    commands.sort()

    usage = """%%prog COMMAND ...

    Available commands:
        %s

    Enter "%%prog help COMMAND" for information on a particular command.
    """ % '\n\t'.join(["%s - %s" % (command.ljust(28), api.command_desc.get(command)) for command in commands])

    parser = PassiveOptionParser(usage=usage)
    parser.add_option("-d", "--debug",
                     action="store_true",
                     dest="debug",
                     default=False,
                     help="Shortcut to turn on DEBUG mode for logging")
    parser.add_option("-q", "--disable_logging",
                      action="store_true",
                      dest="disable_logging",
                      default=False,
                      help="Use this option to disable logging configuration")
    help_commands = ['help', '-h', '--help']
    HELP = False

    try:
        command = argv.pop(0)
        if command in help_commands:
            HELP = True
            command = argv.pop(0)
    except IndexError:
        parser.print_help()
        return

    command_func = getattr(api, command, None)
    if command_func is None or command.startswith('_'):
        parser.error("Invalid command %s" % command)

    parser.set_usage(getdoc(command_func))

    # `inspect.getargspec` is deprecated. It returned a named tuple:
    #   ArgSpec(args, varargs, keywords, defaults)
    # - Haha, *Deprecated since version 3.0*!
    #     https://docs.python.org/3.2/library/inspect.html
    #   The upstream project, sqlalchemy-migrate, was pulled kicking and
    #   screaming from Python 2 into Python 3, I feel like. It was
    #   supported through Python 3.6, so I'm surprised there weren't
    #   deprecation warnings on this line (though not sure when it
    #   was eventually removed; perhaps Python silently supported it
    #   through at least 3.6).
    #
    #  # Deprecated since Py 3.0:
    #  f_args, f_varargs, f_kwargs, f_defaults = inspect.getargspec(command_func)
    sig = signature(command_func)
    # Convert Signature object to the old getargspec values used below.
    f_args = []
    f_defaults = []
    for name, param in sig.parameters.items():
        if param.kind is Parameter.POSITIONAL_OR_KEYWORD:
            f_args.append(name)
            if param.default is not Parameter.empty:
                f_defaults.append(param.default)
    if not f_defaults:
        f_defaults = None

    for arg in f_args:
        parser.add_option(
            "--%s" % arg,
            dest=arg,
            action='store',
            type="string")

    # display help of the current command
    if HELP:
        parser.print_help()
        return

    options, args = parser.parse_args(argv)

    # override kwargs with anonymous parameters
    override_kwargs = dict()
    for arg in list(args):
        if arg.startswith('--'):
            args.remove(arg)
            if '=' in arg:
                opt, value = arg[2:].split('=', 1)
            else:
                opt = arg[2:]
                value = True
            override_kwargs[opt] = value

    # override kwargs with options if user is overwriting
    for key, value in six.iteritems(options.__dict__):
        if value is not None:
            override_kwargs[key] = value

    # arguments that function accepts without passed kwargs
    f_required = list(f_args)
    candidates = dict(kwargs)
    candidates.update(override_kwargs)
    for key, value in six.iteritems(candidates):
        if key in f_args:
            f_required.remove(key)

    # map function arguments to parsed arguments
    for arg in args:
        try:
            kw = f_required.pop(0)
        except IndexError:
            parser.error("Too many arguments for command %s: %s" % (command,
                                                                    arg))
        kwargs[kw] = arg

    # apply overrides
    kwargs.update(override_kwargs)

    # configure options
    for key, value in six.iteritems(options.__dict__):
        kwargs.setdefault(key, value)

    # configure logging
    if not asbool(kwargs.pop('disable_logging', False)):
        # filter to log =< INFO into stdout and rest to stderr
        class SingleLevelFilter(logging.Filter):
            def __init__(self, min=None, max=None):
                self.min = min or 0
                self.max = max or 100

            def filter(self, record):
                return self.min <= record.levelno <= self.max

        logger = logging.getLogger()
        h1 = logging.StreamHandler(sys.stdout)
        f1 = SingleLevelFilter(max=logging.INFO)
        h1.addFilter(f1)
        h2 = logging.StreamHandler(sys.stderr)
        f2 = SingleLevelFilter(min=logging.WARN)
        h2.addFilter(f2)
        logger.addHandler(h1)
        logger.addHandler(h2)

        if options.debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)

    log = logging.getLogger(__name__)

    # check if all args are given
    try:
        num_defaults = len(f_defaults)
    except TypeError:
        num_defaults = 0
    f_args_default = f_args[len(f_args) - num_defaults:]
    # Assemble list of missing required arguments. (Note we use a "stable"
    # algorithm here, so the "Not enough arguments" line we add after the
    # USAGE message (which is prepended by parser.error) both show arguments
    # in the same order. Otherwise, some users — or maybe it's just me —
    # might do a double-take and then spend a few cycles wondering why the
    # two lists are ordered disparately.)
    required = []
    for arg in f_required:
        if arg not in f_args_default:
            required.append(arg)
    if required:
        parser.error("Not enough arguments for command %s: %s not specified" \
            % (command, ', '.join(required)))

    # handle command
    try:
        ret = command_func(**kwargs)
        if ret is not None:
            log.info(ret)
    except (exceptions.UsageError, exceptions.KnownError) as e:
        parser.error(e.args[0])

if __name__ == "__main__":
    main()
