#!/usr/bin/env python
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

import TestSCons

test = TestSCons.TestSCons()

test.subdir('foo')
test.subdir('bar')
test.subdir(['bar', 'baz'])

test.write('testfile1', 'test 1\n')
test.write(['foo', 'testfile2'], 'test 2\n')
test.write(['bar', 'testfile1'], 'test 3\n')
test.write(['bar', 'baz', 'testfile2'], 'test 4\n')

test.write('SConstruct', """
file1 = FindFile('testfile1', [ 'foo', '.', 'bar', 'bar/baz' ])
print open(str(file1), 'r').read()
file2 = FindFile('testfile1', [ 'bar', 'foo', '.', 'bar/baz' ])
print open(str(file2), 'r').read()
file3 = FindFile('testfile2', [ 'foo', '.', 'bar', 'bar/baz' ])
print open(str(file3), 'r').read()
file4 = FindFile('testfile2', [ 'bar/baz', 'foo', '.', 'bar' ])
print open(str(file4), 'r').read()
""")

expect = test.wrap_stdout(read_str = """test 1

test 3

test 2

test 4

""", build_str = 'scons: "." is up to date.\n')

test.run(arguments = ".", stdout = expect)

test.pass_test()

