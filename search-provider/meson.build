service_dir = join_paths(get_option('datadir'), 'dbus-1', 'services')
serarch_provider_dir = join_paths(get_option('datadir'), 'gnome-shell', 'search-providers')


configure_file(
  input: 'scarlatti-sp.in',
  output: 'scarlatti-sp',
  configuration: conf,
  install_dir: LIBEXEC_DIR
)
configure_file(
  input: project_id + '.SearchProvider.service.in',
  output: project_id + '.SearchProvider.service',
  configuration: conf,
  install_dir: service_dir
)
install_data(
  'org.scarlatti.Scarlatti.SearchProvider.ini',
  install_dir: serarch_provider_dir
)
