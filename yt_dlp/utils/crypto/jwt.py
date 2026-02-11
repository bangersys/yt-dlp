import base64
import hashlib
import hmac
import json


# implemented following JWT https://www.rfc-editor.org/rfc/rfc7519.html
# implemented following JWS https://www.rfc-editor.org/rfc/rfc7515.html
def jwt_encode(payload_data, key, *, alg='HS256', headers=None):
    assert alg in ('HS256',), f'Unsupported algorithm "{alg}"'

    def jwt_json_bytes(obj):
        return json.dumps(obj, separators=(',', ':')).encode()

    def jwt_b64encode(bytestring):
        return base64.urlsafe_b64encode(bytestring).rstrip(b'=')

    header_data = {
        'alg': alg,
        'typ': 'JWT',
    }
    if headers:
        # Allow re-ordering of keys if both 'alg' and 'typ' are present
        if 'alg' in headers and 'typ' in headers:
            header_data = headers
        else:
            header_data.update(headers)

    header_b64 = jwt_b64encode(jwt_json_bytes(header_data))
    payload_b64 = jwt_b64encode(jwt_json_bytes(payload_data))

    # HS256 is the only algorithm currently supported
    h = hmac.new(key.encode(), header_b64 + b'.' + payload_b64, hashlib.sha256)
    signature_b64 = jwt_b64encode(h.digest())

    return (header_b64 + b'.' + payload_b64 + b'.' + signature_b64).decode()


# can be extended in future to verify the signature and parse header and return the algorithm used if it's not HS256
def jwt_decode_hs256(jwt):
    _header_b64, payload_b64, _signature_b64 = jwt.split('.')
    # add trailing ='s that may have been stripped, superfluous ='s are ignored
    return json.loads(base64.urlsafe_b64decode(f'{payload_b64}==='))
