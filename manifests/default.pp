import 'mysql.pp'
include concat::setup

exec { "apt-update":
    command => "/usr/bin/apt-get update"
}

Exec["apt-update"] -> Package <| |>

class mount {
  package { 'cifs-utils':
    ensure =>present
  }
}

class lxml {
  package { 'build-essential':
    ensure => 'present'
  } ->
  package { 'libxml2-dev':
    ensure => 'present'
  } ->
  package { 'libxslt1-dev':
    ensure => 'present'
  } ->
  package { 'libxml2-dbg':
    ensure => 'present'
  }
}

class editors {
  package { 'emacs':
    ensure => 'present',
  }
  package { 'vim':
    ensure => 'present',
  }
}

class { 'python':
  version    => 'system',
  pip        => true,
  dev        => true,
  virtualenv => true,
  gunicorn   => false,
}

class pythonenv {
  file { "/opt/virtualenvs":
    ensure => "directory",
  } ->
  python::virtualenv { '/opt/virtualenvs/repository_metrics':
    ensure       => present,
    version      => 'system',
    venv_dir     => '/opt/virtualenvs/repository_metrics',
  } ->
  python::requirements { '/vagrant/requirements.txt':
    virtualenv => '/opt/virtualenvs/repository_metrics',
    require => Python::Virtualenv['/opt/virtualenvs/repository_metrics']
  }
}

class { 'apache':
  default_vhost => false,
}

file { '/var/www/repository_metrics/':
  ensure => 'link',
  target => '/vagrant/src'
} ->
apache::vhost { 'repository-metrics':
  default_vhost               => true,
  docroot                     => '/var/www',
  vhost_name                  => '*',
  port                        => '80',
  wsgi_application_group      => '%{GLOBAL}',
  wsgi_daemon_process         => 'wsgi',
  wsgi_daemon_process_options => {
    processes    => '2',
    threads      => '5',
    display-name => '%{GROUP}',
   },
  wsgi_import_script          => '/var/www/repository_metrics/repository_metrics.wsgi',
  wsgi_import_script_options  => {
    process-group => 'wsgi',
    application-group => '%{GLOBAL}'
  },
  wsgi_process_group          => 'wsgi',
  wsgi_script_aliases         => {
    '/repository_metrics' => '/var/www/repository_metrics/repository_metrics.wsgi'
  }
}

include 'apache::mod::info'
include 'apache::mod::wsgi'
include 'apache::mod::status'
include stdlib
include python
include pythonenv
include editors
include lxml
include mount
