project('lollypop',
  version: '1.2.19',
  meson_version: '>= 0.40.0'
)
i18n = import('i18n')
python = import('python3')
project_id = 'org.gnome.Lollypop'

message('Looking for dependencies')
python_bin = python.find_python()
if not python_bin.found()
    error('No valid python3 binary found')
else
    message('Found python3 binary')
endif

# Dependencies
dependency('gobject-introspection-1.0', version: '>= 1.35.0')
dependency('gtk+-3.0', version: '>= 3.22')
dependency('libsoup-2.4')
dependency('glib-2.0')
dependency('pygobject-3.0', version: '>= 3.29.1')

python_dir = join_paths(get_option('prefix'), python.sysconfig_path('purelib'))
LIBEXEC_DIR = join_paths(get_option('prefix'), get_option('libexecdir'))
DATA_DIR = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
bindir = join_paths(get_option('prefix'), get_option('bindir'))

conf = configuration_data()
conf.set('PACKAGE_URL', 'https://wiki.gnome.org/Apps/Lollypop')
conf.set('DATA_DIR', DATA_DIR)
conf.set('LOCALE_DIR', join_paths(get_option('prefix'), get_option('datadir'), 'locale'))
conf.set('PYTHON_DIR', python_dir)
#conf.set('PYTHON_EXEC_DIR', join_paths(get_option('prefix'), python.sysconfig_path('stdlib')))
conf.set('libexecdir', LIBEXEC_DIR)
conf.set('VERSION', meson.project_version())
conf.set('PYTHON', python_bin.path())

subdir('data')
subproject('po')
subdir('search-provider')

install_subdir(
  'lollypop',
  install_dir: python_dir
)

#install_subdir(
#  'thirdparty',
#  install_dir: join_paths(python_dir, 'lollypop')
#)

message('Preparing init file')
configure_file(
  input: 'lollypop.in',
  output: 'lollypop',
  configuration: conf,
  install_dir: bindir
)

meson.add_install_script('meson_post_install.py')
