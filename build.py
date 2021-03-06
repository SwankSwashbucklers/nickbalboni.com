'''
'''


################################################################################
##### Command Line Interface ###################################################
################################################################################

from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from tempfile import gettempdir
import os

parser = ArgumentParser(
    formatter_class=ArgumentDefaultsHelpFormatter,
    description=__doc__ )
parser.add_argument("-p", "--path",
    type=str,
    help="the path to the desired location of the generated site")
parser.add_argument("-d", "--deploy",
    action="store_true",
    help="package site for movement to deployment server. Default path is the"
    "current working directory, but the path flag will override that value" )
parser.add_argument("-r", "--reuse",
    action="store_true",
    help="if an already built website exists at the targeted path, attempt to"
    "reuse already present resources (i.e. images, favicon elements and other"
    "static resources)" )
args = parser.parse_args()

if args.path is None:
    args.path = os.getcwd()
    # if args.deploy:
    #     args.path = os.getcwd()
    # else:
    #     args.path = gettempdir()



################################################################################
##### Overrides ################################################################
################################################################################

from string import Template
from re import compile

class TemplateWrapper():

    def __init__(self, cls):
        PYTHON_LL = 80
        HTML_LL   = 112

        self.cls = cls
        self.headers = [
            (   # Primary python file header template
                compile(r'\$ph{(.*?)}'),
                lambda x: "\n\n{1}\n##### {0} {2}\n{1}\n".format(
                    x.upper(), '#'*PYTHON_LL, '#'*(PYTHON_LL-len(x)-7) )
            ),
            (   # Secondary python file header template
                compile(r'\$sh{(.*?)}'),
                lambda x: "\n### {0} {1}".format(
                    x, '#'*(PYTHON_LL-len(x)-5) )
            ),
            (   # HTML file header template
                compile(r'\$wh{(.*?)}'),
                lambda x: "<!-- ***** {0} {1} -->".format(
                    x, '*'*(HTML_LL-len(x)-16) )
            )
        ]

    def __call__(self, template):
        for header in self.headers:
            ptn, tpl = header
            for match in ptn.finditer(template):
                replacements = ( match.group(0), tpl(match.group(1)) )
                template = template.replace(*replacements)
        template_obj = self.cls(template)
        template_obj.populate = self.populate
        return template_obj

    @staticmethod
    def populate(template, filepath, **kwargs):
        for key, value in kwargs.items():
            if isinstance(value, list):
                kwargs[key] = "\n".join(
                    [ t[0].safe_substitute(**t[1]) for t in value ]
                )
        try:
            with open(filepath, 'w') as f:
                f.write(template.safe_substitute(**kwargs))
        except Exception as exception:
            raise exception

Template = TemplateWrapper(Template)


from subprocess import Popen, call, DEVNULL, STDOUT, PIPE
from sys import executable

def sPopen(*args):
    command, shell = list(args), True
    if command[0] == 'python':
        command[0] = executable
        shell = False
    if os.name == 'nt':
        from subprocess import CREATE_NEW_CONSOLE
        return Popen( command, shell=shell, creationflags=CREATE_NEW_CONSOLE )
    else:
        return Popen( command, shell=shell )

def sCall(*args):
    command, shell = list(args), True
    if command[0] == 'python':
        command[0] = executable
        shell = False
    if os.name != 'nt':
        shell = False
    call( command, shell=shell, stdout=DEVNULL, stderr=STDOUT )



################################################################################
##### Templates ################################################################
################################################################################

APP_PY_TEMPLATE = Template("""\
\"""
${doc_string}
\"""
from bottle import run, route, get, post, error
from bottle import static_file, template, request
from bottle import HTTPError

$ph{Command Line Interface}
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
from inspect import getframeinfo, currentframe
from os.path import dirname, abspath
import os

parser = ArgumentParser(
    formatter_class=ArgumentDefaultsHelpFormatter,
    description=__doc__ )
parser.add_argument('-d', '--deploy',
    action='store_true',
    help='Run server for deployment' )
parser.add_argument('-i', '--ip',
    type=str,
    default="127.0.0.1",
    help='ip to run the server against, default localhost' )
parser.add_argument('-p', '--port',
    type=str,
    default="8080",
    help='port to run server on' )
args = parser.parse_args()

# change working directory to script directory
os.chdir(dirname(abspath(getframeinfo(currentframe()).filename)))

$ph{Main Site Routes}
${main_routes}
$ph{API and Additional Site Routes}
${api_routes}

$ph{Static Routes}
${static_routes}
$sh{Favicon Routes}
${favicon_routes}
$sh{Image Routes}
${image_routes}
$sh{Font Routes}
${font_routes}
$sh{Stylesheet Routes}
${css_routes}
$sh{Javascript Routes}
${js_routes}
$ph{Error Routes}
@error(404)
def error404(error):
    return 'nothing to see here'

$ph{Run Server}
if args.deploy:
    run(host=args.ip, port=args.port, server='cherrypy') #deployment
else:
    run(host=args.ip, port=args.port, debug=True, reloader=True) #development
""" )


