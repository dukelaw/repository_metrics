activate_this = '/opt/virtualenvs/repository_metrics/bin/activate_this.py'
execfile(activate_this, dict(__file__=activate_this))
import sys
import os
# path = os.path.join(os.path.dirname(__file__), os.pardir)
# if path not in sys.path:
#     sys.path.append(path)
sys.path.append('/var/www/repository_metrics/')

from repository_metrics import app as application

if __name__ == '__main__':
    application.run(debug=True, host='0.0.0.0')
