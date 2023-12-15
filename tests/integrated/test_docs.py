import doctest
import os


from sqlalchemy_migrate_hotoffthehamster.tests import fixture

# Collect tests for all handwritten docs: doc/*.rst

dir = ('..','..','doc','source')
absdir = (os.path.dirname(os.path.abspath(__file__)),)+dir
dirpath = os.path.join(*absdir)
files = [f for f in os.listdir(dirpath) if f.endswith('.rst')]
paths = [os.path.join(*(dir+(f,))) for f in files]
assert len(paths) > 0
suite = doctest.DocFileSuite(*paths)

# SAVVY/2023-12-15: (lb): I thought doctest was just for Docstrings, but you can run
# it on reST files. I haven't read docs on all it does, but I've observed one thing:
# - doctest will try to run each '>>>' in the reST file, and if the next line shows
#   what the OUTPUT should be, doctest verifies it.
# - BWARE: doctest doesn't print the most intuitive error message when a '>>>' line
#   blows up. It'll print something like this:
#     doctest.UnexpectedException <DocTest ... {{ FILENAME.rst }}:0 (1 example)>
#   basically telling you how many '>>>' failed ("1 example"), but not which
#   line(s). (Also, if you haven't used doctest recently, you might have no
#   clue this error has anything to do with '>>>' lines, because doctest does
#   not say that. And it also uses "UnexpectedException" which doesn't really
#   make it seem like something you can fix by "repairing" the reST file. But
#   I suppose that's what you get if you skip docs and go straight to some
#   code you just forked, you're bound to be baffled by some things that
#   might later seem obvious (at least to those who read the docs first).)

def test_docs():
    suite.debug()
