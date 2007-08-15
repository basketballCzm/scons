#
# __COPYRIGHT__
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY
# KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#

__revision__ = "__FILE__ __REVISION__ __DATE__ __DEVELOPER__"

__doc__ = """
CacheDir support
"""

import os.path
import stat
import string
import sys

import SCons.Action

cache_debug = False
cache_force = False
cache_show = False

def CacheRetrieveFunc(target, source, env):
    t = target[0]
    fs = t.fs
    cp = fs.CachePath
    cachedir, cachefile = cp.cachepath(t)
    if not fs.exists(cachefile):
        cp.CacheDebug('CacheRetrieve(%s):  %s not in cache\n', t, cachefile)
        return 1
    cp.CacheDebug('CacheRetrieve(%s):  retrieving from %s\n', t, cachefile)
    if SCons.Action.execute_actions:
        if fs.islink(cachefile):
            fs.symlink(fs.readlink(cachefile), t.path)
        else:
            fs.copy2(cachefile, t.path)
        st = fs.stat(cachefile)
        fs.chmod(t.path, stat.S_IMODE(st[stat.ST_MODE]) | stat.S_IWRITE)
    return 0

def CacheRetrieveString(target, source, env):
    t = target[0]
    fs = t.fs
    cp = fs.CachePath
    cachedir, cachefile = cp.cachepath(t)
    if t.fs.exists(cachefile):
        return "Retrieved `%s' from cache" % t.path
    return None

CacheRetrieve = SCons.Action.Action(CacheRetrieveFunc, CacheRetrieveString)

CacheRetrieveSilent = SCons.Action.Action(CacheRetrieveFunc, None)

def CachePushFunc(target, source, env):
    t = target[0]
    if t.nocache:
        return
    fs = t.fs
    cp = fs.CachePath
    cachedir, cachefile = cp.cachepath(t)
    if fs.exists(cachefile):
        # Don't bother copying it if it's already there.  Note that
        # usually this "shouldn't happen" because if the file already
        # existed in cache, we'd have retrieved the file from there,
        # not built it.  This can happen, though, in a race, if some
        # other person running the same build pushes their copy to
        # the cache after we decide we need to build it but before our
        # build completes.
        cp.CacheDebug('CachePush(%s):  %s already exists in cache\n', t, cachefile)
        return

    cp.CacheDebug('CachePush(%s):  pushing to %s\n', t, cachefile)

    if not fs.isdir(cachedir):
        fs.makedirs(cachedir)

    tempfile = cachefile+'.tmp'
    try:
        if fs.islink(t.path):
            fs.symlink(fs.readlink(t.path), tempfile)
        else:
            fs.copy2(t.path, tempfile)
        fs.rename(tempfile, cachefile)
        st = fs.stat(t.path)
        fs.chmod(cachefile, stat.S_IMODE(st[stat.ST_MODE]) | stat.S_IWRITE)
    except (IOError, OSError):
        # It's possible someone else tried writing the file at the
        # same time we did, or else that there was some problem like
        # the CacheDir being on a separate file system that's full.
        # In any case, inability to push a file to cache doesn't affect
        # the correctness of the build, so just print a warning.
        SCons.Warnings.warn(SCons.Warnings.CacheWriteErrorWarning,
                            "Unable to copy %s to cache. Cache file is %s"
                                % (str(target), cachefile))

CachePush = SCons.Action.Action(CachePushFunc, None)

class CacheDir:

    def __init__(self, path):
        try:
            import SCons.Sig.MD5
        except ImportError:
            msg = "No MD5 module available, CacheDir() not supported"
            SCons.Warnings.warn(SCons.Warnings.NoMD5ModuleWarning, msg)
        else:
            self.path = path

    def CacheDebugWrite(self, fmt, target, cachefile):
        self.debugFP.write(fmt % (target, os.path.split(cachefile)[1]))

    def CacheDebugQuiet(self, fmt, target, cachefile):
        pass

    def CacheDebugInit(self, fmt, target, cachefile):
        #if self.cache_debug:
        if cache_debug:
            if cache_debug == '-':
                self.debugFP = sys.stdout
            else:
                self.debugFP = open(cache_debug, 'w')
            self.CacheDebug = self.CacheDebugWrite
            self.CacheDebug(fmt, target, cachefile)
        else:
            self.CacheDebug = self.CacheDebugQuiet

    CacheDebug = CacheDebugInit

    def cachepath(self, node):
        """
        """
        sig = node.get_cachedir_bsig()
        subdir = string.upper(sig[0])
        dir = os.path.join(self.path, subdir)
        return dir, os.path.join(dir, sig)

    def retrieve(self, node):
        """
        This method is called from multiple threads in a parallel build,
        so only do thread safe stuff here. Do thread unsafe stuff in
        built().

        Note that there's a special trick here with the execute flag
        (one that's not normally done for other actions).  Basically
        if the user requested a no_exec (-n) build, then
        SCons.Action.execute_actions is set to 0 and when any action
        is called, it does its showing but then just returns zero
        instead of actually calling the action execution operation.
        The problem for caching is that if the file does NOT exist in
        cache then the CacheRetrieveString won't return anything to
        show for the task, but the Action.__call__ won't call
        CacheRetrieveFunc; instead it just returns zero, which makes
        the code below think that the file *was* successfully
        retrieved from the cache, therefore it doesn't do any
        subsequent building.  However, the CacheRetrieveString didn't
        print anything because it didn't actually exist in the cache,
        and no more build actions will be performed, so the user just
        sees nothing.  The fix is to tell Action.__call__ to always
        execute the CacheRetrieveFunc and then have the latter
        explicitly check SCons.Action.execute_actions itself.
        """
        retrieved = False

        #if self.cache_show:
        if cache_show:
            if CacheRetrieveSilent(node, [], None, execute=1) == 0:
                node.build(presub=0, execute=0)
                retrieved = 1
        else:
            if CacheRetrieve(node, [], None, execute=1) == 0:
                retrieved = 1
        if retrieved:
            # Record build signature information, but don't
            # push it out to cache.  (We just got it from there!)
            node.set_state(SCons.Node.executed)
            SCons.Node.Node.built(node)

        return retrieved

    def push(self, node):
        return CachePush(node, [], None)

    def push_if_forced(self, node):
        #if self.cache_force:
        if cache_force:
            return self.push(node)
