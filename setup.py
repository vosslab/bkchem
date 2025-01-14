#!/usr/bin/env python



import os
import sys
import glob

from distutils.core import setup

from bkchem import config



## A few pre-setup hacks
if os.name != 'posix':
  sys.path.insert(0, 'bkchem')

# all the apicdoc directories and files
apidocs = [('share/doc/bkchem/'+path[4:], list(map(os.path.join, len(filenames)*[path], filenames)))
              for (path, dirnames, filenames) in os.walk('doc/api')]

# available languages to pack
langs = [l for l in os.listdir('locale')
               if (os.path.isdir('locale/' + l) and
                   os.path.exists('locale/' + l + '/LC_MESSAGES/BKChem.mo'))]

print("found languages:", langs)
localizations = [('share/locale/' + lang + '/LC_MESSAGES', ['locale/' + lang + '/LC_MESSAGES/BKChem.mo'])
                    for lang in langs]

# should we strip something from in the scripts from the installation path (used in gentoo sandboxing etc.)
strip = ""
for arg in sys.argv:
  if arg.startswith("--strip="):
    strip = arg.lstrip("--strip=")
    sys.argv.remove(arg)
    break

def strip_path(path):
  if path.startswith(strip):
    new = path.replace(strip, "", 1)
    return new
  else:
    return path


# the setup itself
conf = setup(
  name = 'bkchem',
  version = config.current_BKChem_version,
  description = "BKChem is a chemical drawing program written in Python",
  author = "Beda Kosata",
  author_email = "beda@zirael.org",
  maintainer = "Reinis Danne",
  maintainer_email = "rei4dan@gmail.com",
  url = "http://bkchem.zirael.org",
  license = "GNU GPL",
  platforms = ["Unix", "Windows", "hopefully other OSes able to run Python"],
  long_description = "BKChem is a chemical drawing program written in Python",

  packages = ['bkchem',
              'bkchem/plugins',
              'bkchem/plugins/piddle'],

  data_files = [('share/bkchem/templates', glob.glob('templates/*.cdml') + glob.glob('templates/*.xml')),
                ('share/bkchem/images', ['images/logo.ppm','images/icon.ico'] + glob.glob('images/bkchem*.png')),
                ('share/bkchem/pixmaps', glob.glob('pixmaps/*.gif')),
                ('share/bkchem/dtd', glob.glob('dtd/*.dtd') + glob.glob('dtd/*.xsd')),
                ('share/bkchem/plugins', glob.glob('plugins/*.py') + glob.glob('plugins/*.xml')),
                ('share/doc/bkchem', glob.glob('doc/*.xml') + glob.glob('doc/*.html') + ['README', 'INSTALL', 'progress.log']),
                #('share/doc/bkchem/pdf', glob.glob( 'doc/pdf/*')),
                ('share/doc/bkchem/html', glob.glob('doc/html/*')),
                ('share/doc/bkchem/scripts', glob.glob('doc/scripts/*')),
                ('share/doc/bkchem/img', glob.glob('doc/img/*')),
                ] + localizations + apidocs,
  )




if len( sys.argv) > 1 and sys.argv[1] == 'install' and '--help' not in sys.argv:
  data_dir = conf.command_obj['install'].install_data
  py_dir   = conf.command_obj['install'].install_lib
  bin_dir  = conf.command_obj['install'].install_scripts

  # the configuration file
  config_name = os.path.join(py_dir, 'bkchem/site_config.py')
  try:
    f = open(config_name, 'w')
  except IOError:
    print("ERROR: couldn't open the file %s for write" %  config_name)
    sys.exit()
  f.write("# the bkchem configuration file, do not edit!\n #(unless you are pretty sure that you know what you are doing, which even I am not)\n")
  f.write('BKCHEM_MODULE_PATH="%s"\n' % strip_path( os.path.join( py_dir, "bkchem")))
  f.write('BKCHEM_TEMPLATE_PATH="%s"\n' % strip_path( os.path.join( data_dir, "share/bkchem/templates")))
  f.write('BKCHEM_PIXMAP_PATH="%s"\n' % strip_path( os.path.join( data_dir, "share/bkchem/pixmaps")))
  f.write('BKCHEM_IMAGE_PATH="%s"\n' % strip_path( os.path.join( data_dir, "share/bkchem/images")))
  f.write('BKCHEM_PLUGIN_PATH="%s"\n' % strip_path( os.path.join( data_dir, "share/bkchem/plugins")))
  f.close()
  print("file %s created" % config_name)


  # the executable
  if not os.path.isdir(bin_dir):
    try:
      os.mkdir(bin_dir)
    except IOError:
      print("ERROR: could not create directory %s" % bin_dir)
      sys.exit( 201)
  exec_name = os.path.join(bin_dir, 'bkchem')
  try:
    f = open(exec_name, 'w')
  except IOError:
    print("ERROR: couldn't open the file %s for write" %  exec_name)
    sys.exit(201)
  f.write("#!/bin/sh\n")
  f.write('python %s "$@"\n' % strip_path(os.path.join(py_dir, "bkchem", "bkchem.py")))
  f.close()
  print("file %s created" % exec_name)
  try:
    os.chmod(os.path.join(bin_dir, 'bkchem'), 5+5*8+7*8*8)
  except IOError:
    print("ERROR: failed to make %s executable" % exec_name)
    sys.exit( 201)
  print("file %s made executable" % exec_name)

