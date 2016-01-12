shotvibe-web
============

ShotVibe REST API webservice

## Development on Mac OS X 10.8.5

Instructions from: https://gist.github.com/thesharp/3179227

Install python and virtualenv:

    $ brew install libgeoip
    $ curl -kL http://xrl.us/pythonbrewinstall | bash
    $ echo '[[ -s $HOME/.pythonbrew/etc/bashrc ]] && source' >> ~/.bashrc
    $ source ~/.bashrc
    $ pythonbrew install 2.7.9
    $ pythonbrew switch 2.7.9
    $ pip install virtualenv

Prepare a working environment in shotvibe-web:

    $ cd shotvibe-web
    $ virtualenv --system-site-packages .venv
    $ . .venv/bin/activate
    $ pip install -r requirements.txt
    $ pip install pillow
    $ pip install geoip
    $ cp local_settings.py.example local_settings.py
    $ deactivate

Edit `local_settings.py`, make sure to change to `Debug = True`

Verify everything:

    $ cd shotvibe-web
    $ . .venv/bin/activate
    $ python manage.py test
    ...
    $ deactivate

Create new Development Database:

    $ cd shotvibe-web
    $ . .venv/bin/activate
    $ python manage.py syncdb --migrate
    $ python manage.py createsuperuser
    Id: 1
    Nickname: supersue
    Password: password
    Password (again): password
    Superuser created succesfully.
    $ python manage.py shell
    >>> from phone_auth.models import User
    >>> User.objects.get(nickname='supersue').id
    392677102
    >>> exit()
    $ python manage.py runserver

Now you can login to the admin panel with your web browser at the URL:

    http://localhost:8000/admin/

    Id: 392677102
    Password: password

Once inside, you can add an email address for your superuser, and then next
time use the email address as the Id for the login.

## Deploying to Production

    $ git clone git@github.com:shotvibe/shotvibe-web.git
    $ git clone git@github.com:shotvibe/shotvibe-puppet.git
    $ cd shotvibe-web
    $ ../shotvibe-puppet/modules/shotvibe_web/scripts/remote_deploy.sh shotvibe.com
