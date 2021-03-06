CONFIG_FILE = "config.yaml"
MODULE_DIR = "./modules/"
CRAWlER_DIR = "./crawlers/"
DATA_DIR = "./app_data/"

import importlib.util
import os
exec_path = os.path.abspath('.')
config_path = os.path.join(exec_path, CONFIG_FILE)

_init_flag = False
config = None

modules_path = None
crawlers_path = None
data_path = None

import logging
log_level = logging.INFO
_logger = None

_loggers = {}
def create_logger(name):
  global log_level, _loggers
  if name in _loggers:
    return _loggers[name]
  else:
    logger = logging.getLogger(name)
    log_handler = logging.StreamHandler()
    log_format = logging.Formatter(
        f"[%(levelname)s] {name}: %(message)s"
        )
    log_handler.setFormatter(log_format)
    logger.addHandler(log_handler)
    logger.setLevel(log_level)
    _loggers[name] = logger
    return logger

from stocklab.args import Args
from stocklab.base_crawler import Crawler
from stocklab.base_module import Module, MetaModule
from stocklab.module import Primitive
from stocklab.db import get_db
from stocklab.error import *
from .states import set as set_state
from .states import get as get_state
__all__ = [
    'Args', 'Crawler', 'Module', 'MetaModule',
    'get_db', 'get_state', 'set_state',
    ]

# scopes of singletons
_modules = {}
_metamodules = {}
_crawlers = {}

def declare(_class):
  def _declare_in(scope):
    assert _class.__name__ not in scope
    scope[_class.__name__] = _class()

  global _modules, _crawlers
  if issubclass(_class, Module):
    _declare_in(_modules)
  elif issubclass(_class, Crawler):
    _declare_in(_crawlers)
  else:
    assert False, f'Class {_class.__name__} is not stocklab.Module nor stocklab.Crawler'

def change_log_level(level):
  global log_level
  log_level = level

  _tmp = {}
  _tmp.update(_metamodules)
  _tmp.update(_modules)
  _tmp.update(_crawlers)
  for m in _tmp.values():
    m.logger.setLevel(level)

  if not _init_flag:
    _init()

  global _logger
  _logger.setLevel(level)

def _create_singleton(prefix, name):
  path = os.path.join(prefix, name + '.py')
  spec = importlib.util.spec_from_file_location(name, location=path)
  assert spec, f"stocklab module {name} not found."
  target_module = importlib.util.module_from_spec(spec)
  spec.loader.exec_module(target_module)
  singleton = getattr(target_module, name)()

  if isinstance(singleton, MetaModule):
    scope = _metamodules
  elif isinstance(singleton, Module):
    scope = _modules
  elif isinstance(singleton, Crawler):
    scope = _crawlers
  else:
    assert False, 'Should not reach here'
  scope[name] = singleton

def get_module(module_name):
  if not _init_flag:
    _init()
  global _metamodules, _modules, modules_path
  if module_name in _metamodules:
    return _metamodules[module_name]
  elif module_name not in _modules:
    _create_singleton(modules_path, module_name)
  return _modules[module_name]

def get_crawler(crawler_name):
  if not _init_flag:
    _init()
  global _crawlers, crawlers_path
  if crawler_name not in _crawlers:
    _create_singleton(crawlers_path, crawler_name)
  return _crawlers[crawler_name]

def evaluate(path, peek=False, meta=False):
  assert '{' not in path
  assert '}' not in path
  if not _init_flag:
    _init()
  global _logger
  _logger.debug(f'evaluating: {path}')

  mod_name = path.split('.')[0].strip('()')
  if meta:
    assert mod_name in _metamodules, f'wrong module name? ({mod_name})'
  else:
    assert mod_name not in _metamodules, f'wrong meta-module name? ({mod_name})'

  mod = get_module(mod_name)
  if meta:
    mod.update()
  return mod._eval(path, peek=peek)

def peek(path):
  return evaluate(path, peek=True)

def metaevaluate(path, peek=False):
  return evaluate(path, peek=peek, meta=True)

def update(mod_name):
  mod = get_module(mod_name)
  assert isinstance(mod, MetaModule) or isinstance(mod, Primitive)
  return mod.update()

def debug_mode():
  print('switching to debug mode..')
  change_log_level(logging.DEBUG)

def _init():
  global _init_flag
  _init_flag = True

  global config, modules_path, crawlers_path, data_path
  from yaml import load, dump
  try:
    from yaml import CLoader as Loader, CDumper as Dumper
  except ImportError:
    from yaml import Loader, Dumper
  config = load(open(CONFIG_FILE, 'r').read(), Loader=Loader)
  root_path = os.path.abspath(config['root_dir'])
  modules_path = os.path.join(root_path, MODULE_DIR)
  crawlers_path = os.path.join(root_path, CRAWlER_DIR)
  data_path = os.path.join(root_path, DATA_DIR)

  global _logger
  _logger = create_logger('stocklab_core')

  for mc in os.listdir(modules_path):
    if mc[-3:] == '.py':
      m_name = mc[:-3]
      _create_singleton(modules_path, m_name)

  for m in _metamodules.keys():
    mod = _metamodules[m]
    mod.update()
