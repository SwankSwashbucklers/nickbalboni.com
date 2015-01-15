from bottle import run, route, request
from bottle import static_file, template
import argparse

# Command Line Interface
parser = argparse.ArgumentParser(description='Run server for nickbalboni.com')
parser.add_argument("-d", "--deploy", help="Run server for deployment", action="store_true")
parser.add_argument("-l", "--local", help="Run server for development testing on a local network")
args = parser.parse_args()


# Static Routes
# Svg image files and favicon pngs are exceptions and will have to follow the general path
@route('/static/<filepath:path>', method='GET')
def server_static(filepath):
	return static_file(filepath, root='static')

@route('/<filename:re:.*\.js>', method='GET')
def javascripts(filename):
    return static_file(filename, root='static/js')

@route('/<filename:re:.*\.css>', method='GET')
def stylesheets(filename):
    return static_file(filename, root='static/css')

@route('/<filename:re:.*\.ico>', method='GET')
def favicon(filename):
	return static_file(filename, root='static/favicon')

@route('/<filename:re:.*\.(jpg|png|gif)>', method='GET')
def images(filename):
    return static_file(filename, root='static/img')

@route('/<filename:re:.*\.(eot|ttf|woff|svg)>', method='GET')
def fonts(filename):
    return static_file(filename, root='static/fonts')


# Misc Resource Routes
@route('/robots.txt')
def robots():
	return static_file('robots.txt', root='static')

#@route('/google7a00f878cb0a19fa.html')
#def googleAuth():
#	return static_file('google7a00f878cb0a19fa.html', root='static')


# Main Site Routes
@route('/')
def load_home():
	return template('home')

#@route('/about')
#def load_about():
#	return template('about')

#@route('/contact')
#def load_contact():
#	return template('contact')

#@route('/test')
#def load_test():
#	return template('test')


# API Routes
@route('/', method='POST')
def api():
	if request.POST.get("v") == 'vendetta': 
		return u"Evey:\tWho are you?\n" + u"V:\tWho? Who is but the form following the function of what, and what\n\tI am is a man in a mask.\n" + u"Evey:\tWell I can see that.\n" + u"V:\tOf course you can. I'm not questioning your powers of observation;\n\tI'm merely remarking upon the paradox of asking a masked man who\n\the is.\n" + u"Evey:\tOh. Right.\n" + u"V:\tBut on this most auspicious of nights, permit me then, in lieu of\n\tthe more commonplace sobriquet, to suggest the character of this\n\tdramatis persona.\n" + u"V:\tVoila! In view, a humble vaudevillian veteran cast vicariously as\n\tboth victim and villain by the vicissitudes of Fate. This visage,\n\tno mere veneer of vanity, is a vestige of the vox populi, now\n\tvacant, vanished. However, this valourous visitation of a bygone\n\tvexation stands vivified and has vowed to vanquish these venal and\n\tvirulent vermin vanguarding vice and vouchsafing the violently\n\tvicious and voracious violation of volition! The only verdict is\n\tvengeance; a vendetta held as a votive, not in vain, for the value\n\tand veracity of such shall one day vindicate the vigilant and the\n\tvirtuous. Verily, this vichyssoise of verbiage veers most verbose,\n\tso let me simply add that it\'s my very good honour to meet you and\n\tyou may call me V.\n"
	if request.POST.get("purpose") == 'ping':
		return "Status OK [nb]"
	return load_home()



if args.deploy:
	run(host='127.0.0.1', port=8010, server='cherrypy') #deployment
elif args.local:
	run(host=args.local, port=8081, debug=True, reloader=True) #development
else:
	run(host='localhost', port=8081, debug=True, reloader=True) #development


