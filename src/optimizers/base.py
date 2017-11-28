import logging

from pyrocko.guts import Object
from grond.meta import GrondError

guts_prefix = 'grond'

logger = logging.getLogger('grond.solver')


class BadProblem(GrondError):
    pass


class Optimizer(Object):

    def optimize(self, problem):
        raise NotImplemented()

    @property
    def niterations(self):
        raise NotImplementedError()


class OptimizerConfig(Object):
    pass


__all__ = '''
    BadProblem
    Optimizer
    OptimizerConfig
'''.split()