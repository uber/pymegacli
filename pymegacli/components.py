import pipes
import subprocess
import re

from .parser import BlockParser
from .parser import colon_field
from .parser import once_per_block
from .parser import ignore_rule
from .parser import rule
from .parser import yesnobool
from .parser import oknokbool
from .parser import parse_bytes
from .parser import parse_time
from .parser import int_or_na


class MegaCLIBase(object):
    def __init__(self, megacli_path, log=None):
        self.megacli_path = megacli_path
        self.log = log

    def run_command(self, *args):
        exit_re = re.compile('^Exit Code: (.*)$')
        cmd = [self.megacli_path] + list(args)
        if self.log:
            self.log.debug('executing: ' + ' '.join(map(pipes.quote, cmd)))
        p = subprocess.Popen(
            cmd,
            shell=False,
            stdout=subprocess.PIPE
        )
        for line in p.communicate()[0].split('\n'):
            emd = exit_re.match(line)
            if emd:
                # exit code is usually meaningless
                rv = int(emd.groups()[0], 16)
                rv = rv
            else:
                yield line

    def extract_by_regex(self, regex, lines, one_only=False):
        if isinstance(regex, basestring):
            regex = re.compile(regex)
        result = []
        for line in lines:
            md = regex.match(line)
            if md:
                if one_only:
                    return md.groups()
                else:
                    result.append(md.groups)
        if one_only:
            raise Exception('Expected one match for %s, got %d. Input was %s' % (
                regex,
                len(result),
                '\n'.join(lines)
            ))
        return result

    @property
    def controller_count(self):
        return int(self.extract_by_regex(
            r'^Controller Count: ([^.]+)\.$',
            self.run_command('-adpCount'),
            one_only=True
        )[0])

    @property
    def controllers(self):
        for i in range(self.controller_count):
            yield MegaCLIController(i, self)


class Component(object):
    REQUIRED_FIELDS = tuple()

    def __init__(self, parent, props=None):
        if props is None:
            self.props = {}
        else:
            self.props = props
        self.parent = parent

    def __setitem__(self, key, value):
        self.props[key] = value

    def __getitem__(self, key):
        return self.props[key]

    def get(self, key, default=None):
        return self.props.get(key, default)

    @property
    def identifier(self):
        return NotImplementedError()

    @property
    def health_status(self):
        return NotImplementedError()

    @property
    def health_messages(self):
        for bad_key, bad_value in sorted(self.health_status[0].items()):
            yield '%s was unexpectedly %r' % (bad_key, bad_value)

    @property
    def healthy(self):
        return self.health_status[1]

    def __str__(self):
        return self.identifier

    @classmethod
    def from_output(kls, lines, parent):
        lds = []
        for d in kls.PARSER.parse(lines):
            args = []
            for f in kls.REQUIRED_FIELDS:
                args.append(d.pop(f))
            args.extend([parent, d])
            lds.append(kls(*args))
        return lds


class Disk(Component):
    ERROR_COUNT_KEYS = (
        'Media Error Count',
        'Predictive Failure Count',
    )
    ERROR_BOOL_KEYS = ('Drive has flagged a S.M.A.R.T alert', )
    REQUIRED_FIELDS = ('Enclosure Device ID', 'Slot Number')

    PARSER = BlockParser(rules=[
        once_per_block(colon_field('Enclosure Device ID', int_or_na)),
        rule(colon_field('Slot Number', int)),
        rule(colon_field('Other Error Count', int)),
        rule(colon_field('Predictive Failure Count', int)),
        rule(colon_field('Media Error Count', int)),
        rule(colon_field('Drive has flagged a S.M.A.R.T alert', yesnobool)),
    ], default_constructor=colon_field(None, str))

    def __init__(self, enclosure_id, slot_number, parent, props=None):
        self.enclosure_id = enclosure_id
        self.slot_number = slot_number
        self.thresholds = dict(
            (k, 0)
            for k
            in self.ERROR_COUNT_KEYS
        )
        super(Disk, self).__init__(parent, props)

    def set_threshold(self, key, value):
        self.thresholds[key] = value

    @property
    def identifier(self):
        return 'PhysDrv [%d:%d]' % (self.enclosure_id, self.slot_number)

    @property
    def health_status(self):
        status = {}
        overall_status = True
        for key, value in self.thresholds.items():
            if self.props.get(key, 0) > value:
                status[key] = self.props[key]
                overall_status = False
        for key in self.ERROR_BOOL_KEYS:
            if self.props.get(key, 0) != 0:
                status[key] = self.props[key]
                overall_status = False
        if 'Online' not in self['Firmware state']:
            status['Firmware state'] = self['Firmware state']
            overall_status = False
        return status, overall_status