MAIN_ROUTE_TEMPLATE = Template("""\
@route('/${path}')
def ${method_name}():
    return template('${template}', request=request, template='${template}')
""" )


STATIC_ROUTE_TEMPLATE = Template("""\
@get('/${path}')
def load_resource():
    return static_file('${file}', root='${root}')
""" )


WATCH_SASS_SCRIPT = Template("""\
from sys import argv, exit
from signal import signal, SIGTERM, SIGINT
from shutil import rmtree
from subprocess import Popen
from inspect import getframeinfo, currentframe
from os.path import dirname, abspath, isdir, isfile
from os import chdir, remove

def signal_term_handler(signal, frame):
    if not p is None: p.kill()
    if isfile("_all.scss"): remove("_all.scss")
    if isdir(".sass-cache"): rmtree(".sass-cache")
    print(argv[0])
    remove("watch.py") # argv[0] contains full path
    exit(0)

p = None
signal(SIGTERM, signal_term_handler)
signal(SIGINT, signal_term_handler)
chdir(dirname(abspath(getframeinfo(currentframe()).filename)))

command = "sass --watch"
for x in range(1, len(argv)):
    command += " {0}.scss:../../www/static/css/{0}.css".format(argv[x])
p = Popen(command, shell=True)
p.wait()
""" )



################################################################################
##### Script Body ##############################################################
################################################################################

from os.path import relpath, abspath, normpath, join, isfile, isdir, splitext
from shutil import copy, copyfileobj, rmtree
from urllib.request import urlopen
from time import sleep
from re import match, search
from sys import exit

SCRIPT_DIR   = os.getcwd()
PROJECT_NAME = relpath(SCRIPT_DIR, "..")
STATIC_ROUTE = lambda p, f, r: \
    ( STATIC_ROUTE_TEMPLATE, { "path": p, "file": f, "root": r } )
MAIN_ROUTE   = lambda p, m, t: \
    ( MAIN_ROUTE_TEMPLATE, { "path": p, "method_name": m, "template": t } )


def migrate_files(directory, destination):
    src_path = join(SCRIPT_DIR, directory)
    if not isdir(destination): os.makedirs(destination)
    for root, dirs, files in os.walk(src_path):
        for dirname in dirs:
            if dirname.startswith('!') or dirname in ['.DS_STORE']:
                dirs.remove(dirname)
        for filename in files:
            if not filename.startswith('!') and filename not in ['.DS_Store']:
                if not isfile(filename): #added for the reuse flag
                    copy(join(root, filename), join(destination, filename))
                if not filename.startswith('~'):
                    yield normpath(join(relpath(root, src_path),
                                        filename) ).replace('\\', '/')


def migrate_views():
    routes = [ MAIN_ROUTE("", "load_root", "index") ]
    for route in migrate_files("dev/views", "views"):
        tpl_name = splitext(route.split("/")[-1])[0]
        if tpl_name == "index":
            continue
        routes.append(MAIN_ROUTE(
            splitext(route)[0],
            "load_" + tpl_name.replace("-","_"),
            tpl_name
        ))
    return routes


def get_api_routes():
    with open( join(SCRIPT_DIR, "dev/py", "routes.py"), 'r') as f:
        return f.read()


def migrate_static_files(source, destination):
    return [ STATIC_ROUTE(r, r.split("/")[-1], destination)
                for r in migrate_files(source, destination) ]


