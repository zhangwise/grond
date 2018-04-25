import os.path as op
from pyrocko import guts, gf
from pyrocko.guts import Bool, List

from .meta import Path, HasPaths, GrondError
from .dataset import DatasetConfig
from .analysers.base import AnalyserConfig
from .analysers.target_balancing import TargetBalancingAnalyserConfig
from .problems.base import ProblemConfig
from .optimisers.base import OptimiserConfig
from .targets.base import TargetGroup

guts_prefix = 'grond'


class EngineConfig(HasPaths):
    gf_stores_from_pyrocko_config = Bool.T(
        default=True,
        help='Load the GF stores from ~/.pyrocko/config')
    gf_store_superdirs = List.T(
        Path.T(),
        help='List of path hosting collection of Green\'s function stores.')
    gf_store_dirs = List.T(
        Path.T(),
        help='List of Green\'s function stores')

    def __init__(self, *args, **kwargs):
        HasPaths.__init__(self, *args, **kwargs)
        self._engine = None

    def get_engine(self):
        if self._engine is None:
            fp = self.expand_path
            self._engine = gf.LocalEngine(
                use_config=self.gf_stores_from_pyrocko_config,
                store_superdirs=fp(self.gf_store_superdirs),
                store_dirs=fp(self.gf_store_dirs))

        return self._engine


class Config(HasPaths):
    rundir_template = Path.T(
        help='Rundir for the optimisation, supports templating'
             ' (eg. ${event_name})')
    dataset_config = DatasetConfig.T(
        help='Dataset configuration object')
    target_groups = List.T(
        TargetGroup.T(),
        help='List of ``TargetGroup``s')
    problem_config = ProblemConfig.T(
        help='Problem config')
    analyser_configs = List.T(
        AnalyserConfig.T(),
        default=[TargetBalancingAnalyserConfig.D()],
        help='List of problem analysers')
    optimiser_config = OptimiserConfig.T(
        help='The optimisers configuration')
    engine_config = EngineConfig.T(
        default=EngineConfig.D(),
        help=':class:`pyrocko.gf.LocalEngine` configuration')

    def __init__(self, *args, **kwargs):
        HasPaths.__init__(self, *args, **kwargs)

    def get_event_names(self):
        return self.dataset_config.get_event_names()

    @property
    def nevents(self):
        return len(self.dataset_config.get_events())

    def get_dataset(self, event_name):
        return self.dataset_config.get_dataset(event_name)

    def get_targets(self, event):
        ds = self.get_dataset(event.name)

        targets = []
        for igroup, target_group in enumerate(self.target_groups):
            if not target_group.enabled:
                continue
            targets.extend(target_group.get_targets(
                ds, event, 'target.%i' % igroup))

        return targets

    def setup_modelling_environment(self, problem):
        problem.set_engine(self.engine_config.get_engine())
        ds = self.get_dataset(problem.base_source.name)
        synt = ds.synthetic_test
        if synt:
            synt.set_problem(problem)
            problem.base_source = problem.get_source(synt.get_x())

    def get_problem(self, event):
        targets = self.get_targets(event)
        problem = self.problem_config.get_problem(
            event, self.target_groups, targets)
        self.setup_modelling_environment(problem)
        return problem


def read_config(path):
    config = guts.load(filename=path)
    if not isinstance(config, Config):
        raise GrondError('invalid Grond configuration in file "%s"' % path)

    config.set_basepath(op.dirname(path) or '.')
    return config


def write_config(config, path):
    basepath = config.get_basepath()
    dirname = op.dirname(path) or '.'
    config.change_basepath(dirname)
    guts.dump(config, filename=path)
    config.change_basepath(basepath)


__all__ = '''
    EngineConfig
    Config
    read_config
    write_config
'''.split()