class LogicalDevice(Component):
    PARSER = BlockParser(rules=[
        once_per_block(colon_field('Virtual Drive', lambda s: int(s.split(' ')[0]))),
        rule(colon_field('Bad Blocks Exist', yesnobool)),
        rule(colon_field('Size', parse_bytes))
    ], default_constructor=colon_field(None, str))

    REQUIRED_FIELDS = ('Name', )

    def __init__(self, name, parent, props=None):
        self.name = name
        super(LogicalDevice, self).__init__(parent, props)

    @property
    def identifier(self):
        return 'VD %r' % self.name

    @property
    def health_status(self):
        status = {}
        if self['State'] != 'Optimal':
            status['State'] = self['State']
        return status, not bool(status)


class BBU(Component):
    BAD_KEYS = (
        'Pack is about to fail & should be replaced',
        'Remaining Capacity Low',
        'Battery Pack Missing',
        'Battery Replacement required',
        'I2c Errors Detected',
    )
    UNEXPECTED_KEYS = ('Temperature',)

    PARSER = BlockParser(rules=[
        ignore_rule(colon_field('BBU status for Adapter')),
        once_per_block(colon_field('BatteryType')),
        rule(colon_field('Voltage', oknokbool)),
        rule(colon_field('Temperature', oknokbool)),
        rule(colon_field('Learn Cycle Requested', yesnobool)),
        rule(colon_field('Learn Cycle Active', yesnobool)),
        rule(colon_field('Learn Cycle Status', oknokbool)),
        rule(colon_field('Learn Cycle Timeout', yesnobool)),
        rule(colon_field('I2c Errors Detected', yesnobool)),
        rule(colon_field('Battery Pack Missing', yesnobool)),
        rule(colon_field('Battery Replacement required', yesnobool)),
        rule(colon_field('Remaining Capacity Low', yesnobool)),
        rule(colon_field('Periodic Learn Required', yesnobool)),
        rule(colon_field('Transparent Learn', yesnobool)),
        rule(colon_field('No space to cache offload', yesnobool)),
        rule(colon_field('Pack is about to fail & should be replaced', yesnobool)),
        rule(colon_field('Cache Offload premium feature required', yesnobool)),
        rule(colon_field('Module microcode update required', yesnobool)),
    ], default_constructor=colon_field(None, str))

    @property
    def identifier(self):
        return self.props['BatteryType']

    @property
    def health_status(self):
        status = {}
        if self['Battery State'] != 'Optimal':
            status['Battery State'] = self['Battery State']
        for key in self.BAD_KEYS:
            if self.get(key):
                status[key] = self[key]
        for key in self.UNEXPECTED_KEYS:
            if not self.get(key):
                status[key] = 'not ok'
        return status, not bool(status)


class MegaCLIController(object):
    def __init__(self, controller_number, parent):
        self.controller_number = controller_number
        self.parent = parent

    @property
    def patrol_read_status(self):
        """patrol reads are the background disk re-reads that constantly
        happen to detect failed blocks."""
        parser = BlockParser(rules=[
            rule(colon_field('Patrol Read Mode')),
            rule(colon_field('Patrol Read Execution Delay', parse_time)),
            rule(colon_field('Number of iterations completed', int)),
            rule(colon_field('Current State')),
        ])
        return parser.parse(
            self.parent.run_command('-AdpPR', '-Info', '-a%d' % self.controller_number)
        )[0]

    @property
    def PDs(self):
        return Disk.from_output(self.parent.run_command(
            '-PDList', 'a%d' % self.controller_number
        ), self)

    @property
    def LDs(self):
        return LogicalDevice.from_output(self.parent.run_command(
            '-LDInfo', '-Lall', '-a%d' % self.controller_number
        ), self)

    @property
    def BBUs(self):
        return BBU.from_output(self.parent.run_command(
            '-AdpBbuCmd -GetBbuStatus', '-a%d' % self.controller_number
        ), self)