def generate_favicon_resources():
    fav_tpl     = lambda r: "favicon-{0}x{0}.png".format(r)
    and_tpl     = lambda r: "touch-icon-{0}x{0}.png".format(r)
    app_tpl     = lambda r: "apple-touch-icon-{0}x{0}.png".format(r)
    pra_tpl     = lambda r: "apple-touch-icon-{0}x{0}-precomposed.png".format(r)
    fav_path    = lambda p: normpath(join("static/favicon", p))
    favicon_tpl = normpath(join(SCRIPT_DIR, "res/favicon.svg"))
    ico_res     = [ "16", "24", "32", "48", "64", "128", "256" ]
    fav_res     = [ "16", "32", "96", "160", "196", "300" ]
    android_res = [ "192" ]
    apple_res   = [ "57", "76", "120", "152", "180" ] # add to head backwards
    if not isdir("static/favicon"): os.makedirs("static/favicon")
    # generate favicon resources
    for res in (list(set(ico_res) | set(fav_res)) + android_res + apple_res):
        if res in android_res: path = abspath( fav_path(and_tpl(res)) )
        elif res in apple_res: path = abspath( fav_path(app_tpl(res)) )
        else:                  path = abspath( fav_path(fav_tpl(res)) )
        sCall("inkscape", "-z", "-e", path, "-w", res, "-h", res, favicon_tpl)
    sCall( *(["convert"] + [fav_path(fav_tpl(r)) for r in ico_res] +
             [fav_path("favicon.ico")]) )
    for res in [ r for r in ico_res if r not in fav_res ]:
        os.remove(fav_path(fav_tpl(res)))
    # return routes for generated favicon resources
    fav_route = lambda f:   STATIC_ROUTE(f, f, "static/favicon")
    app_route = lambda p,t: STATIC_ROUTE(p, t("57"), "static/favicon")
    return ([ fav_route("favicon.ico") ] +
            [ fav_route(fav_tpl(r)) for r in fav_res ] +
            [ fav_route(and_tpl(r)) for r in android_res ] +
            [ fav_route(app_tpl(r)) for r in apple_res if r!="57" ] +
            [ fav_route(pra_tpl(r)) for r in apple_res if r!="57" ] +
            [ app_route("apple-touch-icon.png", app_tpl),
              app_route("apple-touch-icon-precomposed.png", pra_tpl) ])


def generate_stylesheets():
    dev_path   = join( SCRIPT_DIR, "dev/sass" )
    is_sass    = lambda f: splitext(f)[-1].lower() in ['.scss', '.sass']
    is_mixin   = lambda f: match(r'.*mixins?$', splitext(f)[0].lower())
    get_import = lambda p: [ join( relpath(r, dev_path), f )
                             for r, d, fs in os.walk( join(dev_path, p) )
                             for f in fs if is_sass(f) ]
    if not isdir("static/css"): os.makedirs("static/css")
    # generate _all.scss file from existing sass resources
    with open( join( dev_path, '_all.scss' ), 'w') as f:
        f.write('\n'.join( # probably not the most efficient way
            [ '@import "{}";'.format(path.replace('\\', '/')) for path in
                ( # mixins and global variables must be imported first
                    # modules
                    [ f for f in get_import('modules') ]
                    # vendor mixins
                  + [ f for f in get_import('vendor') if is_mixin(f) ]
                    # all other vendor files
                  + [ f for f in get_import('vendor') if not is_mixin(f) ]
                    # partials (comment out this line for manually selection)
                  + [ f for f in get_import('partials') ]
                )
            ] )
        )
    # use sass command line tool to generate stylesheets
    stylesheets = [ splitext(f)[0] for f in os.listdir(dev_path)
                    if is_sass(f) and not f.startswith('_') ]
    sass_path = relpath(dev_path, os.getcwd()).replace('\\', '/')
    if args.deploy:
        for s in stylesheets:
            sCall("sass", sass_path+"/"+s+".scss", "static/css/"+s+".min.css",
                    "-t", "compressed", "--sourcemap=none", "-C")
        os.remove( join(dev_path, "_all.scss") )
    else:
        Template.populate(WATCH_SASS_SCRIPT, '../dev/sass/watch.py')
        command = "sass --watch"
        for s in stylesheets:
            command += " ../dev/sass/{0}.scss:./static/css/{0}.css".format(s)
        p = Popen(command, shell=True)
        #p = sPopen( 'python', '../dev/sass/watch.py', *stylesheets )
        sleep(3) # delay so the stylesheets have time to be created
        p.kill() # note: kill sends SIGKILL
    # return css routes from generated stylesheets
    return [ STATIC_ROUTE(f, f, "static/css") for f in os.listdir("static/css")]


def generate_javascript():
    return migrate_static_files("dev/js", "static/js")


def get_favicon_head():
    link_tpl     = lambda c: '    <link {0}>\n'.format(c)
    all_favs     = os.listdir('static/favicon')
    favicons     = [ x for x in all_favs if x.startswith('favicon') ]
    apple_favs   = [ x for x in all_favs if x.startswith('apple')   ]
    android_favs = [ x for x in all_favs if not x in favicons + apple_favs ]
    fav_head = link_tpl('rel="shortcut icon" href="favicon.ico"')
    favicons.remove('favicon.ico')
    def gen_head(fav_tpl, fav_set):
        dic = {}
        for fav in fav_set:
            res = int(search(r'([0-9]+)x', fav).group(1))
            dic[res] = fav
        keys = list(dic.keys())
        keys.sort()
        keys.reverse()
        for key in keys:
            yield link_tpl( fav_tpl.format(key, dic[key]) )
    for fav_set in [
        ('rel="icon" sizes="{0}x{0}" href="/{1}"', android_favs),
        ('rel="apple-touch-icon" sizes="{0}x{0}" href="/{1}"', apple_favs),
        ('rel="icon" type="image/png" sizes="{0}x{0}" href="/{1}"', favicons) ]:
        fav_head += "".join( gen_head(*fav_set) )
    return fav_head


