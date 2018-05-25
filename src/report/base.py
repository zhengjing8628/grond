import logging
import os.path as op
import shutil
import os
import tarfile

from http.server import HTTPServer, SimpleHTTPRequestHandler

from pyrocko import guts, util
from pyrocko.model import Event
from pyrocko.guts import Object, String

from grond.meta import HasPaths, Path, expand_template, GrondError

from grond import core, environment
from grond.problems import ProblemInfoNotAvailable, ProblemDataNotAvailable

guts_prefix = 'grond'
logger = logging.getLogger('grond.report')


class ReportIndexEntry(Object):
    path = String.T()
    problem_name = String.T()
    event_reference = Event.T(optional=True)
    event_best = Event.T(optional=True)


class ReportConfig(HasPaths):
    reports_base_path = Path.T(default='reports')
    report_sub_path = String.T(
        default='${event_name}/${problem_name}')


def read_config(path):
    config = guts.load(filename=path)
    if not isinstance(config, ReportConfig):
        raise GrondError(
            'invalid Grond report configuration in file "%s"' % path)

    config.set_basepath(op.dirname(path) or '.')
    return config


def iter_report_dirs(reports_base_path):
    for path, dirnames, filenames in os.walk(reports_base_path):
        for dirname in dirnames:
            dirpath = op.join(path, dirname)
            stats_path = op.join(dirpath, 'problem.yaml')
            if op.exists(stats_path):
                yield dirpath


def copytree(src, dst):
    names = os.listdir(src)
    if not op.exists(dst):
        os.makedirs(dst)

    for name in names:
        srcname = op.join(src, name)
        dstname = op.join(dst, name)
        if op.isdir(srcname):
            copytree(srcname, dstname)
        else:
            shutil.copy(srcname, dstname)


def report(env, report_config=None, update_without_plotting=False):
    if report_config is None:
        report_config = ReportConfig()
        report_config.set_basepath('.')

    event_name = env.get_current_event_name()
    problem = env.get_problem()
    logger.info('Creating report for event %s...' % event_name)

    fp = report_config.expand_path
    report_path = expand_template(
        op.join(
            fp(report_config.reports_base_path),
            report_config.report_sub_path),
        dict(
            event_name=event_name,
            problem_name=problem.name))

    if op.exists(report_path) and not update_without_plotting:
        shutil.rmtree(report_path)

    try:
        problem.dump_problem_info(report_path)

        util.ensuredir(report_path)
        plots_dir_out = op.join(report_path, 'plots')
        util.ensuredir(plots_dir_out)

        event = env.get_dataset().get_event()
        guts.dump(event, filename=op.join(report_path, 'event.reference.yaml'))

        try:
            rundir_path = env.get_rundir_path()

            core.export(
                'stats', [rundir_path],
                filename=op.join(report_path, 'stats.yaml'))

            core.export(
                'best', [rundir_path],
                filename=op.join(report_path, 'event.solution.best.yaml'),
                type='event-yaml')

            core.export(
                'mean', [rundir_path],
                filename=op.join(report_path, 'event.solution.mean.yaml'),
                type='event-yaml')

            core.export(
                'ensemble', [rundir_path],
                filename=op.join(report_path, 'event.solution.ensemble.yaml'),
                type='event-yaml')

        except (environment.NoRundirAvailable, ProblemInfoNotAvailable,
                ProblemDataNotAvailable):

            pass

        if not update_without_plotting:
            from grond import plot
            plot.make_plots(env, plots_path=op.join(report_path, 'plots'))

        rie = ReportIndexEntry(path='.', problem_name=problem.name)

        fn = op.join(report_path, 'event.solution.best.yaml')
        if op.exists(fn):
            rie.event_best = guts.load(filename=fn)

        fn = op.join(report_path, 'event.reference.yaml')
        if op.exists(fn):
            rie.event_reference = guts.load(filename=fn)

        fn = op.join(report_path, 'index.yaml')
        guts.dump(rie, filename=fn)

    except Exception:
        logger.warn(
            'report generation failed, removing incomplete report dir: %s'
            % report_path)

        if op.exists(report_path):
            shutil.rmtree(report_path)

    report_index(report_config)
    report_archive(report_config)


def report_index(report_config=None):
    if report_config is None:
        report_config = ReportConfig()

    reports_base_path = report_config.reports_base_path
    reports = []
    for report_path in iter_report_dirs(reports_base_path):
        logger.info('Indexing %s...' % report_path)

        fn = op.join(report_path, 'index.yaml')
        rie = guts.load(filename=fn)
        report_relpath = op.relpath(report_path, reports_base_path)
        rie.path = report_relpath
        reports.append(rie)

    guts.dump_all(
        reports,
        filename=op.join(reports_base_path, 'report_list.yaml'))

    app_dir = op.join(op.split(__file__)[0], 'app')
    copytree(app_dir, reports_base_path)
    logger.info('Created report in %s/index.html' % reports_base_path)


def report_archive(report_config):
    if report_config is None:
        report_config = ReportConfig()

    reports_base_path = report_config.reports_base_path

    logger.info('Generating report\'s archive...')
    with tarfile.open(op.join(reports_base_path, 'grond-reports.tar.gz'),
                      mode='w:gz') as tar:
        tar.add(reports_base_path, arcname='grond-reports')


class ReportHandler(SimpleHTTPRequestHandler):

    def _log_error(self, fmt, *args):
        logger.error(fmt % args)

    def _log_message(self, fmt, *args):
        logger.debug(fmt % args)


def serve_report(addr=('127.0.0.1', 8383), report_config=None):
    if report_config is None:
        report_config = ReportConfig()

    ip, port = addr

    os.chdir(report_config.reports_base_path)

    while True:
        try:
            httpd = HTTPServer((ip, port), ReportHandler)
            break
        except OSError:
            port += 1

    logger.info('Starting report webserver at http://%s:%d...' % (ip, port))
    httpd.serve_forever()


__all__ = '''
    report
    report_index
    ReportConfig
    ReportIndexEntry
    serve_report
    read_config
'''.split()
