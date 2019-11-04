import logging
import json

from flask import Flask, Response, request, jsonify
from utils.mccc_gen import ivr_init, ivr_check
from utils.call_info import Call

app = Flask(__name__)

calls = {}
call_ended = []


def invalid_response():
    """
      Wrapper for returning invalid response
    """
    return Response(
        '{"status": "Invalid request"}',
        status=400,
        mimetype='application/json'
        )


@app.route('/voice/collect-mccc', methods=['POST'])
def collect_mccc():
    """
      Route received when using `collect` parameters from our MoceanVoice GW
    """
    session_uuid = request.form.get('mocean-session-uuid')
    call_uuid = request.form.get('mocean-call-uuid')
    digits = request.form.get('mocean-digits')
    logging.info(f'### Collect MCCC received from [{call_uuid}] ###')
    host = request.headers['Host']

    if call_uuid not in calls:
        call = Call(session_uuid, call_uuid, None, None, host)
        calls[call_uuid] = call
        logging.debug(f'call-uuid[{call_uuid}] added into calls dict')
        return jsonify(ivr_init(call))
    elif call_uuid in call_ended:
        # If the call has ended and still collect-mccc request,
        # it is unprocessable
        return Response('[]', status=422, mimetype='application/json')
    else:
        call = calls[call_uuid]
        del_call, res = ivr_check(digits, call)
        if del_call:
            logging.debug(f'Deleting call-uuid[{call_uuid}] from calls dict')
            del calls[call_uuid]
        return jsonify(res)


@app.route('/voice/inbound-mccc', methods=['POST'])
def inbound_mccc():
    """
      Route received when an inbound call is received from our MoceanVoice GW
    """
    session_uuid = request.form.get('mocean-session-uuid')
    call_uuid = request.form.get('mocean-call-uuid')
    destination = request.form.get('mocean-to')
    source = request.form.get('mocean-from')

    logging.info(f'### Call received from [{source}], \
                assigned call-uuid[{call_uuid}] ###')
    host = request.headers['Host']

    if call_uuid in calls:
        logging.warning(f'call-uuid[{call_uuid}] is in calls, \
            should use `voice/collect-mccc\' path')
        call = calls[call_uuid]
    elif call_uuid in call_ended:
        # If the call has ended and still inbound-mccc request,
        # it is unprocessable
        return Response('[]', status=422, mimetype='application/json')
    else:
        call = Call(session_uuid, call_uuid, source, destination, host)
        calls[call_uuid] = call
        logging.debug(f'call-uuid[{call_uuid}] added into calls dict')

    del_call, res = ivr_init(call)
    if del_call:
        logging.debug(f'Deleting call-uuid[{call_uuid}] from calls dict')
        call_ended.append(call)
        del calls[call_uuid]
    return jsonify(res)


@app.route('/voice/call-status', methods=['POST'])
def call_status():
    """
      Route received for webhook about call
    """

    if call_uuid in request.args.items():
        call_uuid = request.form.get('mocean-call-uuid')
        logging.info(f'### Call status received [{call_uuid}] ###')
        for k, v in request.args.items():
            logging.debug(f'\t{k}:{v}')
        return Response('', status=204, mimetype='text/plain')
    else:
        return invalid_response()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    app.run(debug=True, host='0.0.0.0', port='5000')