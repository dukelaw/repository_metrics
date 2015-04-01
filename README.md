# Repository Metrics

## Configuration
Add some configuration files

### manifests/mysql.pp
Add a MySQL puppet configuration

    class { '::mysql::server':
      root_password    => {ROOT_PASSWORD}
      override_options => {
        'mysqld' => {
          'character-set-server' => 'utf8',
          'collation_server' => 'utf8_unicode_ci',
        }
      },
    }

    mysql::db { 'repository_metrics':
      user     => 'repository',
      password => {PASSWORD},
      host     => 'localhost',
      grant    => ['ALL']
    }


    class mysqlutils {
      package { 'libmysqlclient-dev':
        ensure => 'present',
      }
    }

    include '::mysql::server'
    include mysqlutils


### src/repository_metrics/repository-metrics.cfg

Create a configuration file for the application to access the database

    [sqlalchemy]
    dsn=mysql://repository:{PASSWORD}@localhost/repository_metrics?charset=utf8
    echo=False

## Loading Data

Put your editor and metadata files on a public server

WARNING: Will need to adjust script for other contexts

    python load.py {server}

Load downloads

    python load_downloads.py {filename}
