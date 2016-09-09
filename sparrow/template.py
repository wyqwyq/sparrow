# -*- coding: utf-8 -*-

from abc import ABCMeta, abstractmethod, abstractproperty
import re
from request import request
from response import response
from utilities import abort
from exceptions import HTTPError

class TemplateError(HTTPError):
    def __init__(self, message):
        HTTPError.__init__(self, 500, message)

class BaseTemplate(object, metaclass=ABCMeta):
    '''
    A base class for template. 
    '''

    def __init__(self, template='', filename=None):
        """
        Create a template object
        Template is a raw string of template, i.e., "<p> {{ variable_name }}
        </p>".
        Filename is a absolute path to a template file.
        Only one of two arguments should be filled, otherwise raise error.
        """
        self.filename = filename
        self.template = template
        if not self.template and not self.filename:
            raise TemplateError('Template: miss necessary argument')
        elif self.template and self.filename:
            raise TemplateError('Template: 1 argument only, 2 provided')
        self.prepare()

    @abstractmethod
    def prepare(self):
        """
        prepare something like parsing template.
        """
        pass

    @abstractmethod
    def render(self, **args):
        """
        Render the template with the specified local variables and return an
        iterator of strings (bytes).
        """
        pass

class PyStmt(str):
    def __repr__(self):
        return 'str(' + self + ')'


class SimpleTemplate(BaseTemplate):
    re_python = re.compile(r'^\s*%\s*(?:(if|elif|else|try|except|finally|for|'
                            'while|with|def|class)|(include)|(end)|(.*))')
    re_inline = re.compile(r'\{\{(.*?)\}\}')
    dedent_keywords = ('elif', 'else', 'except', 'finally')

    def prepare(self):
        if self.template:
            code = self.translate(self.template)
            self.co = compile(code, '<string>', 'exec')
        else:
            with open(self.filename) as f:
                code = self.translate(f.read())
                self.co = compile(code, self.filename, 'exec')

    def translate(self, template):
        indent = 0
        strbuffer = []
        code = []
        self.includes = dict()

        def flush(allow_nobreak=False):
            if len(strbuffer):
                if allow_nobreak and strbuffer[-1].endswith("\\\\\n"):
                    strbuffer[-1]=strbuffer[-1][:-3]
                code.append(' ' * indent + "_stdout.append(%s)" % repr(''.join(strbuffer)))
                code.append((' ' * indent + '\n') * len(strbuffer)) # keep the same number of line
                del strbuffer[:]

        for line in template.splitlines(True):
            lineend = '\n' if not line.endswith('\n') else ''
            m = self.re_python.match(line)
            if m:
                flush(allow_nobreak=True)
                keyword, subtpl, end, statement = m.groups()
                if keyword:
                    if keyword in self.dedent_keywords:
                        indent -= 1
                    code.append(" " * indent + line[m.start(1):])
                    indent += 1
                elif subtpl:
                    tmp = line[m.end(2):].strip().split(None, 1)
                    if not tmp:
                        raise TemplateError("include missing file in '%s'" % line)
                    filename = tmp[0]
                    args = tmp[1:] and tmp[1] or ''
                    if filename not in self.includes:
                        self.includes[filename] = SimpleTemplate(filename)
                    code.append(' ' * indent + 
                                "_ = _includes[%s].execute(_stdout, %s)\n"
                                % (repr(filename), args))
                elif end:
                    indent -= 1
                    code.append(' ' * indent + '#' + line[m.start(3):] + lineend)
                elif statement:
                    code.append(' ' * indent + line[m.start(4):] + lineend)
            else:
                splits = self.re_inline.split(line) # text, (expr, text)*
                if len(splits) == 1:
                    strbuffer.append(line)
                else:
                    flush()
                    for i in range(1, len(splits), 2):
                        splits[i] = PyStmt(splits[i])
                    splits = [x for x in splits if bool(x)]
                    code.append(' ' * indent + "_stdout.extend(%s)\n" % repr(splits))
        flush()
        return ''.join(code)

    def execute(self, stdout, **args):
        args['_stdout'] = stdout
        args['_includes'] = self.includes
        eval(self.co, args)
        return args

    def render(self, **args):
        """ Render the template using keyword arguments as local variables. """
        stdout = []
        self.execute(stdout, **args)
        return stdout

TEMPLATES = {}

def template(tpl, **args):
    '''
    Get a rendered template as a string iterator.
    You can use a name, a filename or a template string as first parameter.
    '''
    if tpl not in TEMPLATES:
        if "\n" in tpl or "{" in tpl or "%" in tpl or '$' in tpl:
            TEMPLATES[tpl] = SimpleTemplate(template=tpl)
        elif '.' in tpl:
            TEMPLATES[tpl] = SimpleTemplate(filename=tpl)

    if not TEMPLATES[tpl]:
        abort(500, 'Template (%s) not found' % tpl)
    args['abort'] = abort
    args['request'] = request
    args['response'] = response
    return TEMPLATES[tpl].render(**args)


