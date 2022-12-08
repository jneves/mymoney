'''things that may need frequent changing:
authInputIds
authInputValues
'''

import base64
import hashlib


def _b64_sha1(x):
    tmp = base64.b64encode(hashlib.sha1(x).digest())
    assert tmp[-1] == "="
    return tmp[:-1]


def _doHash(userId, password, challenge):
    return _b64_sha1(userId+challenge+password)


def _extract_inside_quotes(text, find_text):
    i = text.index(find_text)
    i = text.index("'", i) + 1
    j = text.index("'", i)
    return text[i:j]


def _extract_challenge(html):
    '''challenge is dynamically generated with the page.
    This function extracts it from the html of login page'''
    challenge = _extract_inside_quotes(
        html,
        "doHash(contractNumber.value, accessCode.value"
    )
    map(int, challenge)  # assertion
    return challenge


def _extract_session_key(html):
    key = _extract_inside_quotes(
        html,
        '''name="credentialsSessionKey" value='''
    )
    assert key.startswith("CREDENTIALS_SESSION_KEY_")
    return key


def parameters(html, user, password):
    challenge = _extract_challenge(html)
    credentialsSessionKey = _extract_session_key(html)
    contractNumber = user
    accessCode = _doHash(user, password, challenge)
    return {
        "credentialsSessionKey": credentialsSessionKey,
        "contractNumber": contractNumber,
        "accessCode": accessCode,
        }


def parameters_test(user, password, challenge, sessionkey):
    accessCode = _doHash(user, password, challenge)
    return {
        "credentialsSessionKey": sessionkey,
        "contractNumber": user,
        "accessCode": accessCode,
        }
