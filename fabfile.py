# -*- coding: utf-8 -*-

from fabric.api import env, task, roles, run, sudo, cd
from fabric.context_managers import prefix
from fabric.contrib.files import append as file_append
from fabric.contrib.files import sed

from uriz.my_aws_settings import AWS_ACCESS_KEY_ID
from uriz.my_aws_settings import AWS_SECRET_ACCESS_KEY

env.user = 'ubuntu'

# The location of your ec2 key pair. You can find this in the
# AWS management console in the EC2 section. Under
# Network & Security there's a link to Key Pairs.
env.key_filename = '/ec2/accounts/uriz/uriz.pem'

@task
def newbox():
    """Installs uriz on a new web EC2 instance.

    First, start up a new small EC2 instance in
    us-east using ami-3c994355 (Ubuntu 12.04 64-bit).
 
    Then, run this command specifying the EC2 host(s)::

        fab -H ec2host1,ec2host2 newbox

    """
    _update_OS()
    _install_build_essentials()
    _install_git()
    _install_python_schtuff()
    _install_nginx()
    _install_apache2()
    _install_code()
    apache_restart()
    nginx_restart()

def apache_start():
    sudo('/etc/init.d/apache2 start')

def apache_restart():
    sudo('/etc/init.d/apache2 restart')

def apache_stop():
    sudo('/etc/init.d/apache2 stop')

def nginx_restart():
    sudo('/etc/init.d/nginx restart')

def nginx_reload():
    sudo('/etc/init.d/nginx reload')

def nginx_stop():
    sudo('/etc/init.d/nginx stop')

def _update_OS():
    sudo('apt-get -y -q update')
    sudo('apt-get -y -q upgrade --show-upgraded')

def _install_build_essentials():
    sudo('apt-get -y -q install build-essential')
    sudo('gcc -v')
    sudo('make -v')

def _install_git():
    sudo('apt-get -y -q install git-core')

def _install_python_schtuff():
    # Get easy_install and pip
    sudo('apt-get -y -q install python-setuptools')
    sudo('easy_install pip')
    
    # Setup the uriz virtualenv...
    sudo('pip install virtualenv')
    sudo('pip install virtualenvwrapper')

    with cd('~'):
        run('mkdir .virtualenvs')
        file_append('.bash_profile',
                    ['# virtualenvwrapper',
                     'export WORKON_HOME=~/.virtualenvs',
                     'source /usr/local/bin/virtualenvwrapper.sh',
                     'export PIP_VIRTUALENV_BASE=$WORKON_HOME',
                     'export PIP_RESPECT_VIRTUALENV=true'],
                    use_sudo=False, partial=False, escape=True)
        run('source ~/.bash_profile')
        run('mkvirtualenv uriz')

def _install_nginx():
    sudo('apt-get -y -q install nginx')

    # Create log directories
    sudo('mkdir -p /var/log/nginx')
    sudo('chmod +x /var/log/nginx')

    # create the user the nginx process will use
    sudo('adduser --system --no-create-home --disabled-login --disabled-password --group nginx')

    # Remove default Ubuntu nginx conf, we'll replace it with our nginx conf
    sudo('rm /etc/nginx/nginx.conf')

def _install_apache2():
    # Installs to /etc/apache2
    sudo('apt-get -y -q install apache2')
    sudo('apt-get -y -q install libapache2-mod-wsgi')

    # Remove default Ubuntu apache cruft, we'll replace it with our apache conf
    with cd('/etc/apache2/'):
        sudo('rm -rf apache2.conf conf.d/ httpd.conf magic mods-* sites-* ports.conf')

def _install_code():
    sudo('mkdir -p /opt/djangoprojects/')
    with cd('/opt/djangoprojects/'):
        sudo('git clone https://github.com/ryanniemeyer/uriz.git')

    with cd('/opt/djangoprojects/uriz/'):
        # Swap in our nginx conf
        sudo('chmod 744 /opt/djangoprojects/uriz/config/nginx.conf')
        sudo('ln -s /opt/djangoprojects/uriz/config/nginx.conf /etc/nginx/nginx.conf')

        # Swap in our apache conf
        sudo('chmod 744 /opt/djangoprojects/uriz/config/apache2.conf')
        sudo('ln -s /opt/djangoprojects/uriz/config/apache2.conf /etc/apache2/apache2.conf')

        # Install all of our Python dependencies
        with prefix('workon uriz'):
            run('pip install -r requirements.txt')

    # Add in the AWS key and secret that you should have in my_aws_settings.py locally,
    # but is not checked into github...
    with cd('/opt/djangoprojects/uriz/uriz/'):
        sudo('touch my_aws_settings.py')
        file_append('my_aws_settings.py',
                    ['AWS_ACCESS_KEY_ID = "{0}"'.format(AWS_ACCESS_KEY_ID),
                     'AWS_SECRET_ACCESS_KEY = "{0}"'.format(AWS_SECRET_ACCESS_KEY)],
                    use_sudo=True, partial=False, escape=True)
