import urequests


def request_get(url, **kwargs):
    retries = 5
    while retries > 0:
        try:
            result = urequests.get(url, **kwargs)
            return result
        except:
            retries -= 1
            if retries == 0:
                raise
            time.sleep(1)
