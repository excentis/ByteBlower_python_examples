"""
    A simple webserver to interact with the user.
    
      * We list the Wireless Endpoint available for testing.
         * Those running a test a coloured blue.
      * Clickin on a device starts the test.    
         The results are displayed after the test in 
         the lefthand pane.
"""
from flask import Flask, render_template
from flask import jsonify, send_from_directory
from flask import request
from byteblowerll.byteblower import ByteBlower
from byteblowerll.byteblower import DeviceStatus

config = {
    'meetingpoint' : 'byteblower-tutorial-1300.lab.byteblower.excentis.com'
}

def device_status_to_str(state):
    """
        Convert the value to an actual name.
    """
    for (name, val) in DeviceStatus.__dict__.items():
        if val == state:
            return name


# Why did the MeetingPoint add call get this slow??
api = ByteBlower.InstanceGet()
meetingPoint = api.MeetingPointAdd(config['meetingpoint'])

def list_devices():
    """
        List Wireless Endpoint devices.
        Returns the results as a list of dictionairies.
    """
    devices_list = []
    for dev in  meetingPoint.DeviceListGet():
        devices_list.append(
            {'uuid': dev.DeviceIdentifierGet(),
             'name': dev.DeviceInfoGet().GivenNameGet(), 
             'state': device_status_to_str(dev.StatusGet())
            })
    return devices_list        

app = Flask('Wireless Endpoint: Wi-Fi statiscs', static_folder='static')
app.config['TEMPLATES_AUTO_RELOAD'] = True

@app.route("/devices")
def get_devices():
    return jsonify(list_devices())

@app.route("/poller")
def poller():
    """
        Manually send it out, workaround for polling fix ..
        TODO fix poller.js to server the file statically.
    """
    with open('static/poller.js') as f:
        return ''.join(f)

@app.route("/start_run", methods=['POST'])
def start_run():
    """
        Starts at test run..
        TODO all of it.
    """
    print('Starting a run: %s' % (request.form.get('uuid', default ='none', type=str)))
    return "ok"

@app.route("/")
def index():
    return render_template("index.html")


@app.after_request
def add_header(r):
    """
        Add headers to both force latest IE rendering engine or Chrome Frame,
        and also to cache the rendered page for 10 minutes.
    """
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    r.headers["Pragma"] = "no-cache"
    r.headers["Expires"] = "0"
    r.headers['Cache-Control'] = 'public, max-age=0'
    return r

if __name__ == "__main__":
    app.run()