def get_opengraph_head():
    og_head_string = """\
    % url = request.environ['HTTP_HOST']
    <meta property="og:url" content="http://{{url}}/">
    <meta property="og:type" content="website">
    <meta property="og:title" content="{{title}}">
    <meta property="open_graph_image">
    <meta property="og:description" content="{{description}}">"""
    og_image_string = """<meta property="og:image:type" content="image/png">
    <meta property="og:image:width" content="300">
    <meta property="og:image:height" content="300">
    <meta property="og:image:url" content="http://{{url}}/favicon-300x300.png">
    <meta property="og:image" content="http://{{url}}/favicon-300x300.png">"""
    if isfile("static/favicon/favicon-300x300.png"):
        og_head_string = og_head_string.replace(
            '<meta property="open_graph_image">',
            og_image_string
        )
    return og_head_string


def get_stylesheet_head():
    styles_tpl  = '    <link rel="stylesheet" type="text/css" href="/{0}">\n'
    stylesheets = os.listdir('static/css')
    styles_head = ''
    for style in stylesheets:
        if style.split('.')[0] == 'styles':
            styles_head += styles_tpl.format(style)
            stylesheets.remove(style)
            break
    stylesheets = [ s.split('.')[0] for s in stylesheets ]
    styles_head += "    % if template in {}:\n".format(stylesheets)
    tpl_style = '{{template}}.min.css' if args.deploy else '{{template}}.css'
    styles_head += styles_tpl.format(tpl_style)
    styles_head += "    % end"
    return styles_head


os.chdir(args.path)
if isdir("www"): rmtree("www")
os.makedirs("www")
os.chdir("www")

### Import Bottle Framework ####################################################
from urllib.error import URLError

bottle_url = "https://raw.githubusercontent.com/bottlepy/bottle/master/bottle.py"
try:
    with urlopen(bottle_url) as response, open('bottle.py', 'wb') as f:
        copyfileobj(response, f)
except URLError as e:
    print(e)

# try:
#     with open('/Users/Nick/Desktop/bottle.py', 'r') as tpl, open('bottle.py', 'w') as f:
#         f.write(tpl.read())
# except Exception as e:
#     print(e)

### Generate App.py ############################################################
Template.populate(APP_PY_TEMPLATE, 'app.py',
    doc_string="",
    main_routes=migrate_views(),
    api_routes=get_api_routes(),
    static_routes=migrate_static_files("res/static", "static"),
    favicon_routes=generate_favicon_resources(),
    image_routes=migrate_static_files("res/img", "static/img"),
    font_routes=migrate_static_files("res/font", "static/font"),
    css_routes=generate_stylesheets(),
    js_routes=generate_javascript() )

### Generate Head Template #####################################################
if isfile('views/~head.tpl'): os.remove('views/~head.tpl')
head_tpl = ""
with open(join(SCRIPT_DIR, "dev/views/~head.tpl"), 'r') as head:
    head_tpl = head.read()
metas = [ "Favicon_Resources", "Open_Graph", "Style_Sheets" ]
for meta in metas:
    head_tpl = head_tpl.replace(
        '<meta name="'+meta.lower()+'">',
        '\n$wh{'+meta.replace('_', ' ')+'}\n${'+meta.lower()+'}'
    )
Template.populate(Template(head_tpl), 'views/~head.tpl',
    favicon_resources=get_favicon_head(),
    open_graph=get_opengraph_head(),
    style_sheets=get_stylesheet_head() )

### Packaging For Deployment ###################################################
if not args.deploy:
    #sCall('python', 'app.py', '-p', '8081')
    exit(0)

from zipfile import ZipFile
os.chdir('..') # work on this
if isfile('www.zip'): os.remove('www.zip')
with ZipFile('www.zip', 'w') as zip_file:
    for root, dirs, files in os.walk( join(os.getcwd(), 'www') ):
        rel_path = relpath(root, os.getcwd())
        for f in files:
            zip_file.write( join(rel_path, f) )

# set up watch for template and js files using watchdog
