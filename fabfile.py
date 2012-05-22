# -*- coding: utf-8 -*-

from fabric.api import env, task, roles, run, sudo, cd
from fabric.context_managers import prefix
from fabric.contrib.files import append as file_append
from fabric.contrib.files import sed

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
    _install_code()

    with cd('/opt/djangoprojects/uriz/'):
        with prefix('workon uriz'):
	        run('python manage.py run_gunicorn')

    sudo('/etc/init.d/nginx restart')

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

def _install_code():
    sudo('mkdir -p /opt/djangoprojects/')
    with cd('/opt/djangoprojects/'):
        sudo('git clone https://github.com/ryanniemeyer/uriz.git')

    with cd('/opt/djangoprojects/uriz/'):
	    # Swap in our nginx conf
	    sudo('chmod 744 /opt/djangoprojects/uriz/config/nginx.conf')
        sudo('ln -s /opt/djangoprojects/uriz/config/nginx.conf /etc/nginx/nginx.conf')

        # Install all of our Python dependencies
        with prefix('workon uriz'):
	        run('pip install -r requirements.txt')
