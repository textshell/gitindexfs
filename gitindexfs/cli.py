import sys

import click
import fuse

from logbook.handlers import StderrHandler
from logbook.compat import redirect_logging
from logbook import Logger, DEBUG, INFO

from dulwich.repo import Repo, NotGitRepository

from .fs import IndexFS

log = Logger('cli')


@click.command(help='Mount the index of a git repository at MOUNTPOINT')
@click.argument(
    'mountpoint',
    type=click.Path(file_okay=False,
                    dir_okay=True, exists=True), )
@click.option(
    '--root',
    '-r',
    default='.',
    type=click.Path(file_okay=False,
                    dir_okay=True, exists=True),
    help='Path to the git repository that is to be mounted at mountpoint', )
@click.option('--debug',
              '-d',
              default=False,
              is_flag=True,
              help='Enable debug output', )
@click.option('--fuse-debug',
              '-D',
              default=False,
              is_flag=True,
              help='When debug is enabled, also log fuse message')
def main(mountpoint, root, debug, fuse_debug):
    if fuse_debug:
        redirect_logging()

    # setup logging
    StderrHandler(level=DEBUG if debug else INFO).push_application()

    log.info('mounting index of {} onto {}'.format(root, mountpoint))

    try:
        repo = Repo(root)
    except NotGitRepository:
        log.info('Error: {} is not a git repository'.format(root))
        sys.exit(1)

    fuse.FUSE(IndexFS(root, repo, mountpoint), mountpoint, foreground=False)
