from __future__ import absolute_import

# utilities for parsing the weird output of megacli

import functools
import re

NewBlock = object()

IGNORE = object()


def colon_field(expected_key, ty=str):
    COLON_SEPARATED_RE = re.compile(r'\s*(?P<key>.*\w)\s*:\s*(?P<value>.*)$')

    def parser(line):
        md = COLON_SEPARATED_RE.match(line)
        if not md:
            return
        key, value = md.groups()
        if expected_key is None or key == expected_key:
            return key, ty(value)
        else:
            return None

    return parser


def yesnobool(s):
    return s.lower() in ('yes', 'true')


def oknokbool(s):
    return s.lower() == 'ok'


def int_or_na(s):
    if s.upper() == 'N/A':
        return -1
    else:
        return int(s)


def parse_bytes(s):
    size, units = s.strip().split(' ')
    size = float(size)
    multiplier = {
        'PB': 1000 * 1000 * 1000 * 1000 * 1000,
        'TB': 1000 * 1000 * 1000 * 1000,
        'GB': 1000 * 1000 * 1000,
        'MB': 1000 * 1000,
        'KB': 1000,
        'B': 1,
    }.get(units, 1)
    return int(size * multiplier)


def parse_time(s):
    size, units = s.strip().split(' ')
    size = int(size)
    multiplier = {
        'days': 86400,
        'hours': 3600,
        'minutes': 60,
        'seconds': 1,
    }.get(units, 1)
    return int(size * multiplier)


def once_per_block(line_parser):
    @functools.wraps(line_parser)
    def parse(line):
        rv = line_parser(line)
        if rv is not None:
            return rv, NewBlock
        else:
            return rv, None
    return parse


def rule(line_parser):
    @functools.wraps(line_parser)
    def parse(line):
        return line_parser(line), None
    return parse


def ignore_rule(line_parser):
    @functools.wraps(line_parser)
    def parse(line):
        resp = line_parser(line)
        if resp is not None:
            return IGNORE, None
        else:
            return resp, None
    return parse


class BlockParser(object):
    def __init__(self, rules, default_constructor=lambda s: None):
        self.rules = rules
        self.default_constructor = default_constructor

    def parse(self, lines):
        rv = []
        current_state = {}
        for line in lines:
            for a_rule in self.rules:
                resp, create_new_block = a_rule(line)
                if current_state and create_new_block:
                    rv.append(current_state)
                    current_state = {}
                if resp is IGNORE:
                    break
                if resp is not None:
                    current_state[resp[0]] = resp[1]
                    break
            else:
                resp = self.default_constructor(line)
                if resp is not None:
                    current_state[resp[0]] = resp[1]
        if current_state:
            rv.append(current_state)
        return rv